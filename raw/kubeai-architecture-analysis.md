# KubeAI 架构与设计思路分析

> 仓库：https://github.com/kubeai-project/kubeai · 分析日期：2026-06-12 · 版本：HEAD `1fe298d`（2026-03-31，Inject model labels into pods (#657)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`kubeai-project/kubeai` 是 K8s AI inference operator，定位比 KServe 更轻：Model CRD、OpenAI-compatible server、model proxy、autoscaler、model loader、vLLM client、Helm charts 和内置模型 manifests。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kubeai-project/kubeai` 是 K8s AI inference operator，定位比 KServe 更轻：Model … │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `api/k8s`, `api/openai` · `internal/modelcontroller`, `modelautoscaler`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `internal/openaiserver`, `modelproxy`                     │  │ `components/model-loader`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `api/k8s`, `api/openai` | K8s API 和 OpenAI API 类型。 |
| `internal/modelcontroller`, `modelautoscaler` | Model controller 和扩缩容。 |
| `internal/openaiserver`, `modelproxy` | OpenAI-compatible endpoint 和代理。 |
| `components/model-loader` | 模型加载组件。 |
| `charts/models`, `manifests/models` | 内置模型分发。 |

## 关键数据流

1. 用户创建 Model CRD 或安装 charts/models。
2. controller 创建 pod/deployment 并注入 model labels。
3. OpenAI server/model proxy 统一暴露 endpoint。

## 设计决策与哲学

- 以 Model 为核心资源，简化用户心智。
- 内置模型 charts/manifests 适合快速上手。
- 能力覆盖广但高级 routing/KV 优化弱于 llm-d/AIBrix。

## 与已有项目的对比

和 KServe 相比更轻；和 GPUStack 相比更 Kubernetes operator；和 OME 相比路线更直接。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
