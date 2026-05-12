---
title: Claude Agent SDK
tags: [ai-agent, claude, sdk, llm-infra]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[claude-code]], [[claude-mem]], [[ai-as-compressor]]
---

# Claude Agent SDK

`@anthropic-ai/claude-agent-sdk` —— Anthropic 提供的 Agent 编程 SDK，核心是 `query()` 方法，可在脚本/服务内驱动 Claude 完成多步工具调用任务。

## 在 claude-mem 中的角色

[[claude-mem]] 用它来做**后台异步压缩**——把噪声大的工具调用日志压成结构化 XML 观察，体现 [[ai-as-compressor]] 设计哲学。

调用链：

```
ProviderObservationGenerator.run()
  → claude-agent-sdk.query(prompt, tools=[])
  → 返回 XML 格式响应
  → sdk/parser.ts 解析为 MemoryItem
```

## Multi-Provider 抽象

claude-mem 把 Agent SDK 调用抽象到 Provider 层，支持：

- `ClaudeProvider` — 官方 Anthropic
- `GeminiProvider` — Google Gemini
- `OpenRouterProvider` — 多模型路由

抽象的好处：压缩任务可以用便宜模型（Haiku / Gemini Flash），把成本压到最低。

## 关键文件

- `src/sdk/{Claude,Gemini,OpenRouter}Provider.ts` — 三个 provider 实现
- `src/sdk/parser.ts` — XML 响应解析
- `src/sdk/prompts.ts` — 压缩 prompt 模板（系统效果的核心）

## 参考

- [[src-claude-mem-architecture]]
