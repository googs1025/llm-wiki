---
title: Kubernetes GPU / Device Stack 项目地图
tags: [kubernetes, gpu, device-plugin, dra, cdi, project-map]
date: 2026-06-13
sources: [src-k8s-gpu-device-plugins-stars, src-hami-architecture, src-gpu-operator-architecture, src-dra-driver-nvidia-gpu-architecture, src-k8s-device-plugin-architecture]
related: [[kubernetes]], [[llm-inference]], [[device-plugin]], [[kubernetes-dra]], [[cdi]], [[gpu-sharing]], [[hami]], [[gpu-operator]], [[dra-driver-nvidia-gpu]], [[k8s-device-plugin]]
---

# Kubernetes GPU / Device Stack 项目地图

这页把 [[src-k8s-gpu-device-plugins-stars]] 从 star list 整理成 Kubernetes GPU / 异构设备资源层地图。核心结论：LLM serving 的 GPU 底座已经不只是“把 `/dev/nvidia0` 挂进 Pod”，而是 driver/operator、container runtime、device discovery、DRA/CDI、sharing、scheduler、observability、diagnostics 和 fake device 测试环境的组合。

```
AI / CUDA workload
  vLLM · SGLang · TensorRT · CUDA kernels · KV cache workloads
        ↓
Serving / scheduler layer
  llm-d · KServe · AIBrix · GPUStack · Kueue · autoscalers
        ↓
Kubernetes device API
  Device Plugin · DRA ResourceClaim/ResourceSlice · CDI device spec
        ↓
GPU sharing / allocation policy
  HAMi · MIG · time-slicing · vGPU · scheduler extender · admission
        ↓
Node GPU software stack
  GPU Operator · NVIDIA driver · container toolkit · DCGM · NVML
        ↓
Observability / diagnostics / tests
  dcgm-exporter · GPUd · fake-gpu · fake-gpu-operator
```

## 一句话分层

| 层 | 代表项目 | 要解决的问题 |
|---|---|---|
| 驱动与节点软件栈 | [[gpu-operator]], NVIDIA container toolkit, DCGM | 节点怎样安装、升级和暴露 GPU 软件栈 |
| 设备暴露 | [[k8s-device-plugin]], Intel device plugins, host device plugin | kubelet 如何发现并分配专用设备 |
| 声明式设备分配 | [[kubernetes-dra]], [[dra-driver-nvidia-gpu]], [[cdi]] | Pod 如何声明更复杂的设备需求和分配结果 |
| GPU sharing / vGPU | [[hami]], Volcano vGPU, gpushare, vgpu-scheduler | 多租户如何切分、调度和隔离 GPU |
| 调度与队列 | Kueue, scheduler-plugins, autoscaler | GPU batch / AI workload 如何排队和扩缩 |
| 观测与诊断 | DCGM exporter, GPUd, fake-gpu | 怎么发现 GPU 健康、利用率和测试调度逻辑 |

## 核心项目边界

### [[k8s-device-plugin]]

NVIDIA 官方 GPU device plugin 是传统路径的基线：通过 NVML/CUDA discovery 向 kubelet gRPC 注册 `nvidia.com/gpu` 等资源，并在 Allocate 阶段用 env、volume、CDI 等方式把设备注入容器。它解决“设备能不能被 Pod 请求到”，不解决 driver 生命周期、共享策略或模型 serving。

### [[gpu-operator]]

GPU Operator 是生产集群运维入口：用 `ClusterPolicy` / `NVIDIADriver` 驱动 driver、container toolkit、device plugin、DCGM、MIG manager、validator 等 operands 的 lifecycle。它解决“节点 GPU 软件栈怎样持续正确”，通常和 device plugin 一起出现。

### [[hami]]

HAMi 是 GPU sharing / vGPU 方向的重要样本。它通过 webhook、scheduler extender、device plugin 和多厂商 device abstraction，把 GPU 显存、算力、切分和调度策略放到 K8s 资源模型旁边。它解决“多个 workload 如何共享 GPU”，但也带来调度、隔离、观测和兼容性的复杂度。

### [[dra-driver-nvidia-gpu]]

NVIDIA DRA driver 是下一代设备分配路径样板。DRA 把设备需求从传统 extended resource 推向 `ResourceClaim` / `ResourceSlice` / driver controller，支持更动态、更声明式的分配模式。它适合研究 Kubernetes 设备 API 的未来，而不是替代所有现有 device plugin 部署。

## 和 LLM serving 的关系

[[llm-inference]] 会把 GPU 资源层进一步拉进架构设计：

- Prefill/Decode 分离要求不同 GPU 池承担不同负载。
- KV cache offload 让显存、CPU 内存、NVMe 和网络都成为资源决策。
- LoRA / adapter serving 需要更细的内存与模型资产管理。
- GPU sharing 会影响 tail latency，不能只看平均利用率。
- DRA/CDI 会影响 serving operator 如何把“设备分配结果”交给 runtime。

所以 GPU stack 不应只作为运维背景，而应和 [[llm-d]]、[[aibrix]]、[[kserve]]、[[gpustack]]、[[kubeai]] 等 model serving operator 一起比较。

## 选型提示

- 生产 NVIDIA GPU 集群基础栈：先看 [[gpu-operator]] + [[k8s-device-plugin]]。
- 多租户共享和 vGPU：看 [[hami]]，同时关注隔离和性能尾延迟。
- 下一代设备 API：看 [[kubernetes-dra]] + [[dra-driver-nvidia-gpu]] + [[cdi]]。
- LLM serving 平台：GPU 栈只是底座，还需要 [[llm-inference]]、[[inference-routing]]、[[model-serving-operator]] 和可观测能力。

