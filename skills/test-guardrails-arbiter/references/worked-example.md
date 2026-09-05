# 完整案例：新增可选 API 字段

**本页全部需求、路径、命令、版本标识和输出均为模拟。没有在某个业务仓库实际运行，也不能用作该仓库的测试或 CI 证据。** 这里展示怎样完成[验证报告](../assets/verification-report.md)；本技能不附带示例中的工具，使用时须发现并替换为目标项目的真实入口。

## 1. 先保留需求和不变量

假想任务 `REQ-17`：“新建资料接口接受可选 `locale`；缺省为 `zh-CN`，显式 `en-US` 应保留。保留现有 `name` 的去空格和空值拒绝行为；API 类型仍由 schema 生成。”

| ID | 需求来源 | 可观察验收条件 | 计划证据 |
| --- | --- | --- | --- |
| R1 | REQ-17：缺省值 | 无 locale 的请求得到 `zh-CN` | `default locale` 运行时断言 |
| R2 | REQ-17：显式值 | `en-US` 不被缺省值覆盖 | `preserves en-US` 运行时断言 |
| R3 | REQ-17：兼容行为 | name 仍去空格，空 name 仍被拒绝 | 两个既有契约用例 |
| R4 | REQ-17：生成来源 | 从 schema 重生成的类型逐字节一致 | `generated:sync` |

假想项目已采用[清单示例](../assets/arbiter.example.toml)：`generated-api-source` 匹配 `api/schema/**` 与 `src/generated/**`，要求先读 `api/schema/README.md`，注册 checks 为 `generated:sync` 和 `test:api-contract`。`forbid=[]`；来源一致性由生成比对验证，不能靠“文件带 generated 注释”判断。现有结构门禁还禁止运行时代码依赖生成器工具。

## 2. 修改前路由，修改后固定证据对象

先用 base 清单匹配预期路径并读取 schema 说明：在声明源加可选字段，再运行项目生成器，并在已有请求归一化 owner 里处理默认值。最终变更路径如下：

```text
api/schema/profile.json
src/generated/profile.ts
src/api/normalize-profile.ts
tests/profile-contract.test.ts
```

模拟快照记为 `S1`：比较基点 `B`，候选提交 `H`，工作区无已暂存、未暂存或未跟踪变更；提交树指纹为 `TREE-H`。这些是演示标签，实际报告须填完整 Git SHA 和真实内容摘要。若检查对象包含脏文件，另存它们的路径、状态和内容指纹；`HEAD` 相同不等于证据仍有效。

模拟环境为项目锁定的 Node 版本与锁文件依赖；policy 指纹 `P1`，检查器契约版本 `C1`。base 与 candidate 中的清单 ID、paths、checks、执行模式、结构规则及必需 CI job 均一致。对新增、删除和改名路径重新匹配后，命中清单仍为 `generated-api-source`。全部最终检查开始和结束时均为 `S1/P1/C1`。

为验证 R1 能抓到缺陷，在隔离副本 `M1` 只撤回默认值赋值、保留新测试：它仍能编译，但 `default locale` 断言失败，观察到 `undefined`，原始退出码为 `1`。`M1` 是故障实验的独立快照，不能与 `S1` 的通过证据混写。

## 3. 三层工具证据

下面为**模拟命令及原始输出节选**，记录者为假想测试执行进程。命令本身不是适配器，不含会覆盖退出状态的 Shell 管道。实际使用时需保存完整日志、真实原始状态和执行者身份。

Tests：

```text
[模拟] npm run test:api-contract -- --reporter=json
{"snapshot":"S1","executed":4,"passed":4,"failed":0,"skipped":0,
 "cases":["default locale","preserves en-US","trims name","rejects empty name"]}
原始退出码: 0
```

这四个用例确实执行了相关请求处理函数；不是编译成功、包级 `ok` 或发现了四个测试文件。本例没有覆盖率门禁，也没有新增覆盖率声明。

Guardrails：

