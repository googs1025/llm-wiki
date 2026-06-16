---
title: OpenKruise 项目候选地图
tags: [openkruise, kubernetes, project-map, backlog, cloud-native]
date: 2026-06-15
sources: [src-openkruise-projects-current-state, src-openkruise-agents-architecture]
related: ["[[openkruise-agents]]", "[[openkruise-kruise]]", "[[openkruise-rollouts]]", "[[kruise-game]]", "[[kruise-state-metrics]]", "[[kruise-tools]]", "[[kruise-dashboard]]", "[[controllermesh]]", "[[kubernetes-workload-automation]]", "[[kubernetes]]", "[[k8s-core-controller-map]]", "[[cloud-native-security]]", "[[model-serving-operator]]", "[[agent-runtime-sandbox-project-map]]"]
---

# OpenKruise 项目候选地图

这页把 `openkruise` GitHub 组织里值得纳入 wiki 的项目按工程价值排序。目标不是收集全部仓库，而是补齐 Kubernetes workload automation、progressive delivery、specialized workload、observability 和 controller/operator isolation 这些架构维度。

本次核验基于 GitHub API 当前公开仓库元数据（2026-06-15）。当前已收录的正式源码架构页是 [[openkruise-agents]]；本页中的 P0/P1 候选已经补成实体页，并统一归入 [[kubernetes-workload-automation]] 这个整体概念，而不是按每个项目维度继续拆概念页。

## 总体分层

```
OpenKruise ecosystem
        │
        ├─ Workload enhancement: [[openkruise-kruise]]
        │      CloneSet / Advanced StatefulSet / SidecarSet / UnitedDeployment
        │      WorkloadSpread / ImagePullJob / ContainerRecreateRequest
        │
        ├─ Progressive delivery: [[openkruise-rollouts]]
        │      rollout strategy / traffic routing / batch release / canary
        │
        ├─ Specialized workload: [[kruise-game]]
        │      game server set / ops state / network / lifecycle
        │
        ├─ Agent sandbox: agents  已收录为 [[openkruise-agents]]
        │
        └─ Operations: metrics / dashboard / tools / charts / API definitions
```

## P0：应优先摄入

| 项目 | 当前状态 | 加入价值 | 应进入的 wiki 主题 |
|---|---|---|---|
| [[openkruise-kruise]] | 5267 stars，最近 push 2026-06-08，release v1.8.3，CNCF incubating | OpenKruise 主仓，是理解 Kubernetes workload 增强的核心入口。重点是 CloneSet、Advanced StatefulSet、Advanced DaemonSet、SidecarSet、UnitedDeployment、WorkloadSpread、ImagePullJob 等比原生 Deployment/StatefulSet 更细的自动化控制。 | [[k8s-core-controller-map]]、[[kubernetes]]、[[kubernetes-workload-automation]] |
| [[openkruise-rollouts]] | 254 stars，最近 push 2026-06-13，release v0.6.2 | 渐进式发布 / enhanced rollout 控制面。适合和 Argo Rollouts、原生 Deployment rollout、Gateway/Ingress 流量切分对比。 | [[kubernetes-workload-automation]]、[[gitops]]、流量治理、发布控制面 |
| [[kruise-game]] | 1059 stars，最近 push 2026-05-22，release v1.0.0 | Kubernetes game server management，场景独特且成熟度相对高。适合对比 Agones、StatefulSet、GameServerSet、专用 workload operator。 | [[kubernetes-workload-automation]]、specialized workload operator、游戏服务器 |

## 已收录

