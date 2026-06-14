---
title: apiserver-network-proxy 架构与设计思路分析
tags: [architecture, kubernetes, networking, control-plane]
date: 2026-06-14
sources: [apiserver-network-proxy-architecture-analysis.md]
related: ["[[apiserver-network-proxy]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# apiserver-network-proxy 架构与设计思路分析

> 原文：`raw/apiserver-network-proxy-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/apiserver-network-proxy · 优先级 P1

## 一句话定位

apiserver-network-proxy 通过 konnectivity server/agent 建立 apiserver 到节点网络的反向隧道，适合托管集群或私有节点网络。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ apiserver-network-proxy    │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Server: co │ │ Agent: node/cl │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ gRPC strea │ │ Integration: a │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Server | control-plane side proxy |
| Agent | node/cluster side tunnel |
| gRPC streams | multiplexed connections |
| Integration | apiserver egress selector |

## 关键数据流

```
agent 从节点侧连到 server
        │
        ▼
apiserver 需要访问 kubelet/service
        │
        ▼
请求进入 konnectivity server
        │
        ▼
通过 agent tunnel 转发到目标
        │
        ▼
响应回传给 apiserver
```

## 设计决策与哲学

- **补齐 `control plane network proxy` 维度**：apiserver-network-proxy 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它解决 control plane 到 node 网络连通，不是普通 Service mesh 或 Ingress。
- **选型价值**：它应和 [[kubernetes]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[apiserver-network-proxy]]
- [[kubernetes]]
- [[cloud-native-security]]
