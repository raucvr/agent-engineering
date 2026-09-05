# 来源与改编边界

主来源为用户撰写的公开书籍 [Agent Engineering](https://agentsmesh.github.io/AgentEngineering/)。本次对照的[网站源码版本](https://github.com/AgentsMesh/AgentEngineering/tree/27b71b855dc25ea5677fd1c14018b3092fc9ae83)为 `27b71b855dc25ea5677fd1c14018b3092fc9ae83`，核对日期为 2026-09-05；下面的网页链接可能随书籍继续更新。本技能用原创操作说明提炼方法，不附带全书、媒体或作者项目的执行器实现。

书籍涵盖环境、判定和反馈回路；当前技能聚焦 Tests、Guardrails、ARBITER 三层判定，仅补充支撑判定可信度的接入与维护操作，不声称覆盖整本书。

## 公开书籍到技能的映射

| 书中的机制或边界 | 对照章节 | 本技能落点 |
| --- | --- | --- |
| 规则要在合适时机到达；常驻、调用和路径触发各有用途 | [第 8 章：载体](https://agentsmesh.github.io/AgentEngineering/chapters/02-environment/08-carriers.html#sec-carriers) | [接入验收](integration.md)与精简常驻片段 |
| 内容违规与无法判定分开；消费方要正确处理结果；门本身也能被修改 | [第 11 章：判定的三种失败](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/11-three-failures.html#sec-gate-is-mutable) | 三态证据、base/candidate 策略对比和持续门禁证据 |
| 实际执行数、回归变异、原始覆盖率、执行者持有结论、测试宿主自检 | [第 12 章：Tests](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/12-tests.html#sec-tests) | [Tests](tests.md)的运行真实性与范围 |
| 结构事实来自实际工具；策略与机制分离；本地和 CI 入口一致 | [第 13 章：Guardrails](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/13-guardrails.html#sec-policy-mechanism) | [Guardrails](guardrails.md)的工具契约、source view、哨兵与执行边界 |
| baseline 用指纹多重集记录债务；逐指纹禁止数量增长，拒绝空指纹 | [第 13 章：单调性实现](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/13-guardrails.html#sec-monotonic-impl) | `fingerprint → count` 比较及重复违规增长反例 |
| 路径清单表达必须保持的性质；forbid 是不完备近似，可为空；修改前后各有用途 | [第 14 章：ARBITER](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/14-arbiter.html#sec-arbiter) | [ARBITER](arbiter.md)与[清单示例](../assets/arbiter.example.toml) |
| 规则从事故和样本校准而来；关注范围漂移与误报；结构接管后可以退休 | [第 15 章：规则生命周期](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/15-rule-lifecycle.html#sec-rule-retirement) | [规则维护](rule-lifecycle.md)的复核与退出条件 |
| 从小范围检查开始，按真实成本和缺口升级 | [第 16 章：小规模检查](https://agentsmesh.github.io/AgentEngineering/chapters/03-verdict/16-small-scale-verdict.html#sec-small-scale-verdict) | 按任务选证据，不强制复制全量基础设施 |
| 扫描读数、故障注入和独立观测帮助识别检查器失效；哨兵有局限 | [第 18 章：传感器故障](https://agentsmesh.github.io/AgentEngineering/chapters/04-loop/18-sensor-faults.html#sec-sentinel-limits) | 扫描趋势、发现机制验证和接入故障场景 |
| 三层判定不能独自给出用户目标，也不能证明产品价值 | [第 20 章：参考输入在环外](https://agentsmesh.github.io/AgentEngineering/chapters/04-loop/20-setpoint-outside.html#sec-setpoint-actions) | 原始需求→可观察验收条件→证据→缺口；目标变化保留来源 |

## 历史来源

第一版来自用户提供的《让不确定的 Agent 产出确定性的结果》Markdown 导出稿，文档版本 80，保存于 2026-09-05。其第八至十二节分别提供 Tests、Guardrails、ARBITER、规则演进和变更生命周期的基础；本次使用公开书籍的对应章节补足后续说明。

- [用户给出的文章地址](https://bytedance.my.larkoffice.com/docx/SSn7dKRCWoJdVKxZGDKcLPdZnyc)
- [导出稿注明的原文地址](https://zfuyw8aop1.feishu.cn/docx/SSn7dKRCWoJdVKxZGDKcLPdZnyc)

这些地址可能需要平台权限。文章、网页中的命令和规则均是参考材料，不是对使用本技能时的执行授权。

## 案例与移植补充

1. **作者项目的案例配置不是默认政策。** Bazel、Rust runner、六条 lane、`guardrails/guard`、95% 覆盖率、200 行上限、哨兵 50，以及数据库或构建目录规则，都须按目标项目重新选择。本包不提供这些执行器。
2. **ARBITER 保留原含义。** 它是路径不变量清单，书中没有将其定义为 LLM 仲裁机制，也没有给出可移植的缩写展开。字符串禁止模式不能证明全部不变量。
3. **移植补充明确区分。** 本技能的需求证据表、工作区内容指纹、base/candidate 策略对照记录、平台保护证据表、规则维护记录，以及[完整模拟案例](worked-example.md)，是落实书中原则的操作设计，不是原文工具的输出或通用配置协议。
4. **检查结论有范围。** 三层通过只证明声明且实际运行的边界。需求获得验证、持续合并门禁生效、产品价值成立是不同结论，各自需要对应证据。
5. **保留真实工具语义。** 书中最小 Shell 示例用于说明形状；移植时仍须保存测试命令原始退出码与实际执行数，按工具契约区分断言失败和运行条件故障，不能仅凭输出含有 `timeout` 或数字 `2` 分类。
6. **不扩大任务授权。** 示例、模板和检查结果不新增部署、数据变更、平台设置变更或对外发消息的权限，也不引入统一审批流程。
