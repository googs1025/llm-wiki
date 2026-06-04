# K8s GPU & Device Plugins Star 项目清单整理

> 来源：https://github.com/stars/googs1025/lists/k8s-gpu-device-plugins · 抓取日期：2026-06-04 · GitHub list 描述：GPU/异构、device-plugin、DRA、vGPU · 仓库数：36 · list 更新时间：2026-05-12 15:29:47 UTC

## 一句话定位

这个 Star list 聚焦 Kubernetes 异构设备资源层：从最传统的 device plugin、GPU Operator、container toolkit、DCGM/NVML 监控，到 vGPU / GPU sharing、Dynamic Resource Allocation、CDI、fake GPU 测试环境，再延伸到 CUDA 学习、TensorRT、KV cache 虚拟化这类 GPU workload 能力。

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

## 项目分组

### NVIDIA GPU 基座

| 项目 | Stars | 关注点 |
|------|-------|--------|
| NVIDIA/k8s-device-plugin | 3780 | Kubernetes 上暴露 NVIDIA GPU 的标准 device plugin。 |
| NVIDIA/gpu-operator | 2725 | 安装、配置和管理 GPU driver、device plugin、runtime 等完整 NVIDIA GPU 栈。 |
| NVIDIA/nvidia-container-toolkit | 4381 | 让容器运行时使用 NVIDIA GPU 的基础组件。 |
| NVIDIA/gpu-feature-discovery | 309 | 把 GPU 特性写入 Node Feature Discovery labels，支持按能力调度。 |
| NVIDIA/dcgm-exporter | 1751 | 基于 DCGM 的 GPU Prometheus metrics exporter。 |
| NVIDIA/go-nvml | 444 | NVML 的 Go binding，供 operator / plugin / exporter 调用。 |
| NVIDIA/gpu-monitoring-tools | 1074 | NVIDIA Linux GPU 监控工具集。 |

### GPU sharing、vGPU 与虚拟化

| 项目 | Stars | 关注点 |
|------|-------|--------|
| Project-HAMi/HAMi | 3517 | Kubernetes 异构 GPU sharing / vGPU 代表项目。 |
| 4paradigm/k8s-vgpu-scheduler | 592 | GPU 显存虚拟化和 vGPU 调度路线。 |
| AliyunContainerService/gpushare-device-plugin | 495 | 阿里云早期 GPU sharing device plugin。 |
| tkestack/gpu-manager | 899 | Tencent/TKE 系 GPU 管理组件。 |
| Project-HAMi/volcano-vgpu-device-plugin | 156 | 面向 Volcano vGPU 的 device plugin，支持硬资源隔离。 |
| ovg-project/kvcached | 1061 | 虚拟化弹性 KV cache，连接 GPU sharing 与 LLM KV cache 资源化。 |

### DRA、CDI 与异构设备标准化

| 项目 | Stars | 关注点 |
|------|-------|--------|
| kubernetes-sigs/dra-driver-nvidia-gpu | 651 | NVIDIA GPU Dynamic Resource Allocation driver。 |
| kubernetes-sigs/dra-example-driver | 131 | DRA driver 示例，供开发者 fork。 |
| kubernetes-sigs/dra-driver-cpu | 50 | CPU DRA driver。 |
| kubernetes-sigs/cni-dra-driver | 43 | 把 CNI 更靠近 Kubernetes DRA 的实验性 driver。 |
| cncf-tags/container-device-interface | 299 | Container Device Interface 标准化方向。 |
| intel/intel-device-plugins-for-kubernetes | 134 | Intel 设备插件集合。 |
| everpeace/k8s-host-device-plugin | 50 | 把 host device file 暴露给容器的极简 device plugin。 |

### 可观测、诊断与测试替身

| 项目 | Stars | 关注点 |
|------|-------|--------|
| leptonai/gpud | 482 | GPU monitoring、diagnostics、issue identification 自动化。 |
| run-ai/fake-gpu-operator | 264 | 用 fake GPU 模拟环境测试调度和 operator 行为。 |
| chaunceyjiang/fake-gpu | 65 | 模拟 GPU 信息，便于无 GPU 环境测试。 |
| NVIDIA/knavigator | 78 | 面向 AI/ML scheduling systems 的开发、测试和优化工具。 |

### GPU workload、CUDA 与生态边界

| 项目 | Stars | 关注点 |
|------|-------|--------|
| NVIDIA/TensorRT | 13038 | NVIDIA 高性能深度学习推理 SDK 的开源组件。 |
| xlite-dev/LeetCUDA | 11176 | CUDA 学习笔记和 kernel 练习。 |
| Tony-Tan/CUDA_Freshman | 2754 | CUDA 入门学习资源。 |
| MooreThreads/mthreads-ml-py | 9 | 摩尔线程 GPU 管理/监控 Python wrapper。 |
| MooreThreads/torchada | 35 | 让 torch_musa 提供 CUDA-compatible PyTorch 体验的 adapter。 |
| MooreThreads/tutorial_on_musa | 48 | MUSA 学习教程。 |
| NVIDIA/ais-k8s | 132 | AIStore 在 Kubernetes 上的 operator、Helm charts 和工具脚本。 |
| kubernetes-sigs/kernel-module-management | 123 | 在 Kubernetes 中构建、签名和加载 kernel modules。 |

## 观察

- Kubernetes GPU 资源层已经从 “device plugin 把卡暴露出来” 扩展成完整栈：driver/runtime/operator、feature discovery、metrics、diagnostics、admission、scheduler、sharing 和 DRA 都是独立问题。
- vGPU/GPU sharing 仍有多条历史路线并存：gpushare、TKE gpu-manager、4paradigm vgpu-scheduler、HAMi、Volcano vGPU；其中 HAMi 是当前更值得深挖的社区化代表。
- DRA 是下一代设备资源抽象的主线：NVIDIA GPU DRA、CPU DRA、CNI DRA、DRA example driver 说明 Kubernetes 正在把“设备分配”从 device plugin 扩展成更声明式、更可组合的资源 API。
- GPU 可观测不只是 metrics：DCGM exporter/NVML 是数据源，GPUd/fake-gpu/fake-gpu-operator/knavigator 面向诊断、测试和调度系统开发。
- LLM serving 把 GPU 资源层进一步复杂化：kvcached 把 KV cache 也推向可虚拟化资源，和 GPU sharing、KV cache offload、DRA 之间有明显交叉。

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
