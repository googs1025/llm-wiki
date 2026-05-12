# Argo CD 概览

**来源:** https://argo-cd.readthedocs.io/en/stable/
**日期:** 2026-04-22

## 定义
Argo CD 是 Kubernetes 的声明式 GitOps 持续交付工具，以 Git 仓库作为应用期望状态的单一事实来源。

## 核心功能
- **多模板支持**: Kustomize、Helm、Jsonnet、纯 YAML
- **多集群管理**: 跨多个 K8s 集群部署
- **安全**: SSO（OIDC、OAuth2、LDAP、SAML）、RBAC、多租户
- **部署自动化**: 自动/手动同步
- **漂移检测**: 自动识别实际状态与期望状态偏差
- **回滚**: 回退到任何 Git 提交的配置
- **高级部署**: PreSync/Sync/PostSync hooks 支持蓝绿和金丝雀部署

## 架构
Argo CD 作为 Kubernetes controller 持续比较运行中应用与 Git 存储的期望状态。出现 "OutOfSync" 时可视化差异，提供自动/手动同步选项。
