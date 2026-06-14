# llm-d Benchmark 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-benchmark · 分析日期：2026-06-13 · 版本：HEAD `bd8dc5e`（2026-06-12）

## 一句话定位

llm-d Benchmark 是 llm-d 生态的实验编排和评测工作台，用一个 `llmdbenchmark` CLI 把 standup、smoketest、run、result collection、analysis、teardown 串成可复现流程。它不是单一压测引擎，而是用 Jinja specification、scenario、workspace 和多 harness 适配，把 inference-perf、GuideLLM、vLLM benchmark 等工具纳入同一套 Kubernetes 实验生命周期。

## 核心架构图

```
┌────────────────────────┐
│ llmdbenchmark CLI      │
│ llmdbenchmark/cli.py   │
└───────────┬────────────┘
            │ parse args / workspace
            ▼
┌────────────────────────┐
│ RenderSpecification    │
│ config/specification   │
│ scenario + overrides   │
└───────────┬────────────┘
            │ resolved experiment spec
            ▼
┌────────────────────────┐
│ RenderPlans            │
│ templates + defaults   │
│ cluster/version resolve│
└───────────┬────────────┘
            │ manifests / plans / configs
            ▼
┌────────────────────────┐
│ StepExecutor           │
│ global steps sequential│
│ stack steps parallel   │
└─────┬─────┬─────┬──────┘
      │     │     │
      │     │     └──────────────┐
      │     │                    │
┌─────▼─────▼─────┐     ┌────────▼──────────┐
│ standup phase   │     │ run phase          │
│ cluster/stack   │     │ harness namespace  │
│ manifests/Helm  │     │ endpoint discovery │
└─────┬───────────┘     │ deploy benchmark   │
      │                 │ collect/analyze    │
      │                 └────────┬───────────┘
      ▼                          ▼
┌──────────────┐        ┌────────────────────┐
│ Kubernetes   │        │ Harness adapters   │
│ llm-d stack  │        │ inference-perf     │
│ simulator/GPU│        │ guidellm/vllm/etc. │
└──────┬───────┘        └────────┬───────────┘
       │                         │
       ▼                         ▼
┌────────────────────────────────────────────┐
│ workspace: rendered configs, manifests,    │
│ logs, raw results, analyzed reports         │
└────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| CLI 调度 | `llmdbenchmark/cli.py` | 解析命令，初始化 workspace，串起 spec rendering、plan rendering 和 phase execution。 |
| 配置模型 | `llmdbenchmark/config.py`, `config/specification`, `config/scenarios` | defaults → scenario → CLI overrides 的配置合并和实验规格定义。 |
| 模板渲染 | `llmdbenchmark/parser/render_specification.py`, `render_plans.py`, `config/templates` | 渲染 Jinja spec、Kubernetes manifests、Helm values 和 stack plans。 |
| 执行器 | `llmdbenchmark/executor/{step.py,step_executor.py}` | 把 global steps 与 per-stack steps 分开，支持多 stack 并行执行和 `--stack` 过滤。 |
| 生命周期阶段 | `llmdbenchmark/{standup,run,teardown,smoketests}` | standup / run / teardown / smoketest 的 step 定义。 |
| harness 适配 | `workload/harnesses` | 适配 inference-perf、GuideLLM、vLLM benchmark、nop、inferencemax、aiperf 等压测工具。 |
| 结果与遥测 | `llmdbenchmark/result_store`, `llmdbenchmark/telemetry` | 收集结果、分析输出、上传或保存实验数据。 |
| Stack discovery | `llm_d_stack_discovery` | 辅助发现 llm-d stack 端点和运行状态。 |

核心约束是：benchmark repo 管的是“实验生命周期”和“可复现实验资产”，具体负载生成交给 harness，具体 serving 行为交给 llm-d stack 或 simulator。

## 关键数据流

```
用户选择 scenario / flags
        │
        ▼
CLI 初始化 workspace
        │
        ▼
RenderSpecification 合并 defaults + scenario + CLI overrides
        │
        ▼
