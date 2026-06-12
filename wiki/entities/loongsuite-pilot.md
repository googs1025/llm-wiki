---
title: LoongSuite Pilot
tags: [entity, coding-agent, observability, telemetry, alibaba]
date: 2026-06-12
sources: [loongsuite-pilot-architecture-analysis.md]
related: [[coding-agent-observability]], [[token-usage-observability]], [[claude-code]], [[codex]], [[claude-tap]], [[tokscale]]
---

# LoongSuite Pilot

LoongSuite Pilot 是 Alibaba 开源的多 Agent AI coding telemetry collector，面向 [[claude-code]]、[[codex]]、Cursor、Qoder、QoderWork 等本地 coding agent 部署 hooks / plugin probes，并把 hook JSONL、SQLite、session、trace、CLI log 等输入统一成可上报的 AgentActivityEntry。详见 [[src-loongsuite-pilot-architecture]]。

## 架构边界

它不是 coding agent 执行器，也不是记忆系统或推理网关；它是本地常驻采集与观测层。核心边界是：

- `agents.d` 声明 detection、hook settings、events 和 deploy mode；
- `DeploymentManager` 负责部署/修复 hooks；
- `AgentDiscoveryService` 负责 fs.watch + polling 状态机；
- 输入基类负责增量读取本地数据；
- `InputManager` 统一执行 content policy 和 secret mask；
- Flusher fan-out 到 JSONL、SLS、HTTP、OTLP trace。

## 什么时候用

适合需要长期观察多种 coding agent 的团队或个人：想把 Claude Code / Codex / Cursor / Qoder 的 session、工具调用、token、trace、失败、运行健康统一接入本地 JSONL、SLS 或 OTel 后端时，它比单点脚本更成体系。

## 什么时候不用

如果目标只是临时查看某次 API 请求具体 prompt 和 streaming response，[[claude-tap]] 更直接；如果目标只是离线统计 token/cost，[[tokscale]] 更轻；如果目标是执行任务、远程驱动 agent 或做 sandbox 隔离，应看 [[codex]]、[[cc-connect]] 或 runtime/sandbox 类项目。

## 同类对比

| 项目 | 观测入口 | 主要回答 |
|------|----------|----------|
| [[loongsuite-pilot]] | hooks / SQLite / session / trace / CLI logs | 多 agent 活动如何统一采集、标准化和上报？ |
| [[claude-tap]] | 本地代理 | 某次真实请求到底发了什么上下文、工具 schema 和响应？ |
| [[tokscale]] | session 文件/数据库 | 哪些模型、client、workspace 花了多少 token 和成本？ |
