"""Read-only, offline validation of this skill package (Python 3.11+).

Markdown checks cover common inline links/images and reference definitions,
including angle destinations and URL-encoded paths. Fenced/inline code is
ignored. Fragment anchors and full CommonMark syntax are not validated.
This is package validation, not a policy runner or semantic evaluation.
"""

import argparse
import json
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote, urlsplit

import yaml


_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_INLINE_LINK = re.compile(
    r'!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|((?:[^()\s]|\([^()\s]*\))+))'
    r'(?:\s+["\'][^\n]*?["\'])?\s*\)'
)
_REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))", re.MULTILINE)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value, nonempty=False):
    return isinstance(value, list) and (bool(value) or not nonempty) and all(_text(item) for item in value)


def _label(path, root):
    return path.relative_to(root).as_posix()


def _read(path, root, errors):
    label = _label(path, root)
    try:
        if not path.resolve().is_relative_to(root):
            errors.append(f"{label}: file is outside repository")
            return None
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{label}: cannot read file ({exc})")
        return None


def _load(path, parser, root, errors):
    content = _read(path, root, errors)
    if content is None:
        return None
    try:
        return parser(content)
    except (ValueError, yaml.YAMLError) as exc:
        errors.append(f"{_label(path, root)}: invalid format ({exc})")
        return None


def _skill(path, root, errors):
    label = _label(path, root)
    content = _read(path, root, errors)
    metadata = None
    if content is not None:
        lines = content.splitlines()
        if lines and lines[0] == "---" and "---" in lines[1:]:
            end = lines.index("---", 1)
            try:
                metadata = yaml.safe_load("\n".join(lines[1:end]))
            except yaml.YAMLError as exc:
                errors.append(f"{label}: invalid YAML frontmatter ({exc})")
        else:
            errors.append(f"{label}: missing or unterminated YAML frontmatter")
    if not isinstance(metadata, dict):
        errors.append(f"{label}: frontmatter must be a mapping")
        metadata = {}
    name = metadata.get("name")
    if not isinstance(name, str) or len(name) > 64 or not _NAME.fullmatch(name) or name != path.parent.name:
        errors.append(f"{label}: name must match its folder and be a lowercase hyphenated name (1–64 characters)")
    if not _text(metadata.get("description")):
        errors.append(f"{label}: description must be non-empty text")

    agent = path.parent / "agents/openai.yaml"
    data = _load(agent, yaml.safe_load, root, errors)
    interface = data.get("interface") if isinstance(data, dict) else None
    if not isinstance(interface, dict):
        errors.append(f"{_label(agent, root)}: interface must be a mapping")
    else:
        if not _text(interface.get("display_name")):
            errors.append(f"{_label(agent, root)}: display_name must be non-empty text")
        short = interface.get("short_description")
        if not _text(short) or not 25 <= len(short) <= 64:
            errors.append(f"{_label(agent, root)}: short_description must contain 25–64 characters")
        prompt = interface.get("default_prompt")
        token = rf"\${re.escape(path.parent.name)}(?![a-z0-9-])"
        if not _text(prompt) or not re.search(token, prompt):
            errors.append(f"{_label(agent, root)}: default_prompt must contain ${path.parent.name}")

    asset = path.parent / "assets/arbiter.example.toml"
    data = _load(asset, tomllib.loads, root, errors)
    if isinstance(data, dict):
        for key in ("id", "risk", "invariant"):
            if not _text(data.get(key)):
                errors.append(f"{_label(asset, root)}: {key} must be non-empty text")
        for key in ("paths", "read", "forbid", "checks"):
            if not _strings(data.get(key), nonempty=key in ("paths", "checks")):
                errors.append(f"{_label(asset, root)}: {key} must be a string array; paths/checks must be non-empty")


def _prose(content):
    lines = []
    fence = None
    for line in content.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
            continue
        if match:
            fence = match[1]
            continue
        lines.append(line)
    return re.sub(r"(`+).*?\1", "", "\n".join(lines), flags=re.DOTALL)


def _links(path, root, errors):
    content = _read(path, root, errors)
    if content is None:
        return
    prose = _prose(content)
    for pattern in (_INLINE_LINK, _REFERENCE):
        for match in pattern.finditer(prose):
            destination = match[1] or match[2]
            if destination.startswith("#"):
                continue
            try:
                url = urlsplit(destination)
            except ValueError:
                errors.append(f"{_label(path, root)}: invalid link {destination!r}")
                continue
            if url.scheme in ("http", "https", "mailto") or url.netloc:
                continue
            local = Path(unquote(url.path).replace("\\", "/"))
            target = (path.parent / local).resolve()
            if url.scheme or local.is_absolute() or not target.is_relative_to(root):
                errors.append(f"{_label(path, root)}: link {destination!r} is outside repository")
            elif not target.exists():
                errors.append(f"{_label(path, root)}: missing link target {destination!r}")


def _cases(path, rubric, root, errors):
    data = _load(path, json.loads, root, errors)
    rows = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        errors.append(f"{_label(path, root)}: cases must be a non-empty array")
        return set()
    ids = set()
    for index, row in enumerate(rows):
        label = f"{_label(path, root)}: cases[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        identity = row.get("id")
        if not _text(identity):
            errors.append(f"{label}.id must be non-empty text")
        elif identity in ids:
            errors.append(f"{label}: duplicate id {identity!r}")
        else:
            ids.add(identity)
        if rubric:
            for key in ("must", "must_not"):
                if not _strings(row.get(key), nonempty=key == "must"):
                    errors.append(f"{label}.{key} must be a string array; must must be non-empty")
        elif not _text(row.get("request")):
            errors.append(f"{label}.request must be non-empty text")
    return ids


def validate(root):
    """Return all discovered package errors, without changing files or using network."""
    root = Path(root).resolve()
    if not root.is_dir():
        return [f"Repository root does not exist or is not a directory: {root}"]
    errors = []
    for required in ("README.md", "evals/README.md"):
        if not (root / required).is_file():
            errors.append(f"{required}: required file is missing")
    skills = sorted(root.glob("skills/*/SKILL.md"))
    if not skills:
        errors.append("No skills/*/SKILL.md found")
    for path in skills:
        _skill(path, root, errors)
    for path in sorted(root.rglob("*.md")):
        if not {".git", ".venv", "__pycache__"}.intersection(path.relative_to(root).parts):
            _links(path, root, errors)
    cases = _cases(root / "evals/cases.json", False, root, errors)
    rubric = _cases(root / "evals/rubric.json", True, root, errors)
    if cases - rubric:
        errors.append(f"evals/rubric.json: missing case IDs {sorted(cases - rubric)}")
    if rubric - cases:
        errors.append(f"evals/rubric.json: extra case IDs {sorted(rubric - cases)}")
    return errors


def main(argv=None):
    """Run the package check; return 0 for success and 1 for validation failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = validate(args.root)
    if errors:
        print(f"Package validation failed ({len(errors)} problems):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Package validation passed (metadata, TOML, local links, evaluation structure).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
