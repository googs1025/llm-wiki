# Auto-diagnosing Kubernetes Alerts with HolmesGPT and CNCF Tools

**来源:** https://www.cncf.io/blog/2026/04/21/auto-diagnosing-kubernetes-alerts-with-holmesgpt-and-cncf-tools/
**日期:** 2026-04-21
**作者:** Grace Park, Ihyeok Song (STCLab SRE Team)

## 问题
两人 SRE 团队管理多个 Amazon EKS 集群，每个告警需 15-20 分钟人工排查。

## 方案
使用 HolmesGPT（CNCF Sandbox）的 ReAct 推理模式自动诊断告警。

### 关键发现：Runbook 比模型选择更重要
- 有 runbook：同一模型评分 4.6/5，3-4 次工具调用
- 无 runbook：评分 3.6/5，20+ 步才得出结论

### 架构
- HolmesGPT + ReAct 模式（动态选择工具）
- Markdown runbook 带元数据头（指定可用工具、范围限制）
- Robusta 集成（200 行 Python playbook）
- Slack 频道按 namespace 路由

### 模型测试
- 自托管：KubeAI（CNCF）+ Spot GPU，冷启动 5-8 分钟
- 生产：托管 API + VPC endpoint，每次调查约 $0.04

### 效果
- 日告警从 ~40 降至 ~12（去重）
- 排查审核时间：<2 分钟（原 15-20 分钟）
- ~40% 调查自动定位明显根因（OOMKilled、ImagePullBackOff）
- 无效工具调用从 16 次降至 2 次

## 未来方向
集成 Inspektor Gadget（CNCF）的 eBPF 网络指标。
