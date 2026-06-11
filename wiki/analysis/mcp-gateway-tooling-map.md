---
title: MCP Server / Tool Gateway 对比地图
tags: [mcp, ai-gateway, tooling, project-map, selection]
date: 2026-06-11
sources: [src-ai-agent-frameworks-stars, src-agentgateway-architecture]
related: [[mcp]], [[agentgateway]], [[gateway-api]], [[agent-credential-isolation]], [[ai-agent-frameworks-map]]
---

# MCP Server / Tool Gateway 对比地图

MCP 生态已经从“给 Agent 接几个工具”扩展成三层：SDK/framework、具体工具 server、gateway/proxy/data plane。本页把 FastMCP、官方/垂直 MCP server 和 agentgateway/Plano 放在一起看。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 定位 |
|------|------|-----------|-------|--------|------|
| FastMCP | https://github.com/PrefectHQ/fastmcp | 2026-06-06 | 25k | Python | Pythonic MCP servers/clients |
| GitHub MCP | https://github.com/github/github-mcp-server | 2026-06-10 | 30k | Go | GitHub 官方 MCP server |
| Playwright MCP | https://github.com/microsoft/playwright-mcp | 2026-06-10 | 33k | TypeScript | 浏览器自动化 MCP server |
| kubectl MCP | https://github.com/rohitg00/kubectl-mcp-server | 2026-04-08 | 908 | Python | Kubernetes MCP server |
| [[agentgateway]] | https://github.com/agentgateway/agentgateway | 2026-06-10 | 3.2k | Rust | LLM/MCP/A2A agentic proxy |
| Plano | https://github.com/katanemo/plano | 2026-06-09 | 6.5k | Rust | AI-native proxy and data plane |

## 分层

| 层 | 代表 | 解决的问题 |
|----|------|------------|
| MCP SDK/framework | FastMCP, MCP Python SDK | 快速写 server/client，处理 schema、transport、lifecycle |
| Tool server | GitHub MCP, Playwright MCP, kubectl MCP | 把 GitHub、浏览器、K8s 等具体能力暴露给 Agent |
| Gateway/proxy | [[agentgateway]], Plano | federation、鉴权、RBAC、observability、routing、policy |

## 选型

| 需求 | 选择 |
|------|------|
| 快速给内部 API 写 MCP server | FastMCP |
| 让 Agent 操作 GitHub issue/PR/repo | GitHub MCP |
| 让 Agent 控浏览器做验证/抓取 | Playwright MCP |
| 让 Agent 读 K8s 集群状态 | kubectl MCP，但要强 RBAC 和只读优先 |
| 多 MCP server federation + policy | [[agentgateway]] |
| Agentic app data plane / smart routing | Plano |

## 架构差异

| 维度 | FastMCP | GitHub MCP | Playwright MCP | kubectl MCP | [[agentgateway]] / Plano |
|------|---------|------------|----------------|-------------|--------------------------|
| 抽象 | SDK/framework | domain server | browser server | K8s server | gateway/proxy |
| 主要风险 | schema/鉴权自建 | token 权限过宽 | 浏览器可执行外部站点动作 | 集群权限过宽 | 策略和路由复杂 |
| 运维边界 | app 进程 | server + GitHub token | browser runtime | kubeconfig / RBAC | 数据面 + 控制面 |
| 适合规模 | 单 server 到中型 | team / repo workflow | 自动化测试/浏览器任务 | 集群诊断 | 多 server / 多 Agent / 多租户 |

## 避坑条件

- MCP server 默认不是安全边界；凭据、RBAC、allow-list 要外置治理。
- Browser/K8s/GitHub 这类高权限工具必须最小权限启动。
- 多 server 组合时，不要让 Agent 直接持有所有 token；应通过 [[agent-credential-isolation]] 和 gateway 管控。
- “支持 MCP”不等于可观测；生产环境要记录 tool call、参数、结果、token 和审批。

