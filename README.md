# LLM Wiki

个人 LLM / AI Agent / 云原生 / 推理基础设施知识库。

这个仓库不是一个普通代码项目，而是一个持续整理的技术知识库：原始材料保存在 `raw/`，经过 LLM 辅助分析后沉淀到 `wiki/`，并生成可本地浏览的静态 HTML 页面。

## 从哪里开始

- 总索引：[`wiki/index.md`](wiki/index.md)
- 操作日志：[`wiki/log.md`](wiki/log.md)
- 本地 HTML 入口：[`wiki/html/index.html`](wiki/html/index.html)
- Agent 维护规则：[`AGENTS.md`](AGENTS.md)

如果只是阅读内容，优先从 `wiki/index.md` 或 `wiki/html/index.html` 进入；如果要继续维护知识库，先读 `AGENTS.md`。

## 推荐阅读路径

当前知识库的主线集中在 AI Agent 工程、长期记忆、运行时隔离、LLM serving 和 Kubernetes 平台工程。

### AI Agent / Memory

- [`Agent Memory 项目地图`](wiki/analysis/agent-memory-project-map.md)：横向比较 `claude-mem`、`agent-recall`、`agentmemory`、`powermem`、`memsearch`、`TencentDB-Agent-Memory`，重点看 memory 写入方式、事实源、检索与注入路径。
- [`AI Agent Frameworks 项目地图`](wiki/analysis/ai-agent-frameworks-map.md)：把 coding agent、Agent framework、MCP、skills、memory、runtime substrate 放在同一张生态图里看。

### Agent Runtime / Sandbox

- [`Agent Runtime / Sandbox 项目地图`](wiki/analysis/agent-runtime-sandbox-project-map.md)：整理 `agent-sandbox`、`AgentCube`、`OpenShell`、`NemoClaw`、`HiClaw`、`AgentScope`、`agentgateway` 的分层关系。

### LLM Inference / Serving

- [`LLM Inference / Serving 项目地图`](wiki/analysis/llm-inference-serving-project-map.md)：比较 `vLLM`、`SGLang`、`Dynamo`、`SkyPilot` 与 Kubernetes GPU stack 的职责边界。

### Kubernetes / Cloud Native

- [`Kubernetes`](wiki/entities/kubernetes.md)：K8s 相关源文件与概念的入口。
- [`K8s Core & Controllers Star 项目清单`](wiki/sources/src-k8s-core-controllers-stars.md)：controller/operator/API machinery/调度/多集群等方向的项目地图。
- [`K8s GPU & Device Plugins Star 项目清单`](wiki/sources/src-k8s-gpu-device-plugins-stars.md)：GPU device plugin、DRA/CDI、GPU sharing、可观测与诊断方向的项目地图。

## 内容结构

```text
raw/            # 原始材料，视为不可变输入
  assets/       # 图片和附件
wiki/           # LLM 生成和维护的知识页
  index.md      # 知识库总索引
  log.md        # 操作日志
  entities/     # 项目、组织、工具等实体页
  concepts/     # 方法、原则、技术概念页
  sources/      # 原始材料的结构化摘要
  analysis/     # 面向问题的横向分析文章
  html/         # 静态 HTML 输出
  html-assets/  # HTML 构建脚本与样式
```

知识页之间使用 `[[wikilink]]` 连接，便于在 Obsidian 或生成后的 HTML 中沿着主题关系阅读。

## 维护方式

维护规则以 [`AGENTS.md`](AGENTS.md) 为准。README 只保留几个原则：

- 不直接修改 `raw/` 下的原始材料。
- 新增或更新 wiki 页面时保持 YAML frontmatter 和 `[[wikilink]]`。
- 新 source 进入 `wiki/sources/`，实体与概念沉淀到 `wiki/entities/` 和 `wiki/concepts/`。
- 横向总结、选型判断和工程模式分析进入 `wiki/analysis/`。
- 内容更新后同步维护 `wiki/index.md` 和 `wiki/log.md`。

## 本地 HTML 构建

生成静态 HTML：

```bash
./wiki/html-assets/build.py
```

构建结果写入 `wiki/html/`。其中部分手工维护的 HTML 页面会被构建脚本跳过，避免覆盖自定义内容。

## 当前关注方向

- AI Agent 长期记忆：采集、压缩、检索、注入、scope 隔离与事实一致性。
- Agent runtime / sandbox：有状态会话、隔离执行、凭据托管、策略控制与网关治理。
- LLM serving：PagedAttention、RadixAttention、Prefill/Decode 分离、KV cache offload 与多云算力编排。
- Kubernetes 平台工程：controller/operator、GPU 资源栈、多集群、GitOps、可观测与 AI Ops。
