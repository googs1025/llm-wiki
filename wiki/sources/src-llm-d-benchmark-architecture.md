---
title: llm-d Benchmark 架构与设计思路分析
tags: [architecture, llm-serving, benchmark, ai-infra]
date: 2026-06-13
sources: [llm-d-benchmark-architecture-analysis.md]
related: [[llm-d-benchmark]], [[llm-d]], [[llm-inference]], [[llm-d-inference-sim]], [[model-serving-operator]]
---

# llm-d Benchmark 架构与设计思路分析

> 原文：`raw/llm-d-benchmark-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-benchmark · 分析版本 HEAD `bd8dc5e`

## 一句话定位

[[llm-d-benchmark]] 是 [[llm-d]] 生态的实验编排和评测工作台，用一个 `llmdbenchmark` CLI 把 standup、smoketest、run、result collection、analysis、teardown 串成可复现流程。它不是单一压测引擎，而是把 inference-perf、GuideLLM、vLLM benchmark 等工具纳入同一套 Kubernetes 实验生命周期。

## 核心架构图

```
┌────────────────────────┐
│ llmdbenchmark CLI      │
│ llmdbenchmark/cli.py   │
└───────────┬────────────┘
            │ parse args / workspace
            ▼
┌────────────────────────┐
│ RenderSpecification    │
│ config/specification   │
│ scenario + overrides   │
└───────────┬────────────┘
            │ resolved experiment spec
            ▼
┌────────────────────────┐
│ RenderPlans            │
│ templates + defaults   │
│ cluster/version resolve│
└───────────┬────────────┘
            │ manifests / plans / configs
            ▼
┌────────────────────────┐
│ StepExecutor           │
│ global steps sequential│
│ stack steps parallel   │
└─────┬─────┬─────┬──────┘
      │     │     │
      │     │     └──────────────┐
      │     │                    │
┌─────▼─────▼─────┐     ┌────────▼──────────┐
│ standup phase   │     │ run phase          │
│ cluster/stack   │     │ harness namespace  │
│ manifests/Helm  │     │ endpoint discovery │
└─────┬───────────┘     │ deploy benchmark   │
      │                 │ collect/analyze    │
      │                 └────────┬───────────┘
      ▼                          ▼
┌──────────────┐        ┌────────────────────┐
│ Kubernetes   │        │ Harness adapters   │
│ llm-d stack  │        │ inference-perf     │
│ simulator/GPU│        │ guidellm/vllm/etc. │
└──────┬───────┘        └────────┬───────────┘
       │                         │
       ▼                         ▼
┌────────────────────────────────────────────┐
│ workspace: rendered configs, manifests,    │
│ logs, raw results, analyzed reports         │
└────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CLI 调度 | 解析命令，初始化 workspace，串起 spec rendering、plan rendering 和 phase execution。 |
| 配置模型 | defaults → scenario → CLI overrides 的配置合并和实验规格定义。 |
| 模板渲染 | 渲染 Jinja spec、Kubernetes manifests、Helm values 和 stack plans。 |
| 执行器 | 把 global steps 与 per-stack steps 分开，支持多 stack 并行执行和 `--stack` 过滤。 |
| 生命周期阶段 | standup / run / teardown / smoketest 的 step 定义。 |
| harness 适配 | 适配 inference-perf、GuideLLM、vLLM benchmark、nop、inferencemax、aiperf 等压测工具。 |

## 关键数据流

```
用户选择 scenario / flags
        │
        ▼
CLI 初始化 workspace
        │
        ▼
RenderSpecification 合并 defaults + scenario + CLI overrides
        │
        ▼
RenderPlans 解析版本、集群资源、模板和 stack plans
        │
        ▼
预渲染 Kubernetes / Helm manifests
        │
        ▼
StepExecutor 执行阶段
        │
        ├── standup: 部署或准备 llm-d stack
        ├── smoketest: 校验 endpoint/model 可用
        ├── run: 创建 harness namespace、部署 benchmark job、等待完成
        ├── collect: 收集 raw result/logs
        ├── analyze/upload: 生成报告并保存
        └── teardown: 清理实验资源
        │
        ▼
workspace 保留 rendered config + manifests + results
```

## 设计决策与哲学

- **先渲染再执行**：spec、plan 和 manifests 先进入 workspace，再执行 Kubernetes 动作，降低不可复现风险。
- **benchmark 编排器不绑定单一压测工具**：harness 适配层让 inference-perf、GuideLLM、vLLM benchmark 可以替换。
- **global step 顺序执行，per-stack step 并行**：适合一次对比多套 [[llm-d]] stack 或多个参数组合。
- **workspace 是实验事实来源**：rendered configs、manifests、logs 和结果集中保存，适合复现实验和审查差异。

## 相关页面

- [[llm-d-benchmark]]
- [[llm-d-inference-sim]]
- [[llm-d]]
- [[llm-inference]]
- [[model-serving-operator]]
