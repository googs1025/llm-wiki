# CRI Tools 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/cri-tools · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

CRI Tools 提供 crictl 和 critest，用于操作与验证 kubelet Container Runtime Interface。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ CRI Tools                  │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ crictl: in │ │ critest: CRI c │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Runtime en │ │ Kubelet/runtim │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| crictl | inspect/run/exec/logs/images/pods |
| critest | CRI conformance/validation |
| Runtime endpoint config | Runtime endpoint config |
| Kubelet/runtime debugging workflow | Kubelet/runtime debugging workflow |

## 关键数据流

```
用户指定 CRI endpoint
        │
        ▼
crictl 调用 CRI gRPC
        │
        ▼
runtime 返回 pods/containers/images 状态
        │
        ▼
critest 执行 conformance cases
        │
        ▼
定位 kubelet/runtime 边界问题
```

## 设计决策与哲学

- **Kubernetes-native control plane**：CRI Tools 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：kubectl 面向 Kubernetes API；crictl 直接面向 CRI runtime，是节点级诊断工具。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `计算 / Runtime` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | CRI Tools | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 计算 / Runtime | [[kubernetes]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

CRI Tools 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