| 项目 | 当前状态 | wiki 位置 | 后续动作 |
|---|---|---|---|
| [openkruise/agents](https://github.com/openkruise/agents) | 202 stars，最近 push 2026-06-12，release v0.3.0 | [[openkruise-agents]] / [[src-openkruise-agents-architecture]] | 后续可补 `agents-api` 和 charts 作为部署/API 支撑材料，不需要重新排进 P0。 |

## P1：专题补强

| 项目 | 当前状态 | 加入价值 | 建议处理 |
|---|---|---|---|
| [[kruise-state-metrics]] | 12 stars，最近 push 2025-04-28 | OpenKruise CRD metrics addon，适合补 kube-state-metrics / Prometheus 体系下的自定义 workload 可观测。 | 已建实体页；后续若摄入主仓，可补更细的 metrics schema。 |
| [[kruise-tools]] | 55 stars，最近 push 2025-07-22，release v1.2.2 | Kruise libraries/tools，偏工具链与开发/运维辅助。 | 已建实体页；作为主仓工具链支撑引用。 |
| [[kruise-dashboard]] | 0 stars，最近 push 2025-11-19 | CloneSet / Advanced StatefulSet / Advanced DaemonSet dashboard，补 OpenKruise 运维入口。 | 已建实体页；后续可放入 Kubernetes dashboard / ops UI 对比。 |
| [[controllermesh]] | 64 stars，最近 push 2023-05-30 | controller/operator isolation 管理方案，概念有价值但活跃度低。 | 已建实体页并接入 [[kubernetes-workload-automation]] 的 controller operation boundary，作为 controller 高可用、隔离和多 operator 管理设计参考。 |

## P2：支撑材料

| 项目 | 用法 |
|---|---|
| [openkruise/charts](https://github.com/openkruise/charts) | Helm 部署材料。适合作为 `kruise`、`rollouts`、[[openkruise-agents]] 摄入时的部署来源，不建议单独做实体页。 |
| [openkruise/kruise-api](https://github.com/openkruise/kruise-api) | `kruise` API definition repo，摄入主仓时引用。 |
| [openkruise/kruise-rollout-api](https://github.com/openkruise/kruise-rollout-api) | `rollouts` API definition repo，摄入 Rollouts 时引用。 |
| [openkruise/agents-api](https://github.com/openkruise/agents-api) | [[openkruise-agents]] API definition repo，后续补充 API 演进时引用。 |
| [openkruise/openkruise.io](https://github.com/openkruise/openkruise.io) | 官方文档站。每个正式 `$ingest-codebase` 都应同时看对应文档。 |

## 暂不建议单独加入

| 项目 | 原因 |
|---|---|
| `openkruise/website` | 已归档，迁移到 `openkruise.io`。 |
| `openkruise/controller-tools` | fork，不适合作为 OpenKruise 生态主项目。 |
| `openkruise/client-java` / `openkruise/client-rust` | SDK，除非后续做多语言 client 对比。 |
| `openkruise/samples` / `community` / `summer_of_code` | 示例和治理材料，可作为背景，不做架构页。 |
| `openkruise/federation` / `controllermesh-api` / `game.openkruise.io` / `kruise-helm` / `kruise-argo` / `utils` | 当前更像旧实验、API/文档/插件材料，优先级低。 |

## 推荐实施顺序

1. `$ingest-codebase https://github.com/openkruise/kruise`，扩写 [[openkruise-kruise]]。
2. `$ingest-codebase https://github.com/openkruise/rollouts`，扩写 [[openkruise-rollouts]]，并同步更新 [[kubernetes-workload-automation]] 中的 release governance 部分。
3. `$ingest-codebase https://github.com/openkruise/kruise-game`，扩写 [[kruise-game]]。
4. 视主仓内容决定是否单独补 `kruise-state-metrics`
5. 如果要研究 controller/operator isolation，再补 `controllermesh`

## 和现有知识库的关系

- [[k8s-core-controller-map]] / [[kubernetes-workload-automation]]：[[openkruise-kruise]] 可以补齐“原生 workload 之外的增强 workload controller”路线。
- [[cloud-native-security]]：`SidecarSet`、`ImagePullJob`、runtime hooks 和 workload spread 会影响节点/镜像/sidecar/变更安全边界。
- [[agent-runtime-sandbox-project-map]]：[[openkruise-agents]] 已经接入 Agent sandbox 路线，后续可补 `agents-api` 作为 API source。
- [[model-serving-operator]] / AI infra：`kruise` 的 workload spread、pre-download image、advanced StatefulSet 可能为大模型服务滚动、镜像预热和多可用区部署提供对照。
