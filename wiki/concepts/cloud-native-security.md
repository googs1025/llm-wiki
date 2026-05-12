---
title: 云原生安全
tags: [security, kubernetes, cloud-native, ai]
date: 2026-04-22
sources: [ai-vulnerability-discovery.md, k8s-v1.36-sneak-peek.md]
related: ["[[kubernetes]]"]
---

# 云原生安全

云原生环境下的安全实践、威胁模型和工具链。

## 当前趋势

### AI 与漏洞发现
AI 模型同时加速漏洞发现和低质量报告泛滥。核心应对：
- 维护者：公开威胁模型 + 最低报告标准 + AI 辅助分诊
- 发现者：完整 PoC + 修复 PR，禁止批量提交
- 详见 [[src-ai-vulnerability-discovery]]

### K8s v1.36 安全强化
- 弃用 `externalIPs`（中间人攻击风险）
- 移除 `gitRepo` Volume（root 提权风险）
- 详见 [[src-k8s-v1.36-sneak-peek]]

## 待补充
- Service Mesh 安全（Istio/Cilium mTLS）
- 供应链安全（Sigstore、SBOM）
- 运行时安全（Falco、Tetragon）
