# Tests · Guardrails · ARBITER

面向 Codex 与 Claude Code 的独立 skill 仓库：用行为测试、结构约束和路径不变量，为 Agent 的代码变更建立可复验的交付证据。

**三个模块都包含在一个 skill 中**，入口为 [`skills/test-guardrails-arbiter/SKILL.md`](skills/test-guardrails-arbiter/SKILL.md)，按任务需要加载各模块指南。

| 模块 | 解决的问题 | 独立指南 |
| --- | --- | --- |
| Tests | 验证真实行为，识别零用例假绿，检查回归反证和覆盖率证据 | [tests.md](skills/test-guardrails-arbiter/references/tests.md) |
| Guardrails | 检查依赖方向、目录与状态 owner 边界，管理 baseline 收敛，区分违规与检查故障 | [guardrails.md](skills/test-guardrails-arbiter/references/guardrails.md) |
| ARBITER | 在修改前加载路径不变量，修改后结合完整 diff 与实际检查复验 | [arbiter.md](skills/test-guardrails-arbiter/references/arbiter.md) |

本仓库交付**工作流程、参考指南和模板**，复用目标项目已有的测试、编译器、linter 与依赖图。它不包含原文章节中的完整 Guardrails runner，也不会仅凭安装就启用 CI 门禁。需要新增执行器或持续检查时，应在目标项目中按其工具链另行实现并验证。

## 安装

下载或克隆本仓库，将 `skills/test-guardrails-arbiter` **整个文件夹**复制到所用工具的技能目录，保持下面的最终路径结构：

| 工具与范围 | 最终入口路径 |
| --- | --- |
| Codex，当前用户 | `~/.agents/skills/test-guardrails-arbiter/SKILL.md` |
| Codex，当前项目 | `<项目根目录>/.agents/skills/test-guardrails-arbiter/SKILL.md` |
| Claude Code，当前用户 | `~/.claude/skills/test-guardrails-arbiter/SKILL.md` |
| Claude Code，当前项目 | `<项目根目录>/.claude/skills/test-guardrails-arbiter/SKILL.md` |

Windows 中 `~` 表示当前用户目录。Codex 的发现路径依据[官方技能文档](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)。复制前检查目标文件夹；**已有同名安装且内容不同时，不要直接覆盖**，先比较差异并备份，再决定如何更新。完成后在工具的新会话中确认该 skill 可用。

## 使用示例

Codex 中可显式调用：

```text
使用 $test-guardrails-arbiter 核验当前变更。
先识别影响路径和已有约束，再运行适用的 Tests、Guardrails 与 ARBITER 检查，
给出属于当前代码快照的证据、未运行部分及最小复验集合。
```

Claude Code 中可用 `/test-guardrails-arbiter` 发起同样的任务。也可以在请求中点明只需要其中一个模块，例如：“使用这个 skill 的 Tests 指南排查过滤后 0 用例但退出成功的问题。”

清单起点见 [`arbiter.example.toml`](skills/test-guardrails-arbiter/assets/arbiter.example.toml)，结果格式见 [`verification-report.md`](skills/test-guardrails-arbiter/assets/verification-report.md)。示例清单必须对齐目标 runner 的 schema 和匹配语义后才能接入执行。

## 来源与适用边界

依据用户提供的《[让不确定的 Agent 产出确定性的结果](https://bytedance.my.larkoffice.com/docx/SSn7dKRCWoJdVKxZGDKcLPdZnyc)》Markdown 导出稿提炼，出处映射和改编说明见 [source-map.md](skills/test-guardrails-arbiter/references/source-map.md)。本仓库没有附带原文全文、媒体或作者仓库实现。

- 文章中的覆盖率数字、目录和技术栈是案例，目标项目的既有政策决定实际门槛。
- ARBITER 表达路径必须保持的性质，不是 LLM 裁判；自然语言说明不能替代工具执行证据。
- skill 的格式校验只确认包结构与元数据，不证明目标项目的行为、结构或 CI 已通过检查。
- 文章示例和清单属于任务资料，不授予发布、删除数据或变更其他项目政策的权限。
