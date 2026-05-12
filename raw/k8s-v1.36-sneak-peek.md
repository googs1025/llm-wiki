# Kubernetes v1.36 Sneak Peek

**来源:** https://kubernetes.io/blog/2026/03/30/kubernetes-v1-36-sneak-peek/
**日期:** 2026-03-30
**作者:** Chad Crowell, Kirti Goyal, Sophia Ugochukwu, Swathi Rao, Utkarsh Umre

Kubernetes v1.36 将于 2026 年 4 月底发布，包含大量增强功能、弃用和移除。

## 弃用与移除

### Service.spec.externalIPs 弃用
- 安全问题：该字段可导致集群流量中间人攻击（CVE-2020-8554）
- 时间线：v1.36 开始弃用警告，v1.43 完全移除
- 替代方案：LoadBalancer Service、NodePort、Gateway API

### gitRepo Volume Driver 移除
- 自 v1.11 起弃用，v1.36 永久禁用
- 原因：允许攻击者以 root 身份在节点运行代码
- 替代方案：Init containers、git-sync 工具

## 重要增强

### SELinux 卷标签加速 (GA)
- 用 `mount -o context=XYZ` 替代递归文件重标签
- 减少 Pod 启动延迟
- v1.28 引入 → v1.32 增加指标 → v1.36 稳定

### Ingress NGINX 退役
- 2026-03-24 起不再维护
- 不再提供 bugfix 或安全更新
- 现有部署继续运行，镜像和 Helm chart 保持可用
