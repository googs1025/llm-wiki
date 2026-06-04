---
title: K8s GPU & Device Plugins Star 项目清单整理
tags: [kubernetes, gpu, device-plugin, dra, vgpu, ai-infra]
date: 2026-06-04
sources: [k8s-gpu-device-plugins-stars-list.md]
related: ["[[kubernetes]]", "[[llm-inference]]", "[[kv-cache-offload]]", "[[vllm]]", "[[sglang]]", "[[dynamo]]", "[[disaggregated-serving]]"]
---

# K8s GPU & Device Plugins Star 项目清单整理

> 原文：`raw/k8s-gpu-device-plugins-stars-list.md` · 来源：[googs1025 的 K8s GPU & Device Plugins Stars list](https://github.com/stars/googs1025/lists/k8s-gpu-device-plugins) · 抓取日期：2026-06-04 · 仓库数：36

## 一句话定位

这个 Star list 聚焦 [[kubernetes]] 异构设备资源层：从最传统的 device plugin、GPU Operator、container toolkit、DCGM/NVML 监控，到 vGPU / GPU sharing、Dynamic Resource Allocation、CDI、fake GPU 测试环境，再延伸到 CUDA 学习、TensorRT、KV cache 虚拟化这类 GPU workload 能力。

## 分层地图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AI / CUDA workload layer                                                     │
│ TensorRT · LeetCUDA · CUDA_Freshman · kvcached · MUSA adapters               │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Runtime / container integration                                              │
│ NVIDIA container toolkit · CDI · NVML bindings · operator libs               │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Kubernetes device exposure                                                   │
│ NVIDIA k8s-device-plugin · Intel device plugins · host device plugin         │
│ GPU Feature Discovery · GPU Operator · AIStore on K8s                        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Sharing / virtualization / DRA                                               │
│ HAMi · vgpu-scheduler · gpushare · Volcano vGPU · NVIDIA DRA · CPU/CNI DRA   │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Observability / diagnostics / test doubles                                   │
│ DCGM exporter · gpu-monitoring-tools · GPUd · fake-gpu · fake-gpu-operator   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 观察

- Kubernetes GPU 资源层已经从 “device plugin 把卡暴露出来” 扩展成完整栈：driver/runtime/operator、feature discovery、metrics、diagnostics、admission、scheduler、sharing 和 DRA 都是独立问题。
- vGPU/GPU sharing 仍有多条历史路线并存：gpushare、TKE gpu-manager、4paradigm vgpu-scheduler、HAMi、Volcano vGPU；其中 HAMi 是当前更值得深挖的社区化代表。
- DRA 是下一代设备资源抽象的主线：NVIDIA GPU DRA、CPU DRA、CNI DRA、DRA example driver 说明 Kubernetes 正在把“设备分配”从 device plugin 扩展成更声明式、更可组合的资源 API。
- GPU 可观测不只是 metrics：DCGM exporter/NVML 是数据源，GPUd/fake-gpu/fake-gpu-operator/knavigator 面向诊断、测试和调度系统开发。
- [[llm-inference]] 把 GPU 资源层进一步复杂化：kvcached 把 KV cache 也推向可虚拟化资源，和 GPU sharing、[[kv-cache-offload]]、DRA 之间有明显交叉。

## 优先深挖候选

| 优先级 | 项目 | 原因 |
|--------|------|------|
| 1 | NVIDIA/k8s-device-plugin | Kubernetes GPU device plugin 标准参照。 |
| 2 | NVIDIA/gpu-operator | 生产 GPU 集群运维主入口。 |
| 3 | Project-HAMi/HAMi | 当前 GPU sharing / vGPU 方向最值得系统分析的项目。 |
| 4 | kubernetes-sigs/dra-driver-nvidia-gpu | Kubernetes DRA + GPU 的下一代资源 API 样板。 |
| 5 | cncf-tags/container-device-interface | CDI 是 container runtime 侧设备声明标准，和 DRA/device plugin 相邻。 |
| 6 | NVIDIA/dcgm-exporter | GPU metrics 和 Prometheus 集成标配。 |
| 7 | leptonai/gpud | GPU 诊断从 metrics 走向自动化 health/issue detection。 |
| 8 | ovg-project/kvcached | KV cache 资源化和 GPU sharing/LLM serving 的交叉点。 |

## 相关页面

- [[kubernetes]]
- [[llm-inference]]
- [[kv-cache-offload]]
- [[vllm]]
- [[sglang]]
- [[dynamo]]
- [[disaggregated-serving]]
