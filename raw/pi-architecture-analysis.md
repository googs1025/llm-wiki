# Pi Agent Harness 架构与设计思路分析

> 仓库：https://github.com/earendil-works/pi · 分析日期：2026-06-12 · 版本：HEAD `3f44d3e`（2026-06-12，fix(ai): remove stale OpenRouter Kimi free model assertion (#5650)）· 获取方式：GitHub API 复核 HEAD + codeload tarball 源码扫描。

## 一句话定位

`earendil-works/pi` 是 agent harness monorepo，而不是单个 CLI。核心包分成 `pi-ai`（统一多 provider LLM API）、`pi-agent-core`（tool calling/state 管理）、`pi-coding-agent`（交互式 coding CLI）和 `pi-tui`（terminal UI）。README 明确说明 Pi 默认不限制文件/进程/网络/凭据权限，需要用 OpenShell、Gondolin micro-VM 或 Docker 做外部隔离。

## 核心架构图

```text
┌──────────────────────────── pi-coding-agent CLI ─────────────────────────────┐
│ terminal UX · session transcript · tool selection · prompts                    │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ pi-agent-core                                                                 │
│ agent loop · tool call validation · state/context handoff                      │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ pi-ai                         │  │ pi-tui                                      │
│ provider registry · streaming │  │ differential terminal rendering             │
│ tools schema · cost/context    │  │                                             │
└───────────────┬──────────────┘  └────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────────────────┐
│ OpenAI / Anthropic / Google / OpenRouter / Bedrock / OAuth providers          │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `packages/ai` | provider/model registry、stream/complete、tool schema、partial tool JSON、token/cost、OAuth/API key。 |
| `packages/agent` | agent runtime 和 tool loop/state 管理。 |
| `packages/coding-agent` | 面向代码仓库的 CLI、prompt、session、内置工具组合。 |
| `packages/tui` | 终端 UI 渲染库。 |
| `.pi/skills`, `.pi/prompts` | 项目内置 prompts/skills，说明 Pi 自身也用 agent 扩展机制组织能力。 |

## 关键数据流

1. CLI 读取 prompt/session/config，选择模型和工具集，调用 `pi-agent-core`。
2. agent core 通过 `pi-ai` 的统一 stream/complete API 与 provider 通信；tool call 参数使用 TypeBox schema 校验。
3. provider stream 事件可能交错 text/thinking/toolcall delta，消费者必须按 contentIndex 归并。
4. 工具结果写回 context，必要时可 handoff 到其他模型继续。

## 设计决策与哲学

- 先把多 provider LLM API 做稳，再在其上堆 coding agent，是 Pi 的主要抽象顺序。
- 安全边界不内置，换来简洁和宿主机能力，但生产/团队使用必须外部 sandbox。
- 强 supply-chain hardening：依赖 pin、ignore-scripts、shrinkwrap、release smoke test。
- Pi 更像“可复用 harness 组件库”，oh-my-pi 则是在此基础上堆完整工具宇宙。

## 与已有项目的对比

和 Codex 相比，Pi 更偏 framework/harness，provider 中立；和 oh-my-pi 相比，Pi 更克制，工具面和原生 Rust 加速少；和 [[agent-sandbox]]/OpenShell 相比，Pi 不提供 runtime 隔离，只能被它们承载。

## 选型提示

- 适合深挖的问题：入口协议、状态源、工具/运行时边界、部署模型、失败恢复和安全治理。
- 不要只看 README：本页结论来自源码目录、入口文件、核心包和 GitHub 当前 HEAD 的组合扫描。
- 后续如继续深化，应补充 release/tag 变更、关键 issue/PR 和真实部署案例。
