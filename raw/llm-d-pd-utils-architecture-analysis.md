# llm-d P/D Utils 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-pd-utils · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

llm-d P/D Utils 是面向 Prefill/Decode 分离部署的 skills/scripts 工具集，用于 preflight、GPU topology、RDMA/NCCL/network/NIXL 等诊断。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ llm-d P/D Utils            │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Preflight  │ │ GPU topology c │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Network/RD │ │ Agentic skills │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Preflight scripts | cluster and runtime checks |
| GPU topology checks | GPU topology checks |
| Network/RDMA/NCCL diagnostics | Network/RDMA/NCCL diagnostics |
| Agentic skills/workflows for P/D deployment | Agentic skills/workflows for P/D deployment |

## 关键数据流

```
用户选择 P/D 诊断任务
        │
        ▼
脚本收集节点/GPU/网络信息
        │
        ▼
执行连通性和通信测试
        │
        ▼
输出失败项和建议
        │
        ▼
部署前修复基础设施问题
```

## 设计决策与哲学

- **Kubernetes-native control plane**：llm-d P/D Utils 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它不是 serving controller，而是 P/D 部署前后的诊断工具箱。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `P/D diagnostics` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | llm-d P/D Utils | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | P/D diagnostics | [[llm-d]], [[disaggregated-serving]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

llm-d P/D Utils 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