```text
[模拟] npm run guard:structure -- --format=json
{"snapshot":"S1","policy":"P1","mode":"enforced",
 "rule":"runtime-no-generator-import","scannedFiles":8,"sentinelMin":6,
 "graphNodes":12,"graphEdges":18,"violations":[],
 "baselineCounts":{},"candidateCounts":{}}
原始退出码: 0
```

模拟检查器从真实构建配置产生依赖图并检查方向；不是全文搜索推测调用关系。扫描下限 `6` 是本例项目已校准的配置，不是技能默认值。本例没有历史债务；有债务时须逐指纹比较次数，不能只比较集合或总数。

ARBITER 的来源约束及变更后复验：

```text
[模拟] npm run generated:sync -- --check
{"snapshot":"S1","source":"api/schema/profile.json",
 "output":"src/generated/profile.ts","regeneratedFiles":1,"differentFiles":0}
原始退出码: 0

[模拟] npm run arbiter:check -- --base B --head H
{"snapshot":"S1","policy":"P1","matched":["generated-api-source"],
 "requiredChecks":["generated:sync","test:api-contract"],
 "forbidCount":0,"policyDiff":[],"uncoveredChangedPaths":[]}
原始退出码: 0
```

此处 `uncoveredChangedPaths=[]` 仅表示按项目已声明的路由范围核验后无遗漏，不表示所有代码路径都被 ARBITER 保护。`src/api/` 和测试路径由行为、结构检查覆盖。将清单要求的两个 check 与前述同一快照日志逐项关联，不能把打印出名称等同于它们已执行。

## 4. 模拟完成报告

| 维度 | 结论 | 依据与边界 |
| --- | --- | --- |
| Tests | Passed | S1 实际执行 4 个用例，0 失败、0 跳过；M1 的目标断言确实失败 |
| Guardrails | Passed | S1/P1 扫描 8 个文件，满足已校准下限；依赖约束通过，无债务增长 |
| ARBITER | Passed | 修改前已读路径背景；变更后清单与策略复验完成，两项必需 check 具有 S1 证据 |
| 原始需求覆盖 | R1–R4 均有证据 | R1/R2 各一用例，R3 两用例，R4 生成比对；未将需求改为“只通过测试” |
| 持续合并门禁 | 尚未验证 | 本地检查和 CI 配置已对照；本例没有实际 CI run、必需任务保护及下游三态消费的证据 |
| 产品价值 | 未评价 | 未测量使用率或用户结果；代码验收不能替代这些证据 |

本次代码核验在声明范围内 `Passed`；不能据此宣布“CI 已接入并受到保护”。若任务还包括建立持续机制，须继续完成[接入验收](integration.md)；普通代码任务则如实记录这一边界。

## 5. 两个不能报通过的分支

两例各自是独立模拟快照，不能替换上面 `S1` 的日志后仍声称结果相同。这里假想的生成检查器 `C1` 有经校准的契约：`0` 为比对一致，`1` 为成功生成但发现差异，`2` 为生成工具未能启动。此约定仅属于该检查器，不适用于未知工具。

| 分支 | 模拟原始证据 | 分类与下一步 | 需求与门禁结论 |
| --- | --- | --- | --- |
| 手写生成类型，运行时用例仍通过 | S2：`generated:sync` 完成重生成，`differentFiles=1`，差异定位到 `src/generated/profile.ts`，原始码 `1` | **PolicyViolation**：违反 R4 和路径不变量；修改 schema 并重生成，固定新快照后重跑受影响检查 | R1–R3 有证据，R4 不满足；不能交付为通过，持续门禁仍未验证 |
| 锁定生成器无法启动 | S3：`generated:sync` 输出 `generator executable missing`，原始码 `2`，未产出生成结果 | **InfrastructureFailure**：当前无法判断 R4；恢复已声明的工具环境后重跑，不改业务代码来消除工具故障 | 即使 R1–R3 有测试证据，R4 仍未知；不能放行，不能称为已发现生成物违规 |

若真实工具返回未知状态或日志不完整，保留原始码和诊断，将相关结论标为无法判定并补证；不要套用本例数字。若发现同次改动删除清单、缩窄路径或移除 CI 任务，也要记录策略变更及影响，不能只用删减后的候选策略取得绿灯。
