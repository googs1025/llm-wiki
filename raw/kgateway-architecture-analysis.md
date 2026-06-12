# kgateway 架构与设计思路分析

> 仓库：https://github.com/kgateway-dev/kgateway · 分析日期：2026-06-12 · 版本：HEAD `1560573`（2026-06-11，feat: added reference grant mode (#14209)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`kgateway-dev/kgateway` 是通用 cloud-native API Gateway，并带 AI Gateway 能力。仓库核心是 Gateway API 资源、controller/deployer、Envoy xDS、plugins、policies、SDS、安全和 conformance/e2e；最近 reference grant mode 也说明跨 namespace 引用治理是主路径。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kgateway-dev/kgateway` 是通用 cloud-native API Gateway，并带 AI Gateway 能力。仓库… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `api/v1alpha1`, `pkg/kgateway`, `pkg/xds` · `pkg/plugins`, `pkg/pluginsdk`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `pkg/deployer`, `pkg/sds`                     │  │ `install/helm`, `examples/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `api/v1alpha1`, `pkg/kgateway`, `pkg/xds` | Gateway API 扩展、controller 和 xDS 生成。 |
| `pkg/plugins`, `pkg/pluginsdk` | 插件系统。 |
| `pkg/deployer`, `pkg/sds` | Envoy 部署和 Secret Discovery。 |
| `install/helm`, `examples/**` | 安装和示例。 |
| `devel/**`, `test/**` | 架构文档与验证。 |

## 关键数据流

1. Gateway API/自定义 policy 被 controller watch。
2. kgateway 生成 Envoy 配置/xDS 并部署/更新代理。
3. plugins/policies 处理 auth、traffic、AI 等增强能力。

## 设计决策与哲学

- 先做通用 Gateway，再把 AI 场景做成 policy/plugin。
- reference grant 强化跨 namespace 安全边界。
- 适合已有 Gateway API/Envoy 体系的团队。

## 与已有项目的对比

和 Envoy AI Gateway 相比，kgateway 范围更宽；和 Higress 相比，它更 Kubernetes/Gateway API 原生。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
