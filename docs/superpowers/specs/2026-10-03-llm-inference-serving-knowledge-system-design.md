---
title: LLM Inference / Serving 知识体系优化设计
date: 2026-10-03
status: approved-design
---

# LLM Inference / Serving 知识体系优化设计

## 1. 目标与成功标准

本次优化面向 AI Infra / Serving 工程师，把现有以项目条目和 ASCII 图为主的内容重构为一条端到端学习路径：从请求进入系统开始，依次理解路由、调度、执行、KV、分布式 serving、Kubernetes 控制面、性能和可靠性，最后落到项目组合与选型。

成功标准：

1. `[[llm-inference]]` 成为专题首页，读者能在三次点击内到达 engine、KV、P/D、routing、SLO、reliability 和 selection。
2. 形成 12 张互不重复的图：4 张架构图、4 张流程图、4 张时序图。
3. 图源使用 Markdown Mermaid，Obsidian 与生成 HTML 共用同一份源代码。
4. 稳定机制、项目事实、来源快照和横向分析各归其位，避免把易变实现细节复制到总览页。
5. 最新项目判断以 2026-10-03 的官方资料为依据，并与旧 Source 快照明确区分。
6. 新增页面无孤儿、无断链，索引、日志和生成页面同步更新。

## 2. 非目标

- 不覆盖训练、微调或数据工程，只描述它们与 serving 的接口边界。
- 不把所有推理项目扩展成同等深度的源码分析；五个锚点是 vLLM、SGLang、Dynamo、llm-d 和 AIBrix。
- 不修改 `raw/`，也不把历史 Source 页面改写成未经 raw 支撑的“最新版本”。
- 不宣称跨项目存在统一的 P/D、KV transfer、重试或故障恢复协议。
- 不为每个项目重复绘制一套端到端系统图；Concept/Analysis 只表达跨项目稳定抽象。

## 3. 设计选择

### 3.1 采用端到端学习路径

采用“请求如何变成 token”作为主线，而不是纯项目目录或纯故障手册：

```text
API / SLO
  → routing / admission / queue
  → engine scheduling / batching / execution
  → KV allocation / reuse / transfer / eviction
  → distributed serving / P-D
  → control plane / autoscaling / GPU infrastructure
  → observability / reliability / capacity
  → project composition / selection
```

备选方案及未采用原因：

- 分层架构手册：查阅清楚，但新读者难以串起一次完整请求。
- 生产问题手册：实战性强，但基础机制会被按症状切碎。

### 3.2 内容分层

| 层 | 职责 | 本次处理 |
|---|---|---|
| 专题入口 | 建立心智模型和阅读顺序 | 深度重构 `[[llm-inference]]` |
| Concept | 解释跨项目稳定机制 | 更新已有机制页，补 3 个缺失概念 |
| Entity | 说明单个项目的定位、边界和采用条件 | 校准五个锚点项目 |
| Source | 保存 raw-backed 证据和分析时点 | 保持历史快照语义，不伪装成最新事实 |
| Analysis | 比较项目、组合层次、给出选型建议 | 重构项目地图和选型地图 |

## 4. 信息架构与页面范围

### 4.1 深度重构

| 页面 | 设计结果 |
|---|---|
| `wiki/concepts/llm-inference.md` | 专题首页；定义 workload、SLO、系统边界、聚合式热路径和端到端阅读地图 |
| `wiki/analysis/llm-inference-serving-project-map.md` | 用 request/event/control 三平面重画职责边界；更新项目版本、成熟度、组合关系和控制循环 |
| `wiki/analysis/llm-serving-engine-selection-map.md` | 从 workload 与 SLO 出发，先选 engine，再选 distributed runtime / K8s control plane / infrastructure |
| `wiki/concepts/disaggregated-serving.md` | 补齐 P/D 架构、KV handoff 时序、匹配策略、网络前提和失败边界 |
| `wiki/concepts/inference-routing.md` | 补齐 eligibility、admission、queue、cache/load scoring、endpoint picking 和 feedback loop |

### 4.2 机制校准

根据新的端到端主线，校准这些已有页面的定义、边界和交叉链接：

