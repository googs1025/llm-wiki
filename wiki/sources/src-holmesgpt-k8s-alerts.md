---
title: "用 HolmesGPT 自动诊断 Kubernetes 告警"
tags: [kubernetes, observability, ai-ops, ebpf]
date: 2026-04-21
sources: [holmesgpt-k8s-alert-diagnosis.md]
related: ["[[kubernetes]]", "[[opentelemetry]]", "[[ebpf]]", "[[ai-ops]]"]
---

# 用 HolmesGPT 自动诊断 Kubernetes 告警

## 摘要
STCLab 两人 SRE 团队用 HolmesGPT（CNCF Sandbox）+ ReAct 推理模式自动诊断 K8s 告警，核心发现：**Runbook 比模型选择更重要**。

## 关键数据
| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 日告警量 | ~40 | ~12（去重后） |
| 单次排查时间 | 15-20 分钟 | <2 分钟 |
| 无效工具调用 | 16 次/调查 | 2 次/调查 |
| 每次调查成本 | — | ~$0.04 |

## 架构要点
- HolmesGPT ReAct 模式动态选择工具
- Markdown runbook 带元数据（可用工具、范围限制）
- Robusta 集成 + Slack 按 namespace 路由
- 未来：集成 Inspektor Gadget 的 [[ebpf]] 网络指标