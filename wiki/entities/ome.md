---
title: OME
tags: [entity, model-serving, kubernetes, operator, runtime, accelerator]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[model-serving-operator]], [[llm-inference]], [[kserve]], [[kubeai]], [[gpustack]], [[dynamo]]
---

# OME

OME（Open Model Engine）是 Kubernetes model serving operator/control plane，围绕 CRD/controller、model agent、runtime selector 和 accelerator configuration 组织模型部署。

## 解决的问题

模型服务平台需要把模型生命周期、推理 runtime、硬件加速器和部署策略解耦，否则每接入一种 engine 或 GPU 都要复制一套 controller。OME 把 runtime 选择和 accelerator 配置提升为可复用的控制面抽象。

## 核心边界

OME 主要解决“模型怎么被部署和由哪个 runtime 承载”，不以在线 KV-aware routing、P/D traffic orchestration 或 API gateway 为核心。它适合作为 serving platform 的生命周期底座，再组合专用 router 和 engine。

## 适用场景

适合平台团队建设 runtime/accelerator 抽象、支持多种模型 backend，并希望保持 Kubernetes operator 边界清晰的场景。需要统一 predictive + GenAI API 看 [[kserve]]；需要完整 LLM serving 看 [[llm-d]]、[[dynamo]] 或 [[kthena]]。

详见 [[src-ome-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
