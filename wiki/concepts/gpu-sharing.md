---
title: GPU Sharing
tags: [concept, gpu, kubernetes, sharing, scheduling]
date: 2026-06-12
sources: [hami-architecture-analysis.md, k8s-device-plugin-architecture-analysis.md]
related: [[hami]], [[k8s-device-plugin]], [[gpu-operator]], [[kubernetes-dra]], [[device-plugin]]
---

# GPU Sharing

GPU sharing 指多个 workload 共享同一物理 GPU 或 MIG/MPS/time-slicing/vGPU 资源的调度与隔离方法。目标是在吞吐、隔离、成本和利用率之间取平衡。

## 主要路线

| 路线 | 代表 | 特点 |
|---|---|---|
| MIG | [[k8s-device-plugin]] | 硬件切分，隔离强，但粒度受硬件 profile 限制 |
| Time-slicing / MPS | [[k8s-device-plugin]] | 共享简单，但隔离和 QoS 取舍明显 |
| vGPU / memory/core sharing | [[hami]] | 调度器参与，支持更细粒度资源表达 |
| DRA dynamic device config | [[dra-driver-nvidia-gpu]] | 面向未来的声明式资源配置 |

## 和 GPU Operator 的关系

[[gpu-operator]] 管软件栈生命周期；GPU sharing 管 workload 如何共享设备。两者层级不同，但生产环境经常同时出现。
