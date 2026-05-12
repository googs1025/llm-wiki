# K3s on On-Prem Infrastructures the GitOps Way

**来源:** https://www.cncf.io/blog/2026/04/17/k3s-on-on-prem-infrastructures-the-gitops-way-writing-a-custom-k0rdent-template-from-scratch/
**日期:** 2026-04-17
**作者:** Shivani Rathod (Improwised Tech) & Prithvi Raj (CNCF Ambassador)

## 问题
传统 on-prem K8s 部署的痛点：手动 VM 配置、不可移植的 bash 脚本、集群建成后难以修改、缺乏一致性。

## 方案
K3s + k0rdent 声明式多集群管理 + Proxmox 虚拟化。

### 架构分层
1. k0rdent 管理层
2. Proxmox 基础设施（BYOT - Bring Your Own Template）
3. Control Plane Provider
4. K3s Bootstrap Provider
5. 运行中的 K8s 集群

### BYOT 方式
- 使用已有 Proxmox VM 模板 + cloud-init
- 自定义 Helm chart 管理 VM 克隆、资源分配、SSH 密钥注入

### K3s Bootstrap 流程
1. 首个 control plane 节点安装 K3s
2. 提取并分发集群 token
3. 加入其他节点
4. 生成 kubeconfig

### k0rdent 持续调和
- 持续监控期望状态 → 检测/纠正配置漂移
- 完全声明式、GitOps 兼容

## 资源
自定义 Proxmox provider chart：https://github.com/Improwised/charts/tree/main/charts/cluster-api-provider-proxmox
