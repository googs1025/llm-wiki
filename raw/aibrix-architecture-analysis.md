# AIBrix 架构与设计思路分析

> 仓库：https://github.com/vllm-project/aibrix · 分析日期：2026-06-12 · 版本：HEAD `ac2c161`（2026-06-11，chore: nit fix in slo_test race condition test (#2328)）· 获取方式：GitHub API 复核 HEAD + codeload tarball 源码扫描。

## 一句话定位

`vllm-project/aibrix` 是 vLLM 生态的 Kubernetes GenAI inference infrastructure，而不是推理引擎。仓库包含 controller-manager、gateway plugins、KV cache watcher、CRD、webhook、metrics、cache、PodAutoscaler、ModelAdapter/RayCluster/Roleset 等模块，目标是把 vLLM 大规模部署、路由、扩缩容、LoRA、分布式推理和 KV cache 管理做成云原生控制面。

## 核心架构图

```text
┌──────────────────────────── OpenAI-compatible traffic ───────────────────────┐
│ HTTPRoute / Envoy Gateway / AIBrix gateway plugins                            │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ AIBrix control plane                                                          │
│ controllers · webhooks · metrics · routing cache · KV event manager           │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ CRDs                          │  │ runtime/data plane                          │
│ PodAutoscaler · ModelAdapter   │  │ vLLM pods · RayClusterFleet · KV cache sync │
│ StormService · KVCache         │  │ LoRA adapters · GPU optimizer/failure detect│
└───────────────────────────────┘  └────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/controllers`, `pkg/controller/**` | controller-runtime 控制面，PodAutoscaler 等 reconciler。 |
| `api/autoscaling`, `api/orchestration`, `api/model` | CRD API：PodAutoscaler、StormService、RayClusterFleet、Roleset、KVCache、ModelAdapter。 |
| `pkg/plugins/gateway/**` | gateway/routing 插件，包含 P/D disaggregation 路由逻辑。 |
| `pkg/cache`, `pkg/kvevent` | KV event manager、cache snapshot、pod/model cache、ZMQ 事件。 |
| `pkg/metrics`, `config/gateway`, `config/prometheus` | metrics/exporter 和 Gateway/Prometheus 安装资源。 |

## 关键数据流

1. 用户通过 Gateway 访问模型，gateway plugin 根据 model labels、pod metrics、KV/cache 状态选择后端。
2. controller 监听 AIBrix CRD 和 K8s workload，创建/调整 vLLM/RayCluster/RoleSet 等资源。
3. PodAutoscaler 支持 HPA/KPA/APA，不同 metric source 包括 pod/resource/custom/external/domain。
4. KV event watcher 消费 vLLM KV events，更新 cache/pod/model 视图，供 routing/autoscaling 使用。

## 设计决策与哲学

- AIBrix 把 vLLM 从单 engine 运维提升到 K8s control plane。
- 它比 llm-d 更像一体化发行：gateway、autoscaler、LoRA、KV cache、GPU failure detection 都在一个 repo。
- CRD + controller-runtime 是主线，Gateway API/Envoy 是流量入口。
- 白皮书/README feature 很多，源码中 PodAutoscaler/KV/cache/gateway 是最值得先读的实际模块。

## 与已有项目的对比

和 [[dynamo]] 相比，AIBrix 更 Kubernetes/controller-first；Dynamo 更强调推理系统运行时和分离式 P/D/KV 数据路径。和 llm-d 相比，AIBrix 更一体化，llm-d 更生态拆分（router、kv-cache、guides）。和 [[skypilot]] 相比，AIBrix 管集群内 inference，不管多云资源采购。

## 选型提示

- 适合深挖的问题：入口协议、状态源、工具/运行时边界、部署模型、失败恢复和安全治理。
- 不要只看 README：本页结论来自源码目录、入口文件、核心包和 GitHub 当前 HEAD 的组合扫描。
- 后续如继续深化，应补充 release/tag 变更、关键 issue/PR 和真实部署案例。