- `wiki/concepts/paged-attention.md`
- `wiki/concepts/radix-attention.md`
- `wiki/concepts/kv-cache-offload.md`
- `wiki/concepts/elastic-kv-cache.md`
- `wiki/concepts/batch-inference.md`
- `wiki/concepts/model-serving-operator.md`
- `wiki/entities/vllm.md`
- `wiki/entities/sglang.md`
- `wiki/entities/dynamo.md`
- `wiki/entities/llm-d.md`
- `wiki/entities/aibrix.md`

校准只补当前主线需要的内容，不复制对应 Source 页的源码级细节。

### 4.3 新增 Concept

仅新增三个现有页面无法清楚承载的稳定概念：

1. `wiki/concepts/continuous-batching.md`：iteration-level scheduling、waiting/running queue、token budget、prefill/decode 混排、chunked prefill、preemption。
2. `wiki/concepts/llm-serving-performance.md`：TTFT、ITL/TPOT、E2E latency、吞吐、goodput、并发、容量模型和 benchmark 方法。
3. `wiki/concepts/llm-serving-reliability.md`：admission、backpressure、bounded queue、timeout/cancel、retry、load shedding、worker loss、stale routing state 和降级。

### 4.4 导航与生成物

- 更新 `wiki/index.md` 的 LLM Serving 实体、概念、分析和阅读路径。
- 更新 `wiki/html-assets/build.py` 与 `wiki/html-assets/style.css`，支持通用 Mermaid 渲染。
- 运行 `wiki/html-assets/build.py` 重建受影响的 HTML 与主页/图谱。
- 在 `wiki/log.md` 追加 `## [2026-10-03] query | Optimize LLM Inference / Serving knowledge system`。

## 5. 图表体系

### 5.1 架构图：回答 What / Where

| ID | 图 | 主要页面 | 核心问题 |
|---|---|---|---|
| A1 | 端到端 serving 分层 | `llm-inference` | Client、Gateway、Platform、Engine、GPU/KV 的边界是什么？ |
| A2 | Engine V1 进程与执行边界 | `llm-inference`, `vllm`, `sglang` | API、EngineCore/Scheduler/KV、Worker/ModelRunner 如何分工？ |
| A3 | P/D 分离数据面 | `disaggregated-serving` | Prefill pool、KV transfer、Decode pool 如何连接？ |
| A4 | Kubernetes 控制面 | 项目地图 | Intent、Operator/Planner、worker pools、signals 如何形成闭环？ |

### 5.2 流程图：回答 Why / Decision

| ID | 图 | 主要页面 | 核心问题 |
|---|---|---|---|
| F1 | 一次 engine iteration | `continuous-batching` | 请求如何在 token budget 下组成 batch 并执行？ |
| F2 | KV block 生命周期 | `llm-inference`, `kv-cache-offload` | KV 如何 allocate、seal、reuse、offload 和 evict？ |
| F3 | 路由选点 | `inference-routing` | 如何从 eligible endpoints 计算 cache/load score 并反馈？ |
| F4 | 选型决策树 | 选型地图 | 如何从 workload/SLO 走到 engine、runtime/control 和 infra？ |

### 5.3 时序图：回答 When / Contract

| ID | 图 | 主要页面 | 核心问题 |
|---|---|---|---|
| S1 | 聚合式在线请求 | `llm-inference` | 从 Client 到 stream 的同步与异步步骤是什么？ |
| S2 | P/D 请求与 KV handoff | `disaggregated-serving` | prefill、transfer metadata/data、decode routing 和 stream 的先后关系是什么？ |
| S3 | 扩缩闭环 | 项目地图、`model-serving-operator` | metrics、decision、actuation 和 readiness 何时发生？ |
| S4 | 故障与降级 | `llm-serving-reliability` | timeout、cancel、stale index、worker loss 在哪些边界被处理？ |

### 5.4 绘图约束

- 每张图只回答一个主问题，并带标题、图注、前置假设和“不要从图中推断什么”。
- data plane 使用实线，event/control feedback 使用虚线；颜色只辅助分层，语义不依赖颜色。
- 项目名作为实现例子，不把某个项目的私有接口画成通用协议。
- 图的文字说明必须能独立表达关键结论，避免图形渲染失败后知识丢失。

## 6. Mermaid 通用渲染设计

