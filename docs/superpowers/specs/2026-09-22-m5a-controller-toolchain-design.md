# M5-A Kubernetes Controller 工具链地图设计

## 背景

`wiki/analysis/k8s-core-controller-map.md` 当前覆盖 Kubernetes controller/operator 学习路径，但核心表达仍是项目分层和文字说明。页面没有明确区分生成时工具链与运行时控制循环，也没有解释 Kubebuilder、controller-tools、controller-runtime 和 client-go 之间的真实边界。

三个核心 Entity 和 Source 页面形成于 2026-06-14。2026-09-22 的官方仓库 HEAD 为：

- controller-runtime `6ab2188a1fb1`
- Kubebuilder `5f31d1f3c075`
- controller-tools `030a93937cbb`

本次核验未发现会推翻现有 Source 架构的反转；主要缺口是跨项目关系、状态一致性和失败语义没有被画出来。

## 目标

- 把 `k8s-core-controller-map.md` 建成 M5-A 的 L1 入口。
- 区分 build-time generation 与 runtime reconciliation。
- 解释 client-go、controller-runtime、Kubebuilder 和 controller-tools 的职责边界。
- 用统一图例表达异步事件、workqueue、reconcile、状态写回和失败重试。
- 给三个核心 Entity 增加 M5-A 定位和当前证据入口。
- 保持旧 Source 摘要及其 ASCII 图不变。

## 非目标

- 不重写 `raw/` 或三个 Source 摘要。
- 不创建 client-go Entity 或新的 Source 页面；client-go 作为底层机制出现在地图中。
- 不在本 change 中处理 Kueue、Scheduler、Karpenter、DRA 或 GPU runtime。
- 不创建 M5 总 backbone；它在 M5-D 整合 change 中完成。
- 不把具体业务 Operator 的实现细节复制到工具链地图。

## 页面范围

### 主 Analysis

修改 `wiki/analysis/k8s-core-controller-map.md`：

- 增加 2026-09-22 当前上游核验表。
- 保留原有生态和学习路径信息。
- 用 D1、D3、D4、D5 取代当前过于宽泛的单张分层图。
- 更新 frontmatter date、sources 和 related。

### Entity

修改以下页面：

- `wiki/entities/controller-runtime.md`
- `wiki/entities/kubebuilder.md`
- `wiki/entities/controller-tools.md`

每页增加 `在 M5-A Controller 地图中的位置`，并明确其 evidence snapshot 与当前 Analysis 入口。

### 导航与生成层

- 更新 `wiki/index.md` 中 Kubernetes controller/toolchain 的入口说明。
- 在 `wiki/log.md` 追加一条 query 记录。
- 运行 `wiki/html-assets/build.py`，更新 HTML、index 和 graph。

## 架构边界

### Build-time

```text
Kubebuilder CLI
  init / create api / create webhook
              │ scaffold
              ▼
Go API types + markers + project layout
              │ parse / generate
              ▼
controller-tools / controller-gen
              │
              ├─ CRD schema
              ├─ RBAC
              ├─ webhook configuration
              ├─ deepcopy code
              └─ object/manifests YAML
```

Kubebuilder owns author workflow and project shape. controller-tools owns marker parsing and generated artifacts. Neither one owns the running reconcile loop.

### Runtime

```text
Kubernetes API Server
       - - watch event - -> Cache / Informer
                                  │ enqueue key
                                  ▼
Manager → Controller → Workqueue → Reconciler
                                  │
                                  ├─ cached read
                                  ├─ direct client write
                                  ├─ status / condition
                                  ├─ finalizer
                                  └─ owned resource
                                         │
                                         └ - observed state - -> API Server
```

client-go provides transport, watch, informer and workqueue foundations. controller-runtime composes these mechanisms into Manager, Cache, Client, Controller, Reconciler, Webhook and envtest abstractions.

## 图表设计

### D1：工具链职责图

