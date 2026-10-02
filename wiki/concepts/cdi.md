---
title: Container Device Interface
tags: [concept, cdi, kubernetes, device-plugin, gpu]
date: 2026-09-27
sources: [k8s-device-plugin-architecture-analysis.md, dra-driver-nvidia-gpu-architecture-analysis.md]
related: ["[[device-plugin]]", "[[k8s-device-plugin]]", "[[kubernetes-dra]]", "[[gpu-sharing]]", "[[gpu-operator]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[dra-driver-nvidia-gpu]]", "[[hami]]"]
---

# Container Device Interface

CDI（Container Device Interface）用标准化 spec 描述容器需要的设备节点、mount、env、hooks 等 edits，由兼容的 container runtime 按选定的 CDI device ID 应用配置。它是设备注入接口，不负责 scheduler 选节点或 allocator 选设备。

## 在 M5-C Device / GPU 地图中的位置

设备工具链或 driver 生成/维护 CDI spec；[[k8s-device-plugin]] 可通过配置的 CDI strategy 返回设备标识，[[dra-driver-nvidia-gpu]] 可在 Prepare 后返回 CDI devices，kubelet 再把相应配置交给 runtime 消费。[[gpu-operator]] 管理受管 driver/toolkit 等组件的部署，[[hami]] 可在支持的分配路径交接设备与隔离配置，两者都不能把 CDI 当作独立分配决策器。

两条注入路径见 [[k8s-gpu-device-stack]]，Prepare/CDI/checkpoint 与共享 Claim 回收边界见 [[kubernetes-dra-design-deep-dive]]。CDI 注入成功也不证明设备健康或共享隔离策略已满足。

## 在 GPU 栈中的位置

[[k8s-device-plugin]] 支持通过 CDI annotations/device list strategy 把 NVIDIA 设备交给容器；[[dra-driver-nvidia-gpu]] 也在 Prepare 阶段生成或引用 CDI 配置。CDI 是传统 device plugin 与 DRA 都会复用的设备注入抽象。

## 选型提示

如果你在比较 envvar、volume-mounts、CDI annotations，优先理解 CDI：它更适合复杂设备、hooks 和 runtime edits 的标准化。
