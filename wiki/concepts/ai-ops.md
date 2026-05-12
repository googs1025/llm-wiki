---
title: AI 运维 (AIOps)
tags: [ai-ops, observability, kubernetes, llm]
date: 2026-04-22
sources: [holmesgpt-k8s-alert-diagnosis.md]
related: ["[[kubernetes]]", "[[opentelemetry]]", "[[ebpf]]"]
---

# AI 运维 (AIOps)

用 AI/LLM 增强运维流程，特别是告警分诊、根因分析、自动修复。

## 关键发现
**Runbook 比模型选择更重要**（来自 STCLab 实践）：
- 有 runbook：3-4 次工具调用定位问题
- 无 runbook：20+ 步才有结论

## 工具
- **HolmesGPT**（CNCF Sandbox）— ReAct 推理模式自动诊断 K8s 告警
- **Robusta** — K8s 告警自动化平台
- **KubeAI**（CNCF）— K8s 上自托管 LLM

## 效果数据
每次调查成本 ~$0.04（~$12/月），排查时间从 15-20 分钟降至 <2 分钟。

## 详见
- [[src-holmesgpt-k8s-alerts]]
