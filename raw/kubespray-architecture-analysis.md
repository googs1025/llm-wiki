# Kubespray 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kubespray · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Kubespray 用 Ansible inventory/roles 部署生产可用 Kubernetes 集群，覆盖 kubeadm、network plugin、etcd、HA 和云/裸金属差异。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Cluster deployment inventory                                               │
│ Hosts, variables, networking, runtime, and add-ons define desired cluster  │
│ shape.                                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Kubespray Ansible playbooks                                                │
│ Roles prepare OS, container runtime, kubeadm, control plane, workers, and  │
│ CNI.                                                                       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Lifecycle operations                                                       │
│ Install, upgrade, scale, reset, and configure production Kubernetes        │
│ clusters.                                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Bare-metal, VM, or cloud Kubernetes clusters managed through repeatable    │
│ automation.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Inventory | hosts/group_vars/cluster config |
| Ansible roles | kubeadm/etcd/network/storage/addons |
| Playbooks | cluster.yml/upgrade/reset |
| Provider support | bare metal/cloud/on-prem |

## 关键数据流

```
用户准备 inventory
        │
        ▼
Ansible 配置 OS/runtime/etcd
        │
        ▼
kubeadm 初始化 control plane
        │
        ▼
加入 worker nodes
        │
        ▼
安装 CNI/addons 并验证
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Kubespray 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Cluster API 是 K8s-native 声明式生命周期；Kubespray 是 Ansible-based 集群安装/升级自动化。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `计算 / 集群部署` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Kubespray | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 计算 / 集群部署 | [[kubernetes]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Kubespray 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
