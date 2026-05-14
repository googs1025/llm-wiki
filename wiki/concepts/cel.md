---
title: CEL (Common Expression Language)
tags: [policy, dsl, google, expression-language]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[agentgateway]], [[kubernetes]]
---

# CEL（Common Expression Language）

> Stub — 待充实

Google 出品的**轻量表达式语言**（[google/cel-spec](https://github.com/google/cel-spec)），用于在不暴露完整脚本能力的前提下让用户写「布尔判定 / 字段取值 / 简单变换」表达式。设计为**可嵌入、可静态分析、可类型检查**。

K8s 已经把 CEL 内置进多个地方：CRD validation、Admission Policy（ValidatingAdmissionPolicy / MutatingAdmissionPolicy）、Authorization Webhook。

## 语法风格

```
// 字段访问
request.headers["authorization"].startsWith("Bearer ")

// 列表 / map 操作
request.tool.name in user.allowed_tools

// 布尔逻辑 + 短路
has(request.body) && request.body.size() < 10240
```

## 在 [[agentgateway]] 中的使用

agentgateway 把 CEL 当成**策略 IR**：所有授权 / 转换 / 速率限制都被编译成 CEL 表达式存到 `AgentgatewayPolicy.spec.expression`，运行时由 Rust 数据面解释执行。

- controller (Go) **不预编译** —— 避免 Go / Rust CEL 实现差异
- 数据面用 `crates/cel-fork`（fork 的 cel-rust）+ `crates/celx`（扩展函数集）
- 为什么 fork：原生 cel-rust 缺与 HTTP 请求对象的深度集成（header 模糊匹配 / JWT claims 访问 / body 流式访问）

## TODO

- [ ] 写 CEL 跟 Rego（OPA）的对比
- [ ] 写 CEL 在 K8s admission policy 的实战示例
- [ ] 写 cel-rust / cel-go 实现差异（这是 fork 的根因）
- [ ] 写 CEL 性能模型：静态类型检查 + 字节码 + 缓存
