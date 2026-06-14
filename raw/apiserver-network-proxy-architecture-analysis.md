# apiserver-network-proxy 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/apiserver-network-proxy · 分析日期：2026-06-14 · 优先级：P1

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

| 层 / 模块 | 主要职责 |
|----------|----------|
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

- **Kubernetes-native control plane**：apiserver-network-proxy 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它解决 control plane 到 node 网络连通，不是普通 Service mesh 或 Ingress。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `control plane network proxy` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | apiserver-network-proxy | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | control plane network proxy | [[kubernetes]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

apiserver-network-proxy 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
