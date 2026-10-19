# 网页访问一律走 ego-browser

任何需要访问网页的场景，**默认用 ego-browser**（`ego-browser nodejs <<'EOF' ... EOF`），
不要用 web_fetch / fetch 这类抓取工具。

理由：ego-browser 是真实浏览器，且复用用户的登录态。web_fetch 只是匿名 HTTP 请求，
遇到需要登录、有反爬、或内容靠 JS 渲染的站点（Figma、Jira、GitLab 内网、飞书文档、
各类后台系统）一律拿不到东西，常见结果是 403 或一个登录页的 HTML。

适用范围：

- 看设计稿（Figma 取阴影/圆角/间距等具体数值）、看内网系统、看文档站。
- 验证本地页面效果、走查 UI、量 computed style。
- 抓页面数据、填表单、点按钮。
- 查资料看文章：也用 ego 打开读，不要 web_fetch。

例外：web_search 这类搜索工具照常用（它是找 URL，不是取页面内容）；
拿到 URL 后再用 ego 打开看。

## 机械性的浏览器操作外包给子 agent

> ⚠️ **已知 bug（2026-09-10 确认，2026-10-13 在 Kiro 1.2.56 复测仍未修复）**：
> IDE 里的子agent委派**无法**路由到 `~/.kiro/agents/ego.json` 这个自定义 agent。
> 已提 issue：https://github.com/kirodotdev/Kiro/issues/11333（关联 #11150）。
> 维护者 AnilMaktala 9/11 已确认并把 issue type 设为 Bug，根因是：IDE 侧委派查的注册表
> 只装了内置 agent，`~/.kiro/agents/` 的自定义 agent 被加载进另一份只给 CLI 用的注册表，
> 不会传到 IDE 这边（所以 `kiro-cli chat --agent ego` 能用，IDE 里找不到）。
>
> **委派入口在 1.2.x 变了**：
> - 1.1.x 及以前：`invoke_sub_agent`，`name="ego"` 报 `Agent 'ego' not found in registry`。
> - 1.2.56：会话里**不再提供 `invoke_sub_agent` 工具**，单 agent 委派改走
>   `run_workflow` + `workflowPath: "agent://<name>"`（`inputs.prompt` 必填）。
>   传 `agent://ego` 报 `Workflow references custom agent 'ego' which is not registered`，
>   可用的只有内置的 `wf-coder` / `wf-planner` / `semantic_reviewer` 等
>   （以 `run_workflow` 工具描述里的 AVAILABLE AGENTS 列表为准）。
>
> **在这个 bug 修复之前**：
> - 「跑在便宜模型（luna）」这个效果**做不到**：内置 agent 默认继承主会话当前模型
>   （sonnet/opus），没有独立更便宜的模型。
> - 「截图和大段 DOM snapshot 不进主会话上下文」这个效果**依然可以拿到**：用
>   `run_workflow` + `agent://wf-coder`，把 ego-browser 相关操作写进 `prompt`，
>   图片/快照留在 step 自己的会话里，只把文字结论带回主会话。
>   （2026-10-13 在 1.2.56 实跑过：wf-coder 能用 ego-browser 读 Jira、调 REST 接口、
>   下附件。坑：Jira 附件文件名是 `.png`，实际内容常是 JPEG，按 `.png` 存再读图会报
>   `image/png media type, but the image appears to be a image/jpeg`，**整个 step 直接失败**。
>   prompt 里要写明：下载后先 `file -b` 看真实格式，按真实格式命名扩展名再读。）
> - **等这条 bug 修复后**，验证方式：`run_workflow` 传 `workflowPath: "agent://ego"`
>   （或新版对应的委派入口传 `ego`），不报错、且 `ego` 出现在 AVAILABLE AGENTS 列表里，
>   返回内容明显来自更便宜的模型（响应风格/速度差异），才算真的生效，
>   不要想当然认为"新版本了就该自动好了"。

`ego.json` 是浏览器专用 agent，设计上打算跑在 **gpt-5.6-luna（0.1x）**，而主会话通常是
sonnet（1.3x）或 opus（2.2x）——差 13~22 倍。但如上所述，这条路目前被 bug 挡住。
**在 bug 修复前，外包的收益只剩「上下文隔离」这一项，「省模型倍率」这项暂时拿不到**——
1.2.x 起用 `run_workflow` + `agent://wf-coder` 外包（1.1.x 是 `invoke_sub_agent` +
`general-task-execution`）。

### 该外包的（机械、判据明确、结果能一句话回报）

- 读单/读文档：Jira、Confluence、飞书，含下载附件
- 取数：抓页面数据、量 computed style、查接口返回
- 照流程点：后台系统操作（如部署平台发布：克隆模板 → 填镜像 → 提交 → 发布 → 等 1/1）
- 轮询等待：等构建、等 Pod 就绪

### 不该外包的

- **需要视觉判断**的：「这个间距对不对」「像不像设计稿」——留在主会话
- **探索性调试**：不知道要找什么、需要根据上一步结果改下一步假设的
  （例：今天定位那个小圆圈——列 DOM、比对 rect、查 CSS 权重、做反证实验），
  这类来回穿透子 agent 会丢上下文、反而更慢更贵
- 只有一两次调用就完事的：起子 agent 的开销不值得

判断口径：**能把任务写成一段明确的指令、且只需要回报事实结论 → 外包；
需要我边看边改判断 → 自己做。**拿不准时按外包处理，回报不够再自己补一轮。

## 取不到内容时

先在 ego 里确认是不是登录态问题：ego 复用用户登录，但如果页面仍要求登录/验证码，
用 `handOffTaskSpace` 把控制权交给用户，说明要做什么，等用户确认后再 `takeOverTaskSpace` 继续。
不要退回去用 web_fetch 重试。

## GitHub issue / PR 查状态：用 `gh api`，不要用 ego-browser 打开页面

只是查 GitHub 上的 issue / PR 状态、评论、标签这类**只读信息**时，走 `gh api`
（或 `gh issue view` / `gh pr view` 等封装命令），不要用 ego-browser 直接打开页面。

理由（2026-09-15 踩过）：用 ego-browser 打开一个 issue 页面会复用用户自己的登录态，
GitHub 顶层页面访问会把该 thread 的通知**自动标记已读**，甚至可能被自动归档进 Done——
且这个消费动作**不可逆、也没有接口能查历史**，唯一现象就是用户回头发现"通知没了"，
排查起来要绕一圈（先怀疑 API 权限、`gh auth status` 查 scope、`gh auth refresh` 补
`notifications` scope，最后才定位到是浏览器访问顺手标记的）。

判断规则：

- 查状态、查评论、查 label、查 CI 结果 → `gh api` / `gh pr checks` 等命令行方式，
  不产生副作用，也比开浏览器截图快。
- 需要点按钮（合并 PR、加 label、批准 review）或者要看页面渐进渲染效果（预览 Markdown、
  看 diff 的视觉呈现）→ 才用 ego-browser。
- 首次用 `gh api notifications` 类接口前，先 `gh auth status` 确认 token 有没有
  对应 scope（默认 `gist, read:org, repo` 通常不含 `notifications`），没有就
  `gh auth refresh -h github.com -s notifications` 补上——这一步会走 OAuth device flow，
  需要用户自己在浏览器里输验证码确认，agent 没法代替。