回答：Kubebuilder、controller-tools、controller-runtime 和 client-go 分别负责什么。图中将 build-time 与 runtime 分成两个区域，并只使用稳定职责。

### D3：Reconcile 控制循环

回答：事件如何进入 cache/workqueue、Reconciler 如何读取状态、写回 desired/observed state，以及错误如何重新入队。

异步 watch、requeue 和 observed-state feedback 使用虚线；同步 API read/write 使用实线。

### D4：状态与一致性

覆盖：

- cached read 与 direct write 的差异。
- resourceVersion / optimistic concurrency。
- spec、status 和 condition 分离。
- owner reference 与 garbage collection。
- finalizer 的删除协议。
- observed generation 和幂等 reconcile。

### D5：失败边界

覆盖：

- stale cache 导致暂时性判断偏差。
- update conflict 与 retry。
- hot reconcile / rate-limit storm。
- webhook/certificate 未就绪。
- leader election 切换。
- finalizer 卡死与删除阻塞。
- controller 写错 ownership 或 status 的恢复边界。

## 当前证据

Analysis 页面记录以下执行时点的仓库 commit，并链接官方仓库或文档：

- controller-runtime `6ab2188a1fb1`
- Kubebuilder `5f31d1f3c075`
- controller-tools `030a93937cbb`

若实施时 HEAD 已移动，使用实施时重新解析的值，并保持三个 Analysis/Entity 页面一致。旧 Source 仍代表 2026-06-14 的 raw-backed 快照。

## 内容组织

`k8s-core-controller-map.md` 采用以下顺序：

1. 当前上游核验。
2. M5-A 的一句话边界。
3. D1 工具链职责图。
4. D3 Reconcile 控制循环。
5. D4 状态与一致性。
6. D5 失败边界。
7. 学习路径与项目边界表。
8. 与 AI Infra controller 的关系。
9. 选型与阅读建议。

原页面中 Kubernetes SIGs 和 OpenKruise 视角可以保留，但要移到核心控制器解释之后，避免抢占主线。

## 证据与冲突规则

- 当前仓库观察标注日期和 12 字符 SHA。
- 当前事实与 6 月 Source 快照分开表达。
- 若发现实际冲突，在 Analysis、Entity 和对应 Source 都加入 Conflict warning；不静默覆盖 Source。
- 仓库明确事实与架构推断分开。
- 不把生成工具、runtime library 和业务 controller 当成直接替代品。

## 完成标准

- Analysis 页面包含 D1、D3、D4、D5，且图例一致。
- 读者能从页面回答四个工具的职责边界。
- 三个 Entity 都链接 Analysis 和各自 Source。
- 所有改动页面 frontmatter 为有效 YAML。
- 没有新增 wikilink 断链。
- `raw/` 和三个 Source 页面无变化。
- Index 与 reading path 可以进入 M5-A。
- HTML 构建成功，生成图谱出现双向关系。
- 手工 HTML 页面保持不变。

## 风险与控制

- **把生成时和运行时混在一起**：D1 明确分区，D3 只画运行时。
- **把 cache 读当成强一致读**：D4 显式区分 cached read 和 direct write。
- **把 reconcile 当请求处理器**：D3 使用异步 watch/workqueue/requeue 语义。
- **页面膨胀**：项目内部细节链接 Source，不复制完整模块图。
- **事实漂移**：实施开始时重新解析 HEAD，并把 snapshot 日期写入页面。

## 验证策略

- 校验 D1/D3/D4/D5 heading 与 fence 数量。
- 使用 YAML parser 校验四个 Markdown 页面。
- 对新增 wikilink 做目标存在检查。
- 比较实施前后 `raw/` 与三个 Source 页面，确保未修改。
- 运行 HTML 构建器两次，第二次应保持 clean。
- 检查 Analysis、三个 Entity、index、log 和 graph 的生成结果。
- 运行 `git diff --check`。
