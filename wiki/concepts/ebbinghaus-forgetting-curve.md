---
title: Ebbinghaus 遗忘曲线
tags: [concept, agent-memory, memory-decay, cognitive-science]
date: 2026-05-14
sources: [powermem-architecture-analysis.md]
related: [agent-memory, powermem, ai-as-compressor]
---

# Ebbinghaus 遗忘曲线

德国心理学家 **Hermann Ebbinghaus**（1885）通过自身实验得出的记忆衰减经验曲线。在 LLM agent 记忆框架里被改造为 **三层记忆 + 数学衰减 + 强化反馈** 的算法基座，[[powermem]] 是当前最完整的工程实现。

## 数学模型

```
R = e^(-t/S)
```

- `R` ∈ [0, 1] — 当前 retention 强度（记忆"残留度"）
- `t` — 距上次访问的时间（小时）
- `S` — strength 参数（越大衰减越慢；强化访问会增大 S）

衰减是 **指数式** 的：刚记完忘得快，多次复习后衰减率降低 —— 这正是间隔重复（spaced repetition）的理论根基。

## 工程映射：三层记忆 + 三阈值

PowerMem 在 `intelligence/ebbinghaus_algorithm.py` 里把曲线参数化（默认值）：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `initial_retention` | 1.0 | 新记忆的初始强度（按 LLM 评出的 importance_score 缩放） |
| `decay_rate` | 0.1 | 基础衰减率 |
| `reinforcement_factor` | 0.3 | 命中检索时强度增量 |
| `working_threshold` | 0.3 | < 该值 → 工作记忆 |
| `short_term_threshold` | 0.6 | 0.3–0.6 → 短期记忆 |
| `long_term_threshold` | 0.8 | > 0.6 → 长期记忆；> 0.8 → 永久存储 |
| `review_intervals` | `[1, 6, 24, 72, 168]` 小时 | 复习时间表（1h / 6h / 1d / 3d / 1w） |

## 完整生命周期（PowerMem 实现）

```
        New Information
              ↓
      Importance Evaluation (LLM, 0.0~1.0)
              ↓
   initial_retention = 1.0 * importance_score
              ↓
   ┌────────┴─────────────┐
   ↓                       ↓
 working (<0.3)         short-term (0.3~0.6)
   ↓                       ↓
   "Forgetting Decay"   "Reinforcement Learning"
   ↓                       ↓
   importance↓             importance↑
   ↓                       ↓
   Auto Cleanup            long-term (>0.6)
                             ↓
                           Permanent Storage (>0.8)
                             ↓
                           Knowledge Base
```

- **被检索命中** → `retention += reinforcement_factor` → 可能晋升上一层；
- **超过 review_interval 仍未命中** → 按 `R = e^(-t/S)` 衰减；
- **跌破 working_threshold** → `MemoryOptimizer` 离线扫描后清理。

## 为什么这套机制重要

- **解耦存储与智能**：retention / next_review / importance_score 都只是 metadata JSON 列；不需要每次写入都跑昂贵 LLM。`MemoryOptimizer` 定时离线扫描即可完成晋升/清理 —— 对应 [[ai-as-compressor]] 的"边缘轻、后台重"哲学。
- **天然契合 token 经济性**：长期记忆只占总量的小比例，搜索时优先返回 → token 用量降到原 baseline 的 ~3%（PowerMem LOCOMO：0.9k vs 26k tokens）。
- **跨项目可复用**：MemoryOS、Letta（前 MemGPT）、claude-mem 等都用了类似抽象，但 PowerMem 是把它做成"可配置 4 参数 + 3 阈值"的工程化最彻底的版本。

## 同类实现对照

| 框架 | 记忆衰减机制 | 三层抽象 | 数学模型暴露 |
|------|------------|---------|-------------|
| **[[powermem]]** | Ebbinghaus `R=e^(-t/S)` | working / short / long ✅ | 4 参数 + 3 阈值全可配 |
| **[[claude-mem]]** | 时间衰减 + 重要性评分 | implicit | 半透明 |
| **Letta (MemGPT)** | 上下文窗口管理 + archival | core / archival 二层 | 由 LLM agent 自驱 |
| **MemoryOS** | 类生物记忆系统 | sensory / short / long | 学术原型 |

## 相关页面

- 工程实现：[[powermem]] → `intelligence/ebbinghaus_algorithm.py`
- 领域综述：[[agent-memory]]
- 设计哲学：[[ai-as-compressor]]
- 间隔重复（spaced repetition）的认知科学根基 —— Anki、SuperMemo 同源
