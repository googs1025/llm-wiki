---
title: Nacos
tags: [config-center, service-discovery, alibaba-oss]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md]
related: [[HiClaw]]
---

# Nacos

> Stub — 待充实

阿里开源的**配置中心 + 服务发现**系统。在 [[HiClaw]] 中扮演 **Worker 模板市场**角色——Worker 的能力包通过 `WorkerSpec.Package: nacos://<URI>` 声明，Worker 启动时从 Nacos 拉取（类似 docker registry 之于镜像）。

## 在 HiClaw 中的具体使用

- `nacos://` URI scheme 是 `WorkerSpec.Package` 的合法值之一（与 `file://` / `http(s)://` 并列）
- Manager Agent 的 `hiclaw-find-worker` skill 做 Nacos 搜索 + 导入：管理员说"给我一个会做代码评审的 Worker"，Manager 去 Nacos 搜匹配的 package 拉下来用

## TODO

- [ ] 写 Nacos 的核心架构（一致性协议、cluster 拓扑）
- [ ] 补充：Nacos 跟 [[kubernetes]] ConfigMap / etcd 的对比
- [ ] HiClaw 用的 Nacos 包格式规范（manifest schema）
