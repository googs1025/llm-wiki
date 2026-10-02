# M5-B Kubernetes Workload / Scheduling 地图设计

## 背景

当前 `kubernetes-workload-gang-scheduling-design.md` 和 `kubernetes-scheduler-core-design.md` 主要按 KEP 分类解释 Workload、gang scheduling、queue/requeue、placement 和 preemption，但没有把工作负载 API、Kueue admission、kube-scheduler placement 与 Karpenter capacity 串成完整控制链。

相关 Entity/Source 多形成于 2026-06-14。当前官方项目已经出现需要进入地图的重要变化：

- Kueue 的核心 API 已围绕 Workload、LocalQueue、ClusterQueue、ResourceFlavor、AdmissionCheck、Topology 和 Cohort 组织。
- JobSet 使用 `v1alpha2`，提供 ReplicatedJob、DependsOn、failure/success policy、coordinator 和 shared PVC lifecycle。
- LWS 同时提供 `LeaderWorkerSet v1` 和 `DisaggregatedSet v1`；后者用多个 LWS 表达 prefill/decode/encode 等角色。
- kube-scheduler 的 scheduling/binding cycle 明确包含 QueueSort、PreFilter、Filter、Score、Reserve、Permit、PreBind、Bind 等扩展点。
- Karpenter 用 NodePool、NodeClass、NodeClaim 表达约束、容量请求和节点生命周期；它响应 unschedulable Pods，但不替代 kube-scheduler 的 Pod binding。

2026-09-25 当前官方仓库 HEAD：

- Kueue `edf96be8809c`
- JobSet `03f9dccef945`
- LWS `d4f1525f15a4`
- scheduler-plugins `6df8d8e4ae5f`
- Karpenter `06bc3b4b94dd`

这些是 dated default-branch snapshots，不是 release 标识。

## 目标

- 把 `kubernetes-workload-gang-scheduling-design.md` 建成 M5-B L1 入口。
- 建立 Workload API → Kueue admission → scheduler placement → Karpenter capacity 的职责主干。
- 更新 `kubernetes-scheduler-core-design.md` 的 scheduler cycle 与 queue/requeue 图。
- 解释 JobSet、LWS、DisaggregatedSet 的不同 workload ownership 和 failure semantics。
- 给 Kueue、JobSet、LWS、scheduler-plugins、Karpenter 五个 Entity 增加当前证据和 M5-B 定位。
- 保持历史 Source/ASCII 图不变，当前变化进入 Analysis/Entity。

## 非目标

- 不在本 change 中解释 Device Plugin、DRA、CDI 或 GPU runtime；这些属于 M5-C。
- 不在本 change 中重画 HPA/KEDA/metrics 横切控制循环；这些属于 M5-D。
- 不创建 M5 总 backbone。
- 不把 Kueue 描述成 Pod scheduler，也不把 Karpenter描述成 scheduler replacement。
- 不把 JobSet、LWS 和 DisaggregatedSet描述成相互替代的单一 workload API。
- 不修改 `raw/` 或五个历史 Source 页面，除非发现必须双向标记的事实冲突。

## 页面范围

### Analysis

修改：

- `wiki/analysis/kubernetes-workload-gang-scheduling-design.md`
- `wiki/analysis/kubernetes-scheduler-core-design.md`

第一张是 M5-B L1 与跨项目主线；第二张专注 Pod scheduling/binding cycle、queue/requeue 和 scheduler extension points。

### Entity

修改：

- `wiki/entities/kueue.md`
- `wiki/entities/jobset.md`
- `wiki/entities/lws.md`
- `wiki/entities/scheduler-plugins.md`
- `wiki/entities/karpenter.md`

每页增加当前 commit snapshot、历史 Source 边界和 `在 M5-B Workload / Scheduling 地图中的位置`。

### 导航与生成层

- 更新 `wiki/index.md` 中 Workload/Scheduling 入口。
- 在 `wiki/log.md` 追加一条 query 记录。
- 重建 HTML、index 与 graph。

## D1：职责主干

```text
Workload expression
  JobSet · LeaderWorkerSet · DisaggregatedSet
             │ integration / PodSets
             ▼
Admission and quota
  Kueue Workload · LocalQueue · ClusterQueue
  ResourceFlavor · Cohort · AdmissionCheck · Topology
             │ admitted / unsuspend
             ▼
Pod placement
  kube-scheduler framework · scheduler-plugins
             │ bind to existing node
             ▼
Node capacity feedback
  unschedulable Pods → Karpenter NodePool/NodeClass → NodeClaim → Node
             │ node ready
             └ - requeue / retry - -> kube-scheduler
```

职责边界：

- Workload API 管理组、角色、子资源和生命周期。
- Kueue 决定何时以及用哪类 quota/flavor 准入，不决定最终 Node。
- kube-scheduler 决定 Pod 与 Node 的绑定。
- scheduler-plugins 扩展 kube-scheduler，不独立拥有 Workload lifecycle。
- Karpenter 在现有容量不足时创建或回收 Node，不直接绑定 Pod。

## D2：Admission 与 Scheduling 路径

```text
Create JobSet / LWS / DisaggregatedSet
       - - integration - -> Kueue Workload / PodSets
                                   │ queue reference
                                   ▼
                       LocalQueue → ClusterQueue / Cohort
                                   │ quota + flavor + checks
                                   ▼
                ResourceFlavor / AdmissionCheck / Topology
                                   │ admitted
                                   ▼
                       unsuspend child workload / Pods
                                   │
                                   ▼
QueueSort → PreFilter → Filter → Score → Reserve → Permit → PreBind → Bind
```

