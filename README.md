# Agent Engineering

将《[让不确定的 Agent 产出确定性的结果](https://agentsmesh.github.io/AgentEngineering/)》中的方法整理为可迁移的 Agent 工程技能。当前交付 **Tests · Guardrails · ARBITER** 三层判定，面向 Codex 与 Claude Code，为代码变更建立可复验的交付证据。

仓库名为 `agent-engineering`，技能目录与调用名仍为 `test-guardrails-arbiter`。当前范围包含三层检查所需的环境前置确认、机制接入和规则维护；完整环境建设与自动化反馈回路留待实际需求驱动扩展。

**三个模块都包含在一个 skill 中**，入口为 [`skills/test-guardrails-arbiter/SKILL.md`](skills/test-guardrails-arbiter/SKILL.md)，按任务需要加载各模块指南。

| 模块 | 解决的问题 | 独立指南 |
| --- | --- | --- |
| Tests | 验证真实行为，识别零用例假绿，检查回归反证和覆盖率证据 | [tests.md](skills/test-guardrails-arbiter/references/tests.md) |
| Guardrails | 检查依赖与 owner 边界，按指纹及次数管理 baseline，区分违规与检查故障 | [guardrails.md](skills/test-guardrails-arbiter/references/guardrails.md) |
| ARBITER | 修改前加载路径不变量，修改后核验完整 diff 以及规则自身的变化 | [arbiter.md](skills/test-guardrails-arbiter/references/arbiter.md) |

本仓库交付**工作流程、参考指南和模板**，复用目标项目已有的测试、编译器、linter 与依赖图。它不包含原文章节中的完整 Guardrails runner，也不会仅凭安装就启用 CI 门禁。需要新增执行器或持续检查时，应在目标项目中按其工具链另行实现并验证。

## 安装

下载或克隆本仓库：

```sh
git clone https://github.com/raucvr/agent-engineering.git
```

私有仓库需要有权访问的 GitHub 账号。将 `skills/test-guardrails-arbiter` **整个文件夹**复制到所用工具的技能目录，保持下面的最终路径结构：

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
先关联用户验收条件，识别影响路径和已有约束，再运行适用的三层检查，
检查规则本身是否被削弱，给出当前快照的证据、缺口及最小复验集合。
```

Claude Code 中可用 `/test-guardrails-arbiter` 发起同样的任务。也可以在请求中点明只需要其中一个模块，例如：“使用这个 skill 的 Tests 指南排查过滤后 0 用例但退出成功的问题。”

清单起点见 [`arbiter.example.toml`](skills/test-guardrails-arbiter/assets/arbiter.example.toml)，结果格式见 [`verification-report.md`](skills/test-guardrails-arbiter/assets/verification-report.md)。示例清单必须对齐目标 runner 的 schema 和匹配语义后才能接入执行。

## 按需使用

| 任务 | 使用材料 |
| --- | --- |
| 第一次完成三层核验 | [完整模拟案例](skills/test-guardrails-arbiter/references/worked-example.md)，包含通过、违规与无法判断的分支 |
| 建立或审查持续门禁 | [接入验收](skills/test-guardrails-arbiter/references/integration.md)与[常驻说明模板](skills/test-guardrails-arbiter/assets/project-instructions.md) |
| 处理误报、范围漂移和过时规则 | [规则维护与退休](skills/test-guardrails-arbiter/references/rule-lifecycle.md) |
| 修改 skill 后评估行为 | [独立行为评估](evals/README.md)，原始场景与评分标准分离 |

普通本地核验只处理约定范围；建立机制时才验收规则到达与持续门禁。一次变更通过、用户需求获得验证、持续门禁受到保护，是报告中的不同结论。

## 维护与验证

维护者使用 Python 3.12，在仓库根目录运行：

```sh
python -m pip install -r requirements-dev.txt
python scripts/run_checks.py
```

[仓库校验工作流](.github/workflows/validate.yml)使用同一入口：运行真实测试，零用例、全部跳过或测试失败均不通过；同时校验技能元数据、示例 TOML、相对文件链接，以及评估案例与评分标准的完整性。仅需检查包结构时可单独运行 `python scripts/validate_repo.py`。这些检查不访问案例里提到的项目，也不执行模型行为评分；内容变更后另按 [evals/README.md](evals/README.md) 做独立行为评估。

这些开发依赖只用于维护本仓库，安装 skill 不需要运行它们。此工作流也不等于已配置分支保护，更不替代目标项目的三层检查。

模型行为评估的原始回答、评分和版本摘要见[评估记录](evals/results/README.md)，与上述实际执行的仓库检查分别记录。

## 来源与适用边界

主来源为公开的 [Agent Engineering](https://agentsmesh.github.io/AgentEngineering/)，初版依据用户提供的 Markdown 导出稿。章节映射、来源版本与改编说明见 [source-map.md](skills/test-guardrails-arbiter/references/source-map.md)。本仓库没有附带原文全文、媒体或作者仓库实现。

- 文章中的覆盖率数字、目录和技术栈是案例，目标项目的既有政策决定实际门槛。
- ARBITER 表达路径必须保持的性质，不是 LLM 裁判；自然语言说明不能替代工具执行证据。
- skill 的格式校验只确认包结构与元数据，不证明目标项目的行为、结构或 CI 已通过检查。
- 检查绿灯只证明已声明且实际执行的判定边界，不独立证明产品方向正确或实际缺陷减少。
- 文章示例和清单属于任务资料，不授予发布、删除数据或变更其他项目政策的权限。