Markdown 是图源的唯一事实来源。Builder 将 Markdown 生成的 `<pre><code class="language-mermaid">…</code></pre>` 转换为带原始源码的 Mermaid 容器，并只在包含 Mermaid 的页面注入固定版本的渲染脚本。

渲染要求：

1. 首次加载按当前深浅主题初始化 Mermaid。
2. 主题切换时使用保留的原始 Mermaid 文本重新渲染，不能对已生成 SVG 二次解析。
3. 图容器支持横向滚动、合理最小宽度和窄屏阅读。
4. 脚本未加载或渲染失败时保留可读的 Mermaid 源文本，并给出非阻塞错误提示。
5. 不含 Mermaid 的页面不加载 Mermaid 依赖。
6. Builder 的手工 HTML 保护规则保持不变；本次只增强自动生成页。

## 7. 最新上游证据边界

2026-10-03 的设计核验使用官方资料：

- vLLM V1：API Server、Engine Core、GPU Worker 与 DP Coordinator 的多进程边界，以及 KVCacheManager / hybrid KV 管理。
- SGLang：Scheduler、ModelRunner、RadixCache 与分布式/P-D 集成边界；具体 backend 能力仍按版本核验。
- Dynamo 最新稳定文档：request plane、event plane、service discovery、KV-aware router、PrefillRouter、NIXL KV transfer、Planner 与 Operator。
- llm-d 最新文档：Router（Proxy + EPP）、InferencePool、Model Server、P/D、KV management，以及 EPP metrics → KEDA → HPA；WVA 保持 deprecated / 历史设计标记。
- AIBrix v0.7：多引擎、Batch API、KV-centric P/D、高可用可插拔路由，以及 control plane / data plane 的明确边界；preview 能力必须标注成熟度。

这些观察写入 Analysis 或 Entity，并带核验日期与官方链接；历史 Source 页继续表示其既有分析时点。

## 8. 一致性与故障语义

知识内容必须保持以下边界：

- Router/EPP 选择目标，不等于代理数据流必然穿过 Router/EPP 进程。
- KV index 是位置/命中信号，不等于 KV 数据本身，也不能代替引擎有效性检查。
- Engine 内的 DP/TP/PP/EP 与跨实例的 P/D、routing/control plane 是不同层。
- retry 是否安全取决于是否已输出 token、采样状态能否恢复以及 backend 契约；不能写成通用透明重试。
- autoscaling 是异步控制循环，必须结合 queue、admission 和 load shedding 描述启动滞后。
- 性能比较同时报告 workload、模型、硬件、并行配置、输入/输出长度和 percentile，避免脱离条件比较吞吐。

## 9. 验证策略

### 9.1 内容结构

- 校验所有新/改页面的 YAML frontmatter 字段完整。
- 校验 12 个图 ID、标题和对应 Mermaid block 存在。
- 校验五个锚点项目与三个新增 Concept 均有入站链接。
- 校验 `wiki/index.md`、`wiki/log.md` 和阅读路径同步。
- 扫描断开的 `[[wikilink]]` 与孤儿页。

### 9.2 生成链路

- 运行 builder 两次并确认第二次无额外差异。
- 验证不含 Mermaid 的页面不注入 Mermaid 脚本。
- 验证含 Mermaid 的页面保留原始源码、生成容器并加载固定版本脚本。
- 用浏览器检查至少一个 flowchart 和一个 sequence diagram 的深色、浅色与窄屏表现。
- 模拟 Mermaid 加载失败，确认源码 fallback 仍可读。

### 9.3 内容抽查

- 从专题首页按阅读路径走一遍，确认三次点击内能到达七类关键主题。
- 抽查 aggregated、P/D、KV、routing、autoscaling 与 failure 图，确认箭头语义与正文一致。
- 对 vLLM、Dynamo、llm-d、AIBrix 的时效性事实回链官方资料；SGLang 的版本性细节只写入有官方证据支持的范围。

## 10. 交付与提交

实现完成并通过验证后，以一次 durable wiki operation 提交：

```text
query: Optimize LLM inference serving knowledge path
```

提交只包含本次专题相关页面、生成链路、生成 HTML、索引和日志；不包含工作区中既有的无关改动。
