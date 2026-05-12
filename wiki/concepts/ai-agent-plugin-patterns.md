---
title: AI Agent 外挂的 9 条设计原则
tags: [design-pattern, ai-agent, llm-infra, architecture]
date: 2026-05-12
sources: [src-claude-context-architecture, src-claude-mem-architecture]
related: [[claude-context]], [[claude-mem]], [[event-driven-memory-pipeline]], [[ai-as-compressor]], [[merkle-dag-fingerprint]], [[hybrid-search-rrf]]
---

# AI Agent 外挂的 9 条设计原则

构建"AI Agent 外挂"工具（MCP 插件、Hook 插件、记忆系统、RAG 系统）的通用工程经验。从 [[claude-context]] 与 [[claude-mem]] 两个开源项目抽象而来。

## 适用对象

任何**给 Agent 加外部能力**的工具：

- MCP / A2A 协议插件
- Agent runtime 的 Lifecycle Hook（如 Claude Code）
- RAG / 向量检索系统
- 长期记忆系统
- 代码理解 / 文档检索工具

## 9 条原则

### 1. 三段式接口分层（抽象 / 协议 / 引擎）

```
客户端层  →  协议层  →  引擎层
(UI)       (MCP)     (纯领域逻辑)
```

- 引擎层不感知协议——明天换 A2A 只动外层
- 协议层只做转换 + 状态管理
- 客户端独立 UI

**case**：claude-context 把核心拆成 `packages/core`、`packages/mcp`、`packages/vscode-extension`，引擎层完全不知道 MCP 存在。

### 2. 所有外部依赖都做成 Strategy Pattern

```ts
abstract class Embedding {
  abstract embed(text: string): Promise<Vector>
}
// OpenAI / Voyage / Gemini / Ollama 各自实现
```

LLM、向量库、记忆存储——凡是外部 SDK 一律包接口。本地 Ollama 还是云端 GPT-5 只是配置切换。

**case**：claude-context 的 4 种 embedding × 2 种 vectordb × 2 种 splitter 可任意组合。

### 3. 降级链（Graceful Degradation）

```
AST 解析 ─┐
         ├─失败→ LangChain 字符切分 ─┐
         │                         ├─失败→ 跳过该文件，记日志
         ▼                         ▼
   完整语义块                    最小可用
```

**永不让一个边缘 case 卡死整个 pipeline**。Agent 调用工具失败时应有"次优工具"或"裸 LLM 兜底"。

### 4. Merkle DAG 做状态指纹

详见 [[merkle-dag-fingerprint]]。

不只是文件，对话历史去重、知识库增量、工具调用缓存都适用。**用内容 hash 而非时间戳/版本号**。

### 5. 协议通道纪律：stdout 只跑协议

```ts
// MCP 服务第一行代码
console.log = (...args) => process.stderr.write('[LOG] ' + args.join(' ') + '\n');
```

任何与 Agent 通信的进程（stdin/stdout 管道、Unix socket、MCP server）都要**第一行就收紧 stdout**。一个 `console.log("debug")` 就让协议全炸。

### 6. 协作式取消（AbortSignal）穿透整个调用栈

```ts
async indexCodebase(..., signal?: AbortSignal)
  async processFileList(..., signal?: AbortSignal) {
    if (signal?.aborted) throw new IndexAbortError()
  }
```

长时任务（爬取、批量推理、链式工具调用）必须从入口透传 signal 到最底层。否则用户"取消"按钮就是骗人的。

**case**：claude-context issue #199——`clear_index` 返回后后台仍在写"已清空"的 collection，加 signal 在文件边界自检才修好。

### 7. 流式批处理（Streaming Batches）

```
读 → 处理 → 写
batch=100 滚动
内存常驻一个 batch，而非整个数据集
```

RAG 索引、文档处理、批量评测——一律流式。配合协作式取消，可中断的进度也是用户体验。

### 8. 快照自愈 vs. 信任快照

```
启动
  ↓
读 snapshot
  ↓
vs. source of truth 对账
  ├─ 一致 → 信任
  └─ 不一致 → 修复或删除
```

**永远假设你的持久化状态是脏的**。

**case**：claude-context issue #295——旧版本的 `{indexedFiles:0, totalChunks:0}` 被客户端误判为未索引→触发 force reindex→无限循环。启动时用 Milvus 真实行数对账才修复。

[[claude-mem]] 的 outbox 重试机制也是同一思路：AI 生成非确定，状态可能脏，必须能恢复。

### 9. 混合检索而非单一检索

详见 [[hybrid-search-rrf]]。

| 信号 | 用途 |
|------|------|
| 向量相似度 | 语义匹配 |
| 关键词 / BM25 | 精确符号 |
| 时间衰减 | 最近优先（记忆场景） |
| metadata 过滤 | 业务约束 |

RRF 合并：`score = Σ 1/(k + rank_i)`。多路召回是企业级 RAG 标配。

---

## 迁移检查表

构建任何"AI Agent 外挂"工具时逐项检查：

- [ ] **分层**：引擎层是否完全不感知协议层？换协议是否只动外层？
- [ ] **接口化**：外部 SDK（LLM、DB、Embedding）是否都有抽象接口？
- [ ] **降级**：每个工具是否有 fallback 路径？整个 pipeline 是否"永不崩"？
- [ ] **指纹**：增量更新是否用内容 hash 而非时间戳？
- [ ] **通道**：协议通道（stdout/socket）是否被无关日志污染？
- [ ] **取消**：长时任务能否在任意点中断？signal 是否透传到最底层？
- [ ] **流式**：是否一次性加载整个数据集？能否改成 batch 滚动？
- [ ] **自愈**：启动时是否做状态对账？快照损坏是否能恢复？
- [ ] **多路召回**：检索/记忆是否只用单一信号？能否多路并行 + RRF 合并？

## 与其他设计概念的联动

| 原则 | 相关概念页 |
|------|----------|
| #4 Merkle 指纹 | [[merkle-dag-fingerprint]] |
| #9 混合检索 | [[hybrid-search-rrf]] |
| #1-3, #7-8 | [[event-driven-memory-pipeline]] 的边缘/后台分层、outbox |
| AI 调用边界 | [[ai-as-compressor]] |

## 参考

- [[src-claude-context-architecture]]（来源 + 9 条原则的原文）
- [[src-claude-mem-architecture]]（多个原则的另一组佐证）
