---
inclusion: always
trigger: always_on
---

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

委派方式：`invoke_sub_agent`，`name="ego"`。`~/.kiro/agents/ego.json` 是浏览器专用 agent，
设计上跑在 **gpt-5.6-luna（0.1x）**，主会话通常是 sonnet（1.3x）或 opus（2.2x），差 13~22 倍；
截图和大段 DOM snapshot 也留在子 agent 自己的上下文里，只把文字结论带回主会话。

> 历史：IDE 里委派不到自定义 agent 的 bug（https://github.com/kirodotdev/Kiro/issues/11333，
> 关联 #11150）在 1.1.x～1.2.56 都存在，期间只能用内置 agent（`wf-coder` / `general-task-execution`）
> 做上下文隔离。2026-11-20 在 Kiro 1.4.236 复测：`invoke_sub_agent` + `name="ego"` 调用成功，
> 不再报 `Agent 'ego' not found in registry`。子 agent 回复「具体模型型号未公开」，
> **是否真的跑在 luna 还没确认**；看到响应速度/风格不像便宜模型，或账单倍率没降，再回来查。
> 委派失败时退回内置 `general-task-execution` 做上下文隔离。
>
> 坑（2026-10-13）：Jira 附件文件名是 `.png`，实际内容常是 JPEG，按 `.png` 存再读图会报
> `image/png media type, but the image appears to be a image/jpeg`，整个子任务直接失败。
> prompt 里要写明：下载后先 `file -b` 看真实格式，按真实格式命名扩展名再读。

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

## 遇到登录页：agent 用不了浏览器记住的密码，直接交给用户点一下

登录页（CAS 统一认证、各类中台/后台）通常有浏览器记住的账号密码，用户自己点一下用户名框就会弹出
账号下拉框（CAS 上选 `<你的账号>`），一秒钟的事。

但 **agent 触发不出这个下拉框**（2026-10-21 实测）：`page.mouse.click` 点用户名框/密码框、
`ArrowDown + Enter`、先输入一个字母，都不弹，`:-webkit-autofill` 为 0。下拉框是 Chrome 密码管理器的
浏览器 UI，只响应用户本人在系统层面的点击，agent 经 CDP 派发的输入不会触发它；agent 也读不到已保存的密码。
**不要再花几轮去试自动填充**。

做法：

1. 先确认是不是真要登录：CAS 有自己的会话，用户登过一次后，别的 service 地址跳过去通常会自动放行。
   重新 `goto` 一次目标页，还停在登录页才算需要登录。
2. 需要登录就立刻 `task.handOff()`，跟用户说一句：「ego 停在 XX 登录页，点一下用户名框选 `<你的账号>` 登录，
   好了回我继续」。不要先自己试一圈再交。
3. 用户回复后 `takeOverTaskSpace(<id>)` 收回控制权继续。

## 取不到内容时

先在 ego 里确认是不是登录态问题：ego 复用用户登录，页面要求登录时按上一节处理。
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

## ego 升级：任务收尾后、确认没人在用再升级

输出里出现 `[ego-browser:notice] Ego Lite update is available` 时，**不要当场升级**，
等当前任务收尾后按下面的顺序处理（用户 2026-11-04 确认可以自动升级，不必每次问）：

1. 先 `finish()` 掉自己的 TaskSpace。
2. 检查有没有别人在用 ego，**任一项命中就不升级**，只在汇报里一句话提示「ego 有更新，等空闲再升」：
   - `listTaskSpaces()` 里除了 `id: 0` 的用户默认空间之外，还有其他空间（尤其 `ownership: "agent"`：
     多半是别的 Kiro 会话 / workflow 子 agent 正在跑）；
   - `ps -eo pid,etime,command | grep "[e]go-browser nodejs"` 有正在跑的脚本（etime 很长、明显是早已
     挂死的孤儿进程除外，例如挂了一天多的 `-e console.log("ok")`）。
3. 都空闲才跑 `ego-browser upgrade`。它会**重启 ego lite**，有别的空间在跑时 ego 会弹窗问用户
   「是否终止任务」，等于打断别人的会话。
4. 升级后确认生效：`ps -eo command | grep -o "ego Framework.framework/Versions/[0-9.]*" | sort -u`
   只剩新版本号、`ego-browser --version` 是新版本，再跑一次最小冒烟（开 about:blank → `finish`）。
5. 重新执行 `ego-browser skill` 读一遍当前版本的用法（新版本 API 可能有变化）。

踩过的坑（2026-11-04）：子 agent 还在用 TaskSpace 32 跑任务时，主会话连跑了两次 `ego-browser upgrade`，
ego 给用户弹了「是否终止任务」。那次是没先查 `listTaskSpaces()` 就直接升级。
