---
title: Container Device Interface
tags: [concept, cdi, kubernetes, device-plugin, gpu]
date: 2026-06-12
sources: [k8s-device-plugin-architecture-analysis.md, dra-driver-nvidia-gpu-architecture-analysis.md]
related: [[device-plugin]], [[k8s-device-plugin]], [[kubernetes-dra]], [[gpu-sharing]], [[gpu-operator]]
---

# Container Device Interface

CDI（Container Device Interface）用标准化 spec 描述容器需要的设备节点、mount、env、hooks 等 edits，让 device plugin / runtime / scheduler 之间传递设备配置时减少厂商私有约定。

## 在 GPU 栈中的位置

[[k8s-device-plugin]] 支持通过 CDI annotations/device list strategy 把 NVIDIA 设备交给容器；[[dra-driver-nvidia-gpu]] 也在 Prepare 阶段生成或引用 CDI 配置。CDI 是传统 device plugin 与 DRA 都会复用的设备注入抽象。

## 选型提示

如果你在比较 envvar、volume-mounts、CDI annotations，优先理解 CDI：它更适合复杂设备、hooks 和 runtime edits 的标准化。