该图只表达逻辑路径。不同 integration 可能由 owner controller 创建 Workload 或直接管理 suspend/PodSets，页面必须标注证据边界。

## D3：Capacity Feedback

```text
Pod remains Unschedulable
       - - condition/event - -> Karpenter provisioning controller
                                      │ combine constraints
                                      ▼
                    NodePool + NodeClass + pending Pod requirements
                                      │ create immutable request
                                      ▼
                                  NodeClaim
                         launch → register → initialize
                                      │ Node ready
                                      └ - scheduler requeue - -> Pod placement
```

Disruption 是另一条控制路径：Karpenter 评估 drift、consolidation、expiration 和 budgets，必要时 pre-spin replacement，再 taint/drain/terminate。D3 不把它混入 scale-up 热路径。

## D4：Workload 生命周期

用对比表表达：

- JobSet：ReplicatedJobs、DependsOn、coordinator、success/failure policy、restart strategy、shared PVC retention。
- LWS：leader/worker group、replica、group restart、placement/subgroup、rollout ownership。
- DisaggregatedSet：roles、slices、child LWS、role-specific scale、coordinated rollout/drain。
- Kueue Workload：suspend/admission、quota reservation、PodSets、admission checks、eviction/requeue。

## D5：失败边界

覆盖：

- LocalQueue/ClusterQueue 缺失或 inactive。
- quota/flavor 不足、borrowing/preemption 失败。
- AdmissionCheck 未通过或外部 provisioning 卡住。
- topology/placement 无解。
- scheduler Filter/PostFilter 无 feasible node。
- Karpenter NodeClaim launch/register/initialize 失败。
- JobSet child Job failure 与 restart policy。
- LWS group failure、DisaggregatedSet role/slice rollout/drain。
- PDB、do-not-disrupt、termination grace 与 Karpenter disruption 冲突。

每项区分自动重试、控制器级恢复与人工处理边界。

## Scheduler 下钻页

`kubernetes-scheduler-core-design.md` 增加：

- Scheduling cycle 与 binding cycle 图。
- active/backoff/unschedulable queue 与 QueueingHint/requeue 关系。
- scheduler-plugins 与 in-tree framework 的边界。
- Kueue admission 在 Pod scheduling 之前，Karpenter capacity 在 unschedulable feedback 之后。
- 失败路径：Filter failure、PostFilter/preemption、Permit wait/reject、PreBind failure、Bind failure。

## 证据与快照规则

- Analysis 记录 2026-09-25 当前 commit 与官方文档链接。
- 实施时重新解析 HEAD；若发生移动，使用实施时 snapshot 并标注日期。
- Entity 把当前证据与 2026-06-14 raw-backed Source 分开。
- API version、feature stage、默认行为和性能数字必须绑定版本。
- 发现与历史 Source 的真实冲突时，在 Analysis/Entity/Source 双向添加 Conflict warning；仅新增能力缺口不等于冲突。

## 内容组织

M5-B L1 页面顺序：

1. 当前上游核验。
2. D1 职责主干。
3. D2 Admission/Scheduling。
4. D3 Capacity feedback。
5. D4 Workload 生命周期。
6. D5 失败边界。
7. 现有 KEP 演进、preemption、topology、controller API 和项目关系。
8. 选型与阅读路径。

Scheduler 页面顺序：

1. 当前 Kubernetes/scheduler evidence。
2. Scheduler framework cycle。
3. Queue/requeue。
4. Filter/Score/Reserve/Permit/Bind。
5. Kueue/Karpenter 边界。
6. 失败、preemption 和版本状态。

## 完成标准

- L1 页面包含 D1–D5，职责和反馈箭头一致。
- Scheduler 页面有独立 scheduling/binding cycle 和 queue/requeue 图。
- 五个 Entity 具有 evidence snapshot、M5-B 定位和双向链接。
- LWS 页面明确包含 DisaggregatedSet，而非仍只描述 LeaderWorkerSet。
- JobSet 页面将 volatile API/failure behavior 绑定当前 snapshot。
- Kueue 不被描述为 scheduler，Karpenter 不被描述为 Pod binder。
- 所有改动 Markdown frontmatter 是有效 YAML。
- 无新增 wikilink 断链。
- `raw/` 与五个 Source Markdown 无变化，或只有经批准的双向 Conflict warning。
- Index/Log/HTML/graph 同步，手工 HTML 不变。
- 两次构建幂等，`git diff --check` 通过。

## 风险与控制

- **把四层画成同步调用链**：异步 integration、admission、unschedulable feedback 使用虚线与文字限定。
- **混淆 admission 和 placement**：D1/D2 单独分区。
- **混淆 pending Pod 与 capacity provisioning**：D3 明确 scheduler 先判定 unschedulable，Karpenter 再供给 Node。
- **API 漂移**：所有 v1/v1alpha2/v1beta2 与默认行为标注 snapshot。
- **页面过大**：内部实现留在 Source；Analysis 只保留跨项目控制边界。

## 验证策略

- 校验 D1–D5 与 scheduler cycle/requeue headings、fences 和箭头图例。
- YAML parser 校验 7 个内容页。
- baseline-aware wikilink 检查。
- 比较 raw/Source 路径，确保保护。
- 构建 HTML 两次并比较 diff hash。
- 检查 Index、Log、Analysis、Entity、graph 双向关系。
- 检查生成页中 code fence 不含被转义的 wikilink anchor。
- 运行 `git diff --check`。