RenderPlans 解析版本、集群资源、模板和 stack plans
        │
        ▼
预渲染 Kubernetes / Helm manifests
        │
        ▼
StepExecutor 执行阶段
        │
        ├── standup: 部署或准备 llm-d stack
        ├── smoketest: 校验 endpoint/model 可用
        ├── run: 创建 harness namespace、部署 benchmark job、等待完成
        ├── collect: 收集 raw result/logs
        ├── analyze/upload: 生成报告并保存
        └── teardown: 清理实验资源
        │
        ▼
workspace 保留 rendered config + manifests + results
```

失败通常在 step 级别被包装成 `StepResult` / `ExecutionResult`，而不是散落在脚本里；这让用户可以区分配置渲染失败、集群部署失败、endpoint 不可用、harness job 失败和结果收集失败。

## 设计决策与哲学

- **先渲染再执行**：CLI 会先把 spec、plan 和 manifests 渲染进 workspace，再执行 Kubernetes 动作，降低“脚本临时拼 YAML”造成的不可复现。
- **benchmark 编排器不绑定单一压测工具**：`workload/harnesses` 把 inference-perf、GuideLLM、vLLM benchmark 等封装成可替换 harness，避免把实验框架和负载生成器耦死。
- **global step 顺序执行，per-stack step 并行**：`step_executor.py` 把全局资源和 stack-local 资源分开，适合一次对比多套 llm-d stack 或多个参数组合。
- **workspace 是实验事实来源**：rendered configs、manifests、logs 和结果集中在 workspace，方便复现实验、审查差异和归档。
- **DoE / sweep 是一等场景**：配置层支持 scenario 和参数展开，说明它面向系统调参，而不是单次 smoke benchmark。

## 关键组件深入解读

### CLI 编排器（`llmdbenchmark/cli.py`）

CLI 负责把命令参数转成统一执行上下文：创建 workspace，调用 `RenderSpecification`，解析版本与集群信息，调用 `RenderPlans`，预渲染 Helm/Kubernetes 资源，最后根据 phase 派发到 standup、smoketest、run、teardown 或 experiment。它的价值不是复杂算法，而是把“实验可复现”前置成主流程。

### StepExecutor（`llmdbenchmark/executor/step_executor.py`）

`StepExecutor` 把 steps 切成 global 和 per-stack 两类。global steps 顺序执行，避免共享资源竞争；per-stack steps 用 `ThreadPoolExecutor` 并行，提升多 stack 对比实验效率。这个模型把 benchmark 的并行度限定在 stack 边界内，比自由脚本更容易定位失败。

## 与同类对比

| 维度 | llm-d Benchmark | inference-perf / GuideLLM | vLLM benchmark scripts |
|------|-----------------|---------------------------|------------------------|
| 主要职责 | 编排实验生命周期、部署、收集、分析 | 生成负载和测量指标 | 针对 vLLM 的 benchmark 工具 |
| 运行环境 | Kubernetes / llm-d stack / simulator / GPU cluster | 可被容器化运行 | 多偏单工具或单引擎场景 |
| 可复现资产 | workspace + rendered YAML + config + results | 结果和负载配置 | 脚本参数和输出 |
| 适合问题 | 多 stack、多参数、部署到结果闭环 | 单次负载测量 | engine 层性能测量 |

## 性能 / 资源开销

llm-d Benchmark 本身主要消耗 CPU、磁盘和 Kubernetes API 调用；真正的 GPU/推理成本由被测 stack 和 harness 负载决定。Kind + simulator 可用于无 GPU 快速验证，真实 GPU 集群才适合产出选型级吞吐/延迟数据。

## 安全模型

该项目会在 Kubernetes 集群中创建 namespace、ConfigMap、Job/Pod、Helm/Kubernetes 资源并读取 endpoint，因此权限边界主要由 kubeconfig/RBAC 决定。它应作为受控实验工具运行，不应把生产集群高权限 kubeconfig、provider token 或私有模型凭据无隔离地放进共享 workspace。
