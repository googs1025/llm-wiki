# NemoClaw 架构与设计思路分析

> 仓库：https://github.com/NVIDIA/NemoClaw · 分析日期：2026-06-05 · 版本：HEAD `3c0340a`（2026-06-05）

## 一句话定位

NemoClaw 是 NVIDIA 为 OpenShell sandbox 内运行 always-on AI agent 提供的 TypeScript CLI 控制面：它把 guided onboarding、OpenShell gateway、OpenClaw/Hermes agent 配置、routed inference、网络策略、凭证迁移、sandbox 生命周期和 e2e 验证收束到一个 `nemoclaw` / `nemohermes` 命令面。它的核心不是推理引擎本身，而是把 host、OpenShell gateway、sandbox、agent runtime 和第三方 messaging/inference provider 之间的边界显式编排起来。

项目的实现哲学是"薄命令 + 厚编排 + 纯规划 + 外部边界适配"：`src/commands/**` 只做 oclif 解析，业务动作落到 `src/lib/actions/**`，纯规划和分类落到 `src/lib/domain/**`，OpenShell/Docker/HTTP 等副作用集中在 `src/lib/adapters/**`。这个约束在 `src/commands/README.md:6-20` 明确写出。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              User / CI / shell                               │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ nemoclaw / nemohermes
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ CLI front door                                                               │
│ src/nemoclaw.ts                                                             │
│ src/lib/cli/public-dispatch.ts                                               │
│                                                                              │
│ - sandbox-first grammar: nemoclaw <sandbox> <action>                         │
│ - argv normalization + public route translation                              │
│ - oclif command discovery/delegation                                          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ command id / normalized argv
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Thin command surface                                                         │
│ src/commands/**                                                              │
│                                                                              │
│ parse flags/args ───────▶ src/lib/actions/** / command-support helpers       │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ action call
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Host-side orchestration                                                       │
│ src/lib/onboard.ts + src/lib/actions/**                                      │
│                                                                              │
│ preflight → gateway → provider/inference → sandbox → agent setup → policy    │
│              │             │                 │             │                 │
│              │             │                 │             └─ messaging plan │
│              │             │                 └─ registry/session state       │
│              │             └─ inference.local / model router / credentials   │
│              └─ OpenShell gateway lifecycle                                  │
└────────────────────────────┬───────────────────────────────┬─────────────────┘
                             │                               │
                             ▼                               ▼
┌──────────────────────────────────────────────┐   ┌───────────────────────────┐
│ External/runtime adapters                     │   │ Declarative assets         │
│ src/lib/adapters/{openshell,docker,http}/**   │   │ nemoclaw-blueprint/**      │
│ src/lib/runner.ts                             │   │ policies / presets / router│
└────────────────────────────┬─────────────────┘   └──────────────┬────────────┘
                             │                                      │
                             ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ OpenShell gateway + sandbox runtime                                           │
│                                                                              │
│ gateway named "nemoclaw"                                                      │
│ - provider credentials are system-of-record in gateway                        │
│ - inference.local routes sandbox traffic to selected provider                 │
│ - network policy applies baseline + selected presets                          │
│                                                                              │
│ sandbox                                                                       │
│ - OpenClaw or Hermes runtime                                                  │
│ - agent config rendered/synced from host-side plan                            │
│ - messaging channel hooks and health checks                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| CLI 入口与公共语法 | `src/nemoclaw.ts`, `src/lib/cli/public-dispatch.ts`, `src/lib/cli/public-argv-translation.ts`, `src/lib/cli/command-registry.ts` | 兼容 public CLI 语法、sandbox-first 路由、命令建议、注册表感知的 sandbox 名检查，再转交 oclif。 |
| 命令层 | `src/commands/**` | oclif discovery surface；解析 flags/args 后调用 action 或 command-support helper，不放产品逻辑。 |
| Action 编排层 | `src/lib/actions/**`, `src/lib/onboard.ts` | 把用户命令变成端到端 host-side workflow，负责错误消息、resume/fresh/non-interactive 分支、步骤记录和恢复。 |
| 领域规划层 | `src/lib/domain/**`, `src/lib/inference/config.ts`, `src/lib/messaging/compiler/**` | 纯函数或近似纯函数：推理 provider 映射、策略/生命周期分类、manifest 编译、状态转换判断。 |
| 外部边界适配 | `src/lib/adapters/**`, `src/lib/runner.ts`, `src/lib/sandbox/**` | 封装 OpenShell、Docker、HTTP、shell 子进程、privileged sandbox exec。 |
| 状态与凭证 | `src/lib/state/**`, `src/lib/credentials/store.ts` | `~/.nemoclaw` JSON 状态、advisory lock、session/registry、凭证 env staging 和 legacy migration。 |
| 安全与策略 | `nemoclaw-blueprint/policies/**`, `src/lib/policy/**`, `src/lib/shields/**`, `src/lib/security/**` | deny-by-default network policy、policy presets、shields up/down/status、credential redaction/hash。 |
| Messaging 扩展 | `src/lib/messaging/**`, `src/lib/messaging/channels/**` | channel manifest registry、hook registry、plan compiler、OpenShell applier、channel status/health。 |
| 推理与模型路由 | `src/lib/inference/**`, `src/lib/onboard/model-router*.ts`, `nemoclaw-blueprint/router/**` | NVIDIA/OpenAI/Anthropic/Gemini/Hermes/vLLM/Ollama 等 provider 选择、`inference.local` 路由、local proxy/token。 |
| Blueprint 与测试 | `nemoclaw-blueprint/**`, `test/e2e/**`, `test/e2e-scenario/**`, `src/**/*.test.ts` | OpenShell sandbox 资产、policy preset、runtime scripts、unit/e2e/e2e-scenario 验证矩阵。 |

分层里最关键的约束是命令层不得复制业务层。`src/commands/README.md:12-20` 给出固定路径：`src/commands/<public command path>.ts -> parse flags/args -> call src/lib/actions/**`，同时要求 product behavior 留在 actions，纯 planning/classification 留在 domain，host/runtime 边界留在 adapters。

`public-dispatch.ts` 是一个有意放在 oclif 前面的兼容层。注释说明它支撑永久产品语法 `nemoclaw <sandbox-name> <action>`，而 oclif-native 命令 ID 仍是 `sandbox:<action>`；这个文件的职责被限制在 argv normalization、route translation、suggestion 和 registry-aware sandbox-name checks（`src/lib/cli/public-dispatch.ts:4-13`）。

## 关键数据流

### Onboard 主流程

```
┌──────────────┐
│ nemoclaw     │
│ onboard      │
└──────┬───────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ src/lib/onboard.ts:onboard                                          │
│                                                                    │
│ 1. branding/env/options: agent, non-interactive, resume, fresh      │
│ 2. validate sandbox name + usage notice + provider hint             │
│ 3. acquire onboard lock + load/create resumable session             │
│ 4. stage legacy credentials into process.env for gateway migration  │
│ 5. select agent: OpenClaw / Hermes                                  │
└──────┬─────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ state handlers                                                      │
│                                                                    │
│ handlePreflightState                                                │
│   └─ Docker/OpenShell/GPU/DNS/platform checks                       │
│ handleGatewayState                                                  │
│   └─ start/reuse/recover named OpenShell gateway                    │
│ handleProviderInferenceState                                        │
│   └─ provider/model/credential route; model router/local proxy      │
│ handleSandboxState                                                  │
│   └─ create/reuse/recreate sandbox, persist registry/session        │
│ handleAgentSetupState                                               │
│   └─ install/sync OpenClaw or Hermes runtime config                 │
│ handlePoliciesState                                                 │
│   └─ apply baseline + selected policy presets                       │
└──────┬─────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ OpenShell gateway + sandbox side effects                            │
│                                                                    │
│ openshell gateway start/reuse                                       │
│ openshell provider create/update --credential <ENV_KEY>             │
│ openshell sandbox create/connect/exec                               │
│ openshell policy set                                                │
│ ~/.nemoclaw/sandboxes.json + session files                          │
└────────────────────────────────────────────────────────────────────┘
```

源码上，`onboard()` 从 `src/lib/onboard.ts:6086` 开始，先设置 agent、非交互、重建和端口选项；`src/lib/onboard.ts:6174-6188` 获取全局 onboard lock；`src/lib/onboard.ts:6190-6229` 把 legacy plaintext credentials staging 到 `process.env`；随后按状态处理器依次进入 preflight（`6423-6460`）、gateway（`6496-6532`）、provider/inference（`6547-6617`）、sandbox（`6631-6695`）、agent setup（`6698-6734`）和 policies（`6736-6768`）。

### Messaging channel 编译与应用

```
┌──────────────────────┐
│ channel manifests     │
│ telegram/slack/...    │
└──────────┬───────────┘
           │ registry.list()
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ MessagingWorkflowPlanner                                         │
│ - de-duplicate configured channels                               │
│ - reject unsupported channels for selected agent                  │
│ - build ManifestCompilerContext                                  │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ ManifestCompiler.compile                                         │
│                                                                  │
│ resolve manifests                                                │
│ compile per-channel inputs + enrollment/reachability hooks        │
│ fan out into:                                                     │
│   credentialBindings                                              │
│   networkPolicy                                                   │
│   agentRender                                                     │
│   buildSteps                                                      │
│   stateUpdates                                                    │
│   healthChecks                                                    │
└──────────┬──────────────────────────────────────────────────────┘
           │ SandboxMessagingPlan (schemaVersion: 1)
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ MessagingSetupApplier                                            │
│ - base64 JSON plan through env when needed                        │
│ - applyCredentialsAtOpenShell                                    │
│ - applyPolicyAtOpenShell                                         │
│ - applyAgentConfigAtOpenShell                                    │
│ - list/run hook requests                                          │
└──────────┬──────────────────────────────────────────────────────┘
           ▼
┌──────────────────────┐
│ OpenShell + sandbox   │
│ provider/policy/config│
└──────────────────────┘
```

`ManifestCompiler.compile()` 明确把同一组 manifest 拆成 `credentialBindings`、`networkPolicy`、`agentRender`、`buildSteps`、`stateUpdates`、`healthChecks` 六类计划（`src/lib/messaging/compiler/manifest-compiler.ts:37-75`）。每个 channel 在 `compileChannel()` 中根据 configured/disabled/selected、workflow、interactive 和 hook 结果决定 active/configured/disabled 状态（`src/lib/messaging/compiler/manifest-compiler.ts:103-136`）。这个设计让新 channel 主要通过 declarative manifest 和 hook handler 接入，而不是在 onboard 主流程里继续堆条件分支。

### 推理路由与凭证边界

```
┌────────────────────────────┐
│ user selects provider/model │
└──────────────┬─────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│ src/lib/inference/config.ts                                  │
│ provider -> endpointUrl=https://inference.local/v1            │
│          -> profile=inference-local                           │
│          -> credentialEnv                                     │
│          -> providerLabel/model                               │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ OpenShell gateway provider                                   │
│ true credential lives in gateway, not in sandbox config       │
│ sandbox agent receives managed provider/base URL/model ref    │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Sandbox policy baseline                                      │
│ managed_inference allows inference.local for selected binaries│
└──────────────┬───────────────────────────────────────────────┘
               ▼
┌────────────────────────────┐
│ external provider / local   │
│ NVIDIA/OpenAI/vLLM/Ollama...│
└────────────────────────────┘
```

`src/lib/inference/config.ts:4-7` 声明该模块是 provider selection、model resolution 和 gateway inference output parsing 的纯函数集合。默认内部路由固定为 `https://inference.local/v1`（`src/lib/inference/config.ts:11`），各 provider 的 endpoint/profile/credentialEnv 在 `getProviderSelectionConfig()` 中统一映射（`src/lib/inference/config.ts:92-150`）。local Ollama/vLLM 使用专用 env key，注释明确说这样 OpenClaw 和 host-side gateway 不会读取用户的 host OpenAI key（`src/lib/inference/config.ts:60-64`）。

## 设计决策与哲学

- **命令面兼容产品语法，但不让产品语法污染业务层**：`public-dispatch.ts` 只处理 sandbox-first grammar 与 oclif-native grammar 的转换，命令实现仍然由 `src/commands/**` discovery 和 `src/lib/actions/**` 承接（`src/lib/cli/public-dispatch.ts:4-13`, `src/commands/README.md:12-20`）。这样既能给用户稳定的 `nemoclaw <sandbox> <action>`，又保留 oclif 的命令发现、help 和测试方式。
- **Onboard 是可恢复的 host-side 状态机，而不是一次性安装脚本**：`onboard()` 支持 `--resume` / `--fresh` / non-interactive，获取全局 lock，记录 step 结果，并在进程异常退出时标记当前 step failed（`src/lib/onboard.ts:6086-6188`, `src/lib/onboard.ts:6372-6380`）。近期提交也显示主线正在把 onboard 分支拆成 FSM result：`d5d2339 refactor(onboard): consume handler FSM results compatibly`, `93adbc7 refactor(onboard): add FSM runner shell`, `8260015 refactor(onboard): return FSM results from provider inference`。
- **Declarative assets + host orchestrator，而不是把 sandbox 配置写死在代码里**：`nemoclaw-blueprint/blueprint.yaml` pin 住 OpenShell/OpenClaw 版本、sandbox image digest、resource profiles、inference profiles 和 router profile（`nemoclaw-blueprint/blueprint.yaml:4-108`）。TypeScript 编排层消费这些资产，release tooling 可以独立更新 digest/profile，policy preset 也能独立演进。
- **Provider 凭证由 OpenShell gateway 托管，NemoClaw 只做进程内 staging**：`src/lib/credentials/store.ts:4-9` 明确说 gateway 是 provider credentials 的 system of record，该模块只在当前进程 env 中暂存以便执行 `openshell provider create/update --credential KEY`。`getCredsFile()` 只保留旧版明文 `credentials.json` 的迁移路径，新代码不得写该文件（`src/lib/credentials/store.ts:117-125`）。
- **网络默认最小化，第三方平台通过 preset 显式启用**：`openclaw-sandbox.yaml` 写明默认策略原则是 deny by default，只允许核心功能（`nemoclaw-blueprint/policies/openclaw-sandbox.yaml:4-14`）。`inference.local` 是所有 provider 的统一 sandbox 内出口，因此在 baseline；GitHub 和 messaging endpoint 被移出 baseline，改成用户显式选择 preset（`nemoclaw-blueprint/policies/openclaw-sandbox.yaml:88-116`, `180-186`）。
- **Shields 是 host-side 安全控制，sandbox 不能自降级**：`src/lib/shields/index.ts:4-11` 明确 shields up/down/status 都是 host-side 管理，sandbox 不能自己降低或提高 shields。它通过 privileged sandbox exec 绕开 sandbox 内 Landlock 上下文来修改只读路径或 chattr flags，并集中到 registry-scoped helper（`src/lib/shields/index.ts:63-78`）。
- **Messaging channel 用 manifest compiler 做扩展点**：manifest 先解析成 serializable `SandboxMessagingPlan`，再由 applier 落到 OpenShell provider/policy/agent config。这让 channel 能独立声明 secret/config input、policy preset、render target、hook phase 和 health check，减少主 onboard 流程的组合爆炸。
- **本地 JSON 状态优先，复杂性用 lock 和恢复逻辑兜住**：registry 存在 `~/.nemoclaw/sandboxes.json`，并用 mkdir advisory lock 实现跨进程互斥（`src/lib/state/registry.ts:80-99`）。这保持 CLI 无 daemon/DB 依赖，但要求 registry、session、recovery action 对部分写入和 stale lock 有明确处理。

## 关键组件深入解读

### CLI front door（`src/lib/cli/public-dispatch.ts`）

NemoClaw 的 public CLI 不是 oclif 原生形态，而是 sandbox-first：用户输入 `nemoclaw mybox connect`，内部需要转成 `sandbox:connect` 类 command id 或 native argv。`public-dispatch.ts` 的设计重点是把这个兼容层限制在最前面。它懒加载 registry、registry recovery 和 sandbox connect action，只有在需要做 sandbox-name 检查、恢复或 connect help/flag 解析时才触发相关模块。

这层还承担用户体验逻辑：全局命令建议、OpenShell 命令误用提示、sandbox 不存在时列出已注册 sandbox、对 `connect` 参数顺序给 hint。重要的是，源码注释要求"new command adapters in `src/commands/**`, product behavior in `src/lib/actions/**`"，所以它不是第二套命令框架，而是 public grammar adapter。

### Onboard 编排器（`src/lib/onboard.ts`）

`src/lib/onboard.ts` 是全仓最大复杂度中心，但它的职责不是单个算法，而是 host-side workflow 的事务边界。`onboard()` 初始化运行模式、验证 sandbox 名、获得 usage consent、抢占 onboard lock、加载/创建 session、迁移 legacy credentials，然后依序调用多个 `handle*State` 状态处理器。每个处理器返回 session/state result，再通过 `onboardRuntimeBoundary.recordStateResult*` 写入兼容的进度记录。

这解释了为什么文件顶部 import 了大量 helper：它更像 coordinator，不像 library。近期 git 历史集中在把 provider inference、sandbox branch、OpenClaw setup 等分支抽成 FSM result，说明维护方向是继续把巨型编排器拆成可测试状态处理器，同时保留一个端到端顺序入口。

### Messaging manifest compiler（`src/lib/messaging/compiler/**`）

Messaging 子系统是 NemoClaw 最清晰的可扩展架构。`MessagingWorkflowPlanner` 先根据 agent 和 supportedChannelIds 做去重与支持性校验，再调用 `ManifestCompiler`。Compiler 对每个 manifest 执行 input resolution、credential availability、enrollment hook、reachability hook，然后把 manifest 的声明性字段 fan out 成六类 plan：credential binding、network policy、agent render、build step、state update、health check。

Applier 只接受 serializable `SandboxMessagingPlan`，并提供 base64 env 编解码。这说明 plan 被当作跨边界 contract：可以在 host process、OpenShell command、sandbox apply step 之间传递，不携带函数/类实例，也不直接携带 secret 值。

## 性能 / 资源开销

未在源码中发现稳定基准数据。可确认的资源设计点包括：

- 仓库本身约 1871 个非 `.git` 文件、约 30 MB，主体是 TypeScript CLI 与测试。
- Onboard 是重 I/O workflow：Docker/OpenShell/gateway/sandbox/provider/local inference 检查都可能产生秒级到分钟级等待。
- `blueprint.yaml` 给 sandbox resource profiles 设置 CPU/memory 百分比（creator/gamer/game-developer/developer），说明资源预算被看作 operator 可选 posture，而不是固定默认。
- local inference 路径包含 vLLM/Ollama/NIM 等 provider，`timeout_secs` 多处设置为 180，体现模型服务冷启动/健康检查需要更长窗口。

## 安全模型

NemoClaw 的安全边界可以分成四层：

1. **凭证边界**：OpenShell gateway 是 provider credentials 的 system of record；NemoClaw CLI 只把凭证暂存在当前进程 env，legacy plaintext file 仅用于迁移，迁移后走 secure unlink。
2. **网络边界**：baseline policy deny-by-default，只允许核心 agent、managed inference 和必要 docs/plugin 访问；GitHub、messaging、package index 等通过 policy preset 显式 opt-in。
3. **文件/进程边界**：OpenShell policy 设置 read-only/read-write 路径、sandbox 用户/组、Landlock best_effort；shields up 再用 host-side privileged exec 对 agent config 做 DAC/chattr/hash seal。
4. **状态边界**：`~/.nemoclaw` 存 registry/session/shields 状态，registry 使用 mkdir lock 与 owner pid/stale mtime 处理并发；这不是强安全存储，但足够承载 CLI 控制面的可恢复状态。

主要风险是 host-side CLI 是高权限协调者：它能调用 Docker/OpenShell privileged path，也能 staged credentials。因此源码把 secret redaction、known env allowlist、unsafe HOME 拒绝、legacy file size cap、policy opt-in 和 host-side shields 作为多层防护，而不是依赖单点隔离。
