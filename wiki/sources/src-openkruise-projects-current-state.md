---
title: OpenKruise 组织项目当前状态核验
tags: [openkruise, kubernetes, project-map, backlog, cloud-native]
date: 2026-06-15
sources: [openkruise-projects-current-state.md]
related: ["[[openkruise-project-candidate-map]]", "[[openkruise-agents]]", "[[kubernetes]]", "[[k8s-core-controller-map]]", "[[cloud-native-security]]"]
---

# OpenKruise 组织项目当前状态核验

> 原文：`raw/openkruise-projects-current-state.md` · 核验日期：2026-06-15 · 来源：GitHub API `openkruise` organization repositories + `gh repo view` 复核重点仓库。

## 结论

当前 wiki 已完成 [[openkruise-agents]]。OpenKruise 生态还值得补的主线不是“把所有仓库都摄入”，而是围绕 Kubernetes workload 自动化形成几条清晰路线：

- workload enhancement：`openkruise/kruise`
- progressive delivery：`openkruise/rollouts`
- specialized workload：`openkruise/kruise-game`
- observability / operations：`openkruise/kruise-state-metrics`、`openkruise/kruise-dashboard`
- controller/operator isolation：`openkruise/controllermesh`
- deployment/API support：`openkruise/charts`、`openkruise/*-api`

## 重点仓库元数据

| 仓库 | stars | forks | 最近 push | release | 语言 | 定位 |
|---|---:|---:|---|---|---|---|
| `openkruise/kruise` | 5267 | 890 | 2026-06-08 | v1.8.3 / 2026-02-25 | Go | Automated management of large-scale applications on Kubernetes，CNCF incubating。 |
| `openkruise/rollouts` | 254 | 106 | 2026-06-13 | v0.6.2 / 2025-12-22 | Go | Enhanced Rollouts features for application automation。 |
| `openkruise/kruise-game` | 1059 | 169 | 2026-05-22 | v1.0.0 / 2025-07-21 | Go | Game Servers Management on Kubernetes。 |
| `openkruise/agents` | 202 | 78 | 2026-06-12 | v0.3.0 / 2026-05-15 | Go | Agent sandbox lifecycle management，已摄入 wiki。 |
| `openkruise/kruise-tools` | 55 | 30 | 2025-07-22 | v1.2.2 / 2025-06-23 | Go | Kruise libraries/tools。 |
| `openkruise/controllermesh` | 64 | 10 | 2023-05-30 | none | Go | controller/operator isolation and management。 |
| `openkruise/kruise-state-metrics` | 12 | 14 | 2025-04-28 | none | Go | OpenKruise CRD metrics addon。 |
| `openkruise/charts` | 16 | 49 | 2026-06-08 | agents-sandbox-manager-0.3.0 / 2026-05-22 | Mustache | OpenKruise Helm charts。 |
| `openkruise/kruise-dashboard` | 0 | 3 | 2025-11-19 | none | TypeScript | Dashboard for CloneSet / Advanced StatefulSet / Advanced DaemonSet。 |
| `openkruise/openkruise.io` | 21 | 98 | 2026-06-05 | none | JavaScript | OpenKruise documentation website。 |

## 支撑 / 暂缓仓库

| 仓库 | 判断 |
|---|---|
| `openkruise/kruise-api` | API definition repo，适合在 `openkruise/kruise` 摄入时引用，不建议单独建主实体。 |
| `openkruise/kruise-rollout-api` | Rollouts API definition repo，作为 `openkruise/rollouts` 辅助材料。 |
| `openkruise/agents-api` | Agents API definition repo，作为 [[openkruise-agents]] 后续补充。 |
| `openkruise/client-java` / `openkruise/client-rust` | SDK，除非做 OpenKruise client 多语言专题，否则不单独摄入。 |
| `openkruise/samples` | 示例材料，随主仓引用。 |
| `openkruise/community` / `summer_of_code` | 治理材料，不做架构页。 |
| `openkruise/website` | 已归档，迁移到 `openkruise.io`。 |
| `openkruise/controller-tools` | fork，不纳入候选。 |
| `openkruise/federation` / `controllermesh-api` / `game.openkruise.io` / `kruise-helm` / `kruise-argo` / `utils` | 当前更像旧实验、API/文档/插件材料，暂缓。 |

## 推荐优先级

```
P0: kruise, rollouts, kruise-game
P1: kruise-state-metrics, kruise-tools, kruise-dashboard, controllermesh
P2: charts, API definition repos, openkruise.io docs as supporting sources
```

[[openkruise-agents]] 已完成正式源码架构页，后续只需要在 OpenKruise 生态图中作为已收录项目引用。
