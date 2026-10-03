---
title: LLM Serving Reliability
tags: [concept, llm-inference, llm-serving, reliability, fault-tolerance]
date: 2026-10-03
sources: [src-vllm-architecture, src-sglang-architecture, src-k8s-serving-stack-comparison]
related: [llm-inference, llm-serving-performance, continuous-batching, inference-routing, disaggregated-serving, model-serving-operator, vllm, sglang]
---

# LLM Serving Reliability

在线 [[llm-inference]] 的可靠性合同定义：在可观测的故障、过载和控制面滞后下，系统如何保护已接受请求的语义、拒绝超出容量的请求，并留下可追溯证据。它补充 [[llm-serving-performance]]：性能讨论容量与延迟，可靠性讨论容量边界被触及时的正确行为。

## 可靠性不是透明重试

文本生成是有状态的流式请求。重试是否安全取决于调用方幂等键、采样参数与随机状态、模型/revision、已产生 token，以及服务端是否仍能辨识同一执行尝试。首 token 前的失败可在合同允许的次数、deadline 和预算内重试；一旦已向客户端发送 token，透明重放可能重复内容、改变采样轨迹或掩盖部分结果，通常应终止该流并明确报告中断。不得据此推断所有系统实现这些策略，或中途流重放是透明的。

[[continuous-batching]] 是 engine 内的调度；入口准入、排队和拒绝是请求路径上的合同。[[model-serving-operator]]、自动扩缩和模型装载则多是异步控制路径：它们最终改变可用容量，却不能替代当前请求的 admission 决策。

## S4 · 在线请求故障与降级时序

```mermaid
sequenceDiagram
  participant C as Client
  participant G as Gateway
  participant R as Router / EPP
  participant E as Engine worker
  C->>G: request + deadline
  G->>R: select eligible endpoint
  alt queue is bounded and full
    R-->>G: overload / no capacity
    G-->>C: reject or shed load
  else endpoint selected
    G->>E: forward request
    alt failure before first token
      E--xG: error / timeout
      G-->>C: retry only if policy and budget allow
    else failure after streaming starts
      E--xG: stream interrupted
      G-->>C: terminate stream; do not assume transparent replay
    end
  end
  Note over R,E: stale locality should reduce hit quality, not bypass engine KV validation
```

图中是抽象请求路径，而非某个项目的默认拓扑。其解释是：先以有界容量作出接纳或拒绝，再在已选择端点上区分首 token 前后；路由的 locality 线索只能改善命中质量，engine 仍负责 KV 身份与可用性的最终校验。

## Overload and Backpressure

可靠系统把并发数、队列深度、排队时间或 token/KV 预算设为有界资源，并对每个边界公开拒绝、限流或 load shedding 的语义。排队无限增长只会把过载伪装成高尾延迟，并挤占已开始流的资源。安全响应可按合同选择快速拒绝、优先级降级、客户端退避提示或停止接收低优先级工作；不能把“稍后会扩容”当成当前请求一定能等待的保证。

## Timeout and Cancellation

deadline 应随请求从 Gateway 传到 Router/EPP 和 worker；任一跳耗尽预算时，应取消下游尚未需要的工作并回收排队、KV 和执行槽位。取消是尽力传播还是强保证、客户端断连后是否继续计算、以及已提交给 GPU 的 iteration 何时停止，都必须由实现合同说明。日志应区分入站 deadline、排队超时、执行超时和客户端取消，避免把容量不足误诊为网络失败。

## Worker and Router Failure

worker 可能崩溃、未 ready、模型未装载或在 prefill/decode 中失败；Router/EPP 也可能不可用、发现结果陈旧或无法确认容量。对路由故障，系统可按策略 fail-open 到一个已知安全的候选集、fail-close，或直接 reject；每种选择在隔离风险、错误路由风险与可用性之间取舍，不能假定通用默认值。

