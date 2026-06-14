# external-dns 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/external-dns · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

ExternalDNS 从 Service、Ingress、Gateway 等 Kubernetes 对象动态维护外部 DNS records，是声明式网络控制器代表。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ external-dns               │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Sources: s │ │ Registry: TXT  │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Provider:  │ │ Controller loo │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Sources | service/ingress/gateway/istio/contour 等 |
| Registry | TXT ownership and conflict protection |
| Provider | Route53/CloudDNS/Cloudflare 等 DNS API |
| Controller loop | desired endpoints -> record changes |

## 关键数据流

```
用户创建 Service/Ingress/Gateway
        │
        ▼
source 生成 DNS endpoints
        │
        ▼
registry 判断 ownership
        │
        ▼
provider apply record changes
        │
        ▼
外部 DNS 指向入口地址
```

## 设计决策与哲学

- **Kubernetes-native control plane**：external-dns 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Gateway/Ingress 决定流量入口；ExternalDNS 负责把入口地址发布到 DNS。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `网络 / DNS` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | external-dns | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 网络 / DNS | [[gateway-api]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

external-dns 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
