---
title: apiserver-network-proxy
tags: [entity, kubernetes, networking, control-plane]
date: 2026-06-14
sources: [apiserver-network-proxy-architecture-analysis.md]
related: ["[[apiserver-network-proxy]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# apiserver-network-proxy

apiserver-network-proxy 通过 konnectivity server/agent 建立 apiserver 到节点网络的反向隧道，适合托管集群或私有节点网络。 详见 [[src-apiserver-network-proxy-architecture]]。

## 架构边界

它解决 control plane 到 node 网络连通，不是普通 Service mesh 或 Ingress。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `control plane network proxy` 能力 | 适合，apiserver-network-proxy 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[cloud-native-security]] 组合。 |

## 核心组件

- Server: control-plane side proxy
- Agent: node/cluster side tunnel
- gRPC streams: multiplexed connections
- Integration: apiserver egress selector

## 选型提示

把 apiserver-network-proxy 放在 `control plane network proxy` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
