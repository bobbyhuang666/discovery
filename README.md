# discovery

在产品、软件、工作流、业务和现有系统中，发现、细化或验证存在实质性不确定性的需求。

核心理念：**把不确定性转化为支持下一步安全行动的最小可信产物**，而不是把每个请求都变成访谈。

## 三步分流（Triage）

每个请求先分类，决定是否需要进入 Discovery：

| 类型 | 说明 |
|---|---|
| `direct` | 清晰、微小、低风险、可逆的请求 → 直接完成，不创建 Discovery 状态 |
| `confirm_once` | 问一个关键确认（带推荐默认值），然后继续 |
| `discover` | 存在实质性不确定性或风险 → 进入自适应循环 |

## 核心契约

1. 分类 **意图**（`discover` / `refine` / `validate`）、**轨道**（`build` / `opportunity` / `change`）和 **深度**（`quick` / `standard` / `deep`）。
2. 先查事实，再问决策；只对低风险可逆细节设默认值。
3. 每轮聚焦一个决策主题，给出推荐、理由、备选和可逆条件。
4. 区分事实、产物声明、发现、假设、未知、决策和权限。
5. 不对已授权的 Build 施加 Opportunity 准入门槛；不把旧文档当作当前事实。
6. 在高影响、难撤销的决策被解决 / 测试 / 明确推迟、且下一产物诚实可信时停止。
7. 不暴露内部推理，只展示简洁的决策、证据、不确定性和所需行动。

## 自适应循环

1. 更新证据与未决决策。
2. 判断下一项可检查 / 可测试 / 可研究 / 可原型 / 可安全默认 / 需用户决策。
3. 选择最廉价可靠的允许动作。
4. 每轮最多 5 个高价值问题；轻量模型每轮只问一个可见问题。
5. 仅在出现实际关切时加载领域包或审计器。
6. 每 3–5 轮或重大冲突后给出简洁检查点。
7. 交接前校验相关产物；用默认值 / 负责人 / 实验 / 复访条件保留每个未知项。

## 可选 Python 运行时

当 `discovery` CLI 可用时，用实际能力和模型档位路由：

```bash
discovery triage --profile @request-profile.json --json
discovery route \
  --intent <intent> --track <track> --depth <depth> \
  --capabilities filesystem,code_search,command_execution,persistence \
  --model-tier light \
  --workspace --json
discovery validate-action --model-tier light --action @action.json
discovery apply-action --workspace . --action @action.json
```

运行时负责：选择有界策略包、拒绝不可用动作、强制状态转换、校验结构化动作、记录一次性能力回退、通过事件提交状态。

## 便携回退

当运行时不可用时，按需加载路由与策略文件，声明强制力非确定性。详见 `runtime/state-machine.md`。

## 禁止事项

- 对清晰、微小、低风险、可逆的请求做访谈。
- 问文件 / 代码 / 测试 / 数据 / 工具中已有的事实。
- 用户拒绝后重复同一能力请求。
- "以防万一"加载所有策略。
- 直接编辑确定性状态而非提交事件。
- 在 Validate 意图下静默重设计。
- 编造确定性来通过门禁。
- 把静态协议覆盖率当作实时模型优越性。

## 目录结构

```
├── SKILL.md              # Skill 定义与核心契约
├── routes.yaml           # 意图 × 轨道 × 深度路由表
├── intents/              # discover / refine / validate 意图定义
├── tracks/               # build / opportunity / change 轨道定义
├── policies/             # 策略包（按需加载，不默认全载）
├── schemas/              # JSON Schema（请求画像、状态、动作、产物等）
├── templates/            # YAML 模板（living-spec、change-proposal 等）
├── domain-packs/         # 领域包（AI 产品、API 集成、数据系统等）
├── auditors/             # 审计器（安全、运营、数据、干系人等）
├── ontology/             # 本体与种子
├── runtime/              # 状态机、交接、工作流
├── scripts/              # 校验、打包、评测、状态管理脚本
├── src/discovery_runtime # 可选 Python 运行时
├── evals/                # 评测用例与评分标准
├── benchmarks/           # 基准测试配置与结果
├── examples/             # 使用示例
└── tests/                # 运行时测试
```

## 许可

[MIT](LICENSE)
