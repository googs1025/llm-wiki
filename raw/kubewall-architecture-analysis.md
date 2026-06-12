# kubewall 架构与设计思路分析

> 仓库：https://github.com/kubewall/kubewall · 分析日期：2026-06-12 · 版本：HEAD `fd575ff`（2026-05-19，ci: route middleware and build update）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`kubewall/kubewall` 是 single-binary K8s dashboard，仓库分为 Go backend、client、charts 和 media。它在 P1 中的价值是“AI integration 进入 K8s dashboard 管理体验”的对照样本，而不是完整 agent framework。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kubewall/kubewall` 是 single-binary K8s dashboard，仓库分为 Go backend、client… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `backend/cmd`, `backend/routes`, `backend/handlers` · `backend/event`, `backend/portfoward`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `client/src`                     │  │ `charts/kubewall`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `backend/cmd`, `backend/routes`, `backend/handlers` | Go dashboard server、路由和 handler。 |
| `backend/event`, `backend/portfoward` | 集群事件和端口转发。 |
| `client/src` | 前端 UI。 |
| `charts/kubewall` | Helm 安装。 |

## 关键数据流

1. 用户通过 dashboard 浏览资源。
2. backend 代理 K8s API、事件、port-forward 等能力。
3. AI 功能作为控制台辅助层接入。

## 设计决策与哲学

- single-binary/Helm 部署优先，降低运维门槛。
- 核心仍是 dashboard，AI 是增强层。
- 适合作为 k8m 的更轻对照。

## 与已有项目的对比

和 k8m 相比，kubewall 更 dashboard 基础设施；和 kubectl-ai 相比，它牺牲 CLI 灵活性换 UI 可视化。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
