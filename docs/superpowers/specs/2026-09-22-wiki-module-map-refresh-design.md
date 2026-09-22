# Wiki 模块地图与项目更新设计

## 背景

当前知识库包含 120 篇实体页、35 篇概念页、115 篇源摘要和 29 篇分析页。现有架构图主要集中在源摘要页，横向分析页大多依赖表格和文字：29 篇分析页中，只有少量页面包含 ASCII 架构图。部分源摘要已在 2026 年 9 月重新核验，但对应的横向项目地图仍停留在 6 月或 7 月，形成内容新旧不一致。

本设计将“项目事实更新”和“流程图重画”组织成可独立提交的主题域工作包，并增加跨模块地图，使读者既能理解单个项目，也能理解项目之间的职责、依赖和数据流。

## 目标

- 用稳定的模块边界组织项目，而不是按页面类型批量修改。
- 建立从全局生态、主题域到单项目流程的三级地图。
- 统一流程图语义，让不同项目可以横向比较。
- 明确哪些页面需要重画、核验、保留或延后。
- 区分当前 GitHub 观察、旧源摘要和分析推断。
- 每个模块可独立验证、提交和回滚。

## 非目标

- 不在一个 change 中更新全部 299 篇页面。
- 不为了统一视觉风格机械重画已有的高质量 ASCII 图。
- 不把短期实现细节固化为长期模块边界。
- 不在没有官方证据时补画推测性的组件或调用关系。
- 不修改 `raw/` 下的材料。

## 选定方案

采用“主题域为主、图表类型为辅”的混合拆分方式。每个主题域工作包执行相同流程：页面盘点、官方仓库核验、新旧证据对比、图表更新、wiki 同步和生成验证。

没有选择纯页面类型拆分，因为先统一修改全部 Source、Entity 或 Analysis 会割裂同一主题的上下文。也没有仅按主题自由发挥，因为这会造成不同模块的图表语言继续分化。

## 六个主题模块

### M1：Agent Experience / Framework

范围包括 Codex、Claude Code、Pi、AgentScope、Nanobot，以及 tool loop、plugin、skill、delegation 等交互和编程模型。

重点更新：

- `ai-agent-frameworks-map.md`
- `agent-framework-programming-model-map.md`
- `agent-skills-plugin-system-map.md`
- `coding-agent-selection-map.md`
- Codex、Claude Code、Pi 的工具调用、权限与 sandbox 流程
- AgentScope、Nanobot 的 event/ReAct loop

优先级：P1。

### M2：Memory / Context

范围包括 claude-mem、Agent Recall、AgentMemory、Mem0、ReMe、PowerMem、MemSearch 和 TencentDB Agent Memory。

重点更新：

- `agent-memory-project-map.md`
- `agent-memory-selection-matrix.md`
- capture → consolidate → source-of-truth/index → retrieve → inject 的共同生命周期
- source-of-truth 与 shadow index 的一致性关系
- memory scope、遗忘、冲突和注入边界

优先级：P0。现有横向分析内容较完整，但缺少模块图。

### M3：Runtime / Sandbox / Gateway

范围包括 agent-sandbox、OpenKruise Agents、AgentCube、OpenShell、NemoClaw、HiClaw 和 agentgateway。

重点更新：

- 保留 2026 年 9 月更新的 Runtime/Sandbox 分析图
- 重画 sandbox 原语、平台层、会话编排层和 host-side agent 的层级关系
- 补充 credential、egress、gateway 和 policy enforcement 的横切位置
- 重新核验 2026 年 5–6 月形成的 agent-sandbox、OpenShell、agentgateway 源摘要

优先级：P1。

### M4：Inference / Serving / Routing

范围包括 vLLM、SGLang、Dynamo、llm-d、AIBrix、KServe、KubeAI、OME、GPUStack 及相关路由、KV cache、P/D 分离和 autoscaling 项目。

重点更新：

- `llm-inference-serving-project-map.md`
- `llm-serving-engine-selection-map.md`
- Gateway / EPP / Router → Prefill → KV transfer → Decode → streaming 的请求流
- metrics / KV events → planner / autoscaler → operator → worker pools 的控制流
- KV block 的创建、索引、跨 worker 传输、offload 和 eviction
- 保留 vLLM、SGLang、Dynamo、llm-d 源摘要中的引擎内部图，统一命名和图例

优先级：P0。相关源摘要已在 2026 年 9 月更新，而横向分析页仍主要反映 6 月结构。

### M5：Kubernetes Platform / GPU

范围拆成三条支线：

1. controller 工具链：client-go、controller-runtime、Kubebuilder、controller-tools。
2. workload 与调度：Kueue、JobSet、LeaderWorkerSet、scheduler-plugins、Karpenter。
3. device 与 GPU：Node Feature Discovery、GPU Operator、device plugin、DRA、CDI、HAMi 和 GPU sharing。

重点更新：

- `k8s-core-controller-map.md`
- `k8s-gpu-device-stack.md`
- DRA、scheduler、workload 和 node 设计分析页
- 从声明式 API 到 controller reconcile、Pod admission、node provisioning 和 GPU 分配的端到端控制循环

优先级：P0。项目数量最多，且现有横向分析页几乎没有图。

### M6：Code Intelligence / Knowledge Ops

范围包括 Claude Context、GitNexus、DeepWiki Open、Code Review Graph，以及 semantic search、code graph、Graph RAG 和 repo wiki generation。

重点更新：

