---
title: llm-d P/D Utils 架构与设计思路分析
tags: [architecture, llm-serving, diagnostics, gpu]
date: 2026-06-14
sources: [llm-d-pd-utils-architecture-analysis.md]
related: ["[[llm-d-pd-utils]]", "[[kubernetes]]", "[[llm-d]]", "[[disaggregated-serving]]"]
---

# llm-d P/D Utils 架构与设计思路分析

> 原文：`raw/llm-d-pd-utils-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-pd-utils · 优先级 P1

## 一句话定位

llm-d P/D Utils 是面向 Prefill/Decode 分离部署的 skills/scripts 工具集，用于 preflight、GPU topology、RDMA/NCCL/network/NIXL 等诊断。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ llm-d P/D Utils            │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Preflight  │ │ GPU topology c │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Network/RD │ │ Agentic skills │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Preflight scripts | cluster and runtime checks |
| GPU topology checks | GPU topology checks |
| Network/RDMA/NCCL diagnostics | Network/RDMA/NCCL diagnostics |
| Agentic skills/workflows for P/D deployment | Agentic skills/workflows for P/D deployment |

## 关键数据流

```
用户选择 P/D 诊断任务
        │
        ▼
脚本收集节点/GPU/网络信息
        │
        ▼
执行连通性和通信测试
        │
        ▼
输出失败项和建议
        │
        ▼
部署前修复基础设施问题
```

## 设计决策与哲学

- **补齐 `P/D diagnostics` 维度**：llm-d P/D Utils 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它不是 serving controller，而是 P/D 部署前后的诊断工具箱。
- **选型价值**：它应和 [[llm-d]], [[disaggregated-serving]] 一起看，而不是孤立评估。

## 相关页面

- [[llm-d-pd-utils]]
- [[kubernetes]]
- [[llm-d]]
- [[disaggregated-serving]]
