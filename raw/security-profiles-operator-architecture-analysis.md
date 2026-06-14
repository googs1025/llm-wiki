# Security Profiles Operator 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/security-profiles-operator · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Security Profiles Operator 管理 seccomp/AppArmor/SELinux profiles，并可通过 recording 把运行时行为转成可部署 profile。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Security Profiles Operator │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CRDs: Secc │ │ Daemon/control │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Recorder:  │ │ Admission/prof │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| CRDs | SeccompProfile, SelinuxProfile, ProfileRecording |
| Daemon/controller | install profiles on nodes |
| Recorder | capture syscalls/behavior |
| Admission/profile binding integrations | Admission/profile binding integrations |

## 关键数据流

```
用户声明或录制 profile
        │
        ▼
operator 分发到目标节点
        │
        ▼
Pod runtime 引用 profile
        │
        ▼
内核/runtime enforcement
        │
        ▼
状态和失败原因回写
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Security Profiles Operator 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：NetworkPolicy 管网络；SPO 管 syscall/LSM runtime confinement，适合高风险 workload 和 Agent sandbox 边界。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Runtime security` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Security Profiles Operator | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Runtime security | [[cloud-native-security]], [[agent-sandbox]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Security Profiles Operator 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