readiness 与服务发现是异步控制路径，因而存在从 worker 健康改变到入口不再选它的滞后。P/D 分离的 [[disaggregated-serving]] 还增加交接边界：prefill 结果或 KV 传输失败时，合同需要明确是否可重新 prefill、何时放弃，以及已占用的 decode 槽位如何回收。autoscaler 的扩容滞后和模型装载失败同样只能改变后续可用容量，不能补救已经过期的请求预算。

## Stale KV / Routing State

Router/EPP 的 prefix、会话粘性或 KV locality 索引可能过期；它应至多降低命中率、增加一次选择或重算成本，而不应绕过 engine 对模型 revision、token 前缀、块所有权和生命周期的校验。这里必须区分正确性与优化质量：选错 locality 是性能损失；把不匹配或已释放的 KV 当作可用数据才是正确性故障。相关路由职责见 [[inference-routing]]，engine KV 行为可参考 [[vllm]]、[[sglang]] 与 [[src-vllm-architecture]]。

## Failure Injection Matrix

| fault/scenario | observable signal | safe response | potentially lost state | metric/log/evidence to inspect |
|---|---|---|---|---|
| gateway unavailable | 连接失败、5xx、入口健康检查失败 | 由多入口、DNS/LB 或客户端策略决定是否切换；不要把未确认提交的请求当作可安全重试 | 未送达或入口尚未持久化的请求 | gateway availability、连接错误、request ID、LB health |
| EPP/router unavailable | 选端点超时、路由错误、EPP 健康检查失败 | 按合同 fail-open、fail-close 或 reject；记录选择策略 | 未完成的选择、局部 queue 视图 | router availability、route-decision log、discovery revision |
| worker not ready | readiness 为 false、连接拒绝、模型未就绪 | 从候选集剔除；无合格端点时拒绝或排队至预算结束 | 尚未开始的请求、预留槽位 | readiness transition、endpoint discovery lag、queue depth |
| prefill failure | 首 token 前 engine error、prefill 失败码 | 在幂等/预算/策略允许时重试或重新 prefill；否则返回失败 | 部分 KV、prefill 计算 | TTFT、prefill error、KV allocation/release log |
| KV transfer timeout | P/D 交接超时、connector timeout | 取消交接并按合同重算 prefill 或失败；释放两端预留资源 | 传输中的 KV、decode reservation | transfer latency、timeout、connector trace、cleanup log |
| decode failure before first token | worker error 且无已发送 token | 仅在策略与 deadline 允许时换 worker 重试；保留尝试关联 | 未发送的生成状态、部分 decode/KV | first-token flag、attempt count、engine error、deadline budget |
| decode failure after first token | stream reset、客户端收到部分 token | 终止流并报告部分完成；不假定透明重放 | 已发送 token 后的生成状态、流连接 | stream started flag、last token sequence、disconnect/error trace |
| stale KV index | locality 命中后 engine 拒绝 KV、命中率下降 | 让 engine 校验失败后回退到安全路径或重算，不使用不匹配 KV | 过期索引条目、一次 locality 优势 | KV validation reject、cache hit/miss、index revision/age |
| autoscaler lag | queue 增长、ready 副本少于期望、扩容事件滞后 | 继续有界准入与 shedding；不要承诺等待扩容 | 超时排队请求、临时容量计划 | desired/ready replicas、scale event latency、queue wait p99 |
| model-load failure | load error、worker 永不 ready、artifact/内存错误 | 隔离该 revision/worker，重新调度或拒绝；重试由部署策略决定 | 未完成加载、已分配显存或槽位 | model load log、image/artifact revision、OOM、readiness reason |

这张矩阵用于演练合同而非声明实现一致性。注入故障时应同时观察请求路径的 request ID/stream 状态，以及异步控制路径的 discovery、readiness、扩缩和模型生命周期事件；两者关联后才可区分真实执行故障与陈旧控制状态。