- `code-semantic-search-rag-map.md`
- parse → index/graph → retrieve → generate/review 的数据流
- 代码事实源、派生索引和自动 wiki 之间的刷新与失效关系

优先级：P2。

## 三层模块地图

### L0：全局生态关系图

放在总索引或全局入口页，表达稳定的主干关系：

```text
Agent Experience
      ↓
Framework / Memory
      ↓
Runtime / Sandbox
      ↓
Gateway / Routing
      ↓
Inference Engine / KV
      ↓
Kubernetes Workload / GPU

横切：Security / Credential、Observability / Benchmark、Code Intelligence
```

L0 只表达职责依赖，不塞入项目实现细节。

### L1：主题域模块图

放在 Analysis 页面，表达模块边界、代表项目、控制面/数据面、状态归属和上下游依赖。项目跨域时只设置一个主归属，其他模块用引用或虚线依赖连接。

### L2：项目流程图

放在 Source 页面，表达一次真实请求、一次 reconcile、一次 memory 写入或一次 sandbox session 的路径。L2 必须链接回所属 L1 模块图。

## 统一图表类型

### D1：模块边界图

回答“谁负责什么、边界在哪里”。每个 L1 Analysis 页面必须有一张。

### D2：请求或热路径图

回答“一次真实请求经过哪里”。只保留同步关键路径，不混入异步控制面。

### D3：控制循环图

回答“配置、观测、决策和执行如何闭环”。适用于 operator、planner、autoscaler 和长期运行的 agent service。

### D4：状态或数据生命周期图

回答 KV、memory、session、credential、index 等状态由谁创建、保存、转移、失效和回收。

### D5：故障与降级图

仅在失败语义决定架构时增加，例如 worker crash、route drain、request migration、缓存丢失、credential 泄漏边界、重试和回滚。

每个模块必须包含 D1，并从 D2–D4 中选择与该领域最相关的图。D5 按需使用。图太密时拆图，不制作包含所有信息的“万能图”。

## 单模块处理流程

1. 先读 `wiki/index.md`，盘点相关 Analysis、Entity、Concept 和 Source 页面。
2. 查看官方仓库 README、文档、目录结构、近期 release/tag 和重要提交。
3. 对比当前观察与既有 Source 摘要，记录一致、变化、冲突和待核验项。
4. 先完成 L1/D1，再补真正有解释价值的 L2/D2–D5。
5. 同步 Entity、Concept、Analysis、Index 和 Log；Source 页只在证据链清晰时更新。
6. 重建 HTML，验证 frontmatter、wikilink、reading path 和知识图谱。
7. 一个模块一次提交，避免不同主题共同进入同一提交。

## 证据与冲突规则

- 当前 GitHub 观察标注核验日期、tag、commit 或文档版本。
- 官方 README、官方文档、仓库代码和 release 是当前事实的主要证据。
- 旧 raw/source 笔记不静默改写；出现冲突时按仓库规则在相关页面加入 Conflict callout。
- 仓库明确说明和分析推断分开表达。
- 无法确认的关系标为“待核验”，不凭常识补箭头。
- Source 摘要中的密集 ASCII 图继续遵守原图保真要求。

## 执行顺序

第一批：

1. M4 Inference / Serving / Routing
2. M2 Memory / Context
3. M5 Kubernetes Platform / GPU

第二批：

4. M3 Runtime / Sandbox / Gateway
5. M1 Agent Experience / Framework

第三批：

6. M6 Code Intelligence / Knowledge Ops
7. 回补全局 L0 地图，并检查跨模块引用

M4 首先执行，因为近期源摘要已更新，可以低成本验证新图表体系。M2 和 M5 随后处理，因为两者横向内容丰富但图表缺口最大。

## 单模块完成标准

- L1 地图覆盖模块边界、主要项目和上下游。
- 关键项目至少有一张真实流程图，不只有组件列表。
- 图中每个项目均有 Entity 或 Source 落点。
- 当前事实、旧来源和推断清晰区分。
- 新增或提升的重要概念同步到 Concept 页面。
- `wiki/index.md` 和 reading path 可以进入新增内容。
- `wiki/log.md` 记录本次 durable wiki 更新。
- `wiki/html-assets/build.py` 构建成功。
- 无新增 frontmatter 缺失、wikilink 断链或明显 orphan 页面。
- 生成的 HTML 索引和关系图反映源 Markdown 的更新。

## 风险与控制

- **范围失控**：每次只完成一个模块，跨模块发现进入后续 backlog。
- **重复绘图**：项目只保留一个主归属图，其他页面使用 wikilink 引用。
- **图表过密**：边界、热路径、控制循环和状态生命周期分开绘制。
- **内容过时**：实施前重新核验官方仓库，不直接照搬旧 Source 摘要。
- **生成层领先于知识源**：先更新 Markdown，再运行 HTML 构建器；不在生成 HTML 中单独维护新知识。
- **ASCII 图损坏**：涉及源摘要时比较原始材料与摘要中的框线结构，避免压缩或表格化替代。

## 验证策略

- 针对本模块运行 frontmatter 与 wikilink 检查。
- 对新图执行人工可读性检查：方向一致、箭头语义明确、控制面和数据面可区分。
- 对 Source 摘要执行 ASCII 框线保真检查。
- 运行 `./wiki/html-assets/build.py`。
- 检查生成首页、主题 Analysis 页面和至少两个 L2 Source 页面。
- 验证 L0 → L1 → L2 以及 L2 → L1 的双向导航。
- 审查 `git diff --check` 和最终变更范围后提交。
