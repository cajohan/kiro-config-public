---
inclusion: auto
trigger: model_decision
name: jira-bugfix
description: 用户说「处理一下 jira 的 bug 单 / 故障单」「修下 jira bug」之类时使用：读分配给用户的未解决故障单，复现、归类、修复、发 SIT、在 Jira 上流转为已解决。
---

# 一句话处理 Jira 故障单

用户说「帮我处理一下 jira 的 bug 单」这类话时，**直接启动一个工作流**（`run_workflow` + `workflowPrompt`），
不要先问范围。brief 写到当前工作区的 `.agents/tasks/jira-bugs-<MMDD>/brief.md`，日期用 `date +%m%d`，
内容按下面的流程写，并带上本次会话里已知的背景（相关需求的 `.agents/tasks/*/decisions.md` 路径、仓库和分支、
sit 分支名、各后端负责人）。2026-10-31 的 ZTHK-20881 这一轮就是这么跑的，
brief 可以参考 `youxin-admin-transaction/.agents/tasks/kr-jp-bugs-1031/brief.md`。

## 流程（写进 brief）

1. **取单**：ego 打开 `<内部地址>`（复用登录态），在页面里调 REST：
   `/rest/api/2/search?jql=assignee = currentUser() AND resolution = Unresolved AND issuetype = 故障 ORDER BY created DESC`。
   - 每张单要读完：描述（问题描述、操作步骤、预期、实际、环境、测试账号）、评论、附件。
   - 下载附件后先用 `file -b` 看真实格式再读（Jira 的 .png 常常是 JPEG）；图片单边超过 1600 就 `sips -Z 1600`。
   - 没有故障单就直接告诉用户「当前没有待处理的故障单」，然后结束。
2. **triage**：每张单都在 SIT 上只读复现，归类为以下之一：前端 bug / 需求理解差异（以原型为准）/ 后端问题 / 不归我们 / 已修好。
   - 判断归属看代码提交人（git log / blame）、原型章节、实际页面。分工表不可靠，不作为依据。
   - 不改别人的代码。不归我们的，写一句可以直接转给对方的话。
3. **修**：一张单一个提交，提交信息 `fix: <单号> <简述>`。
   - 每个提交前都要构建通过、改动文件 eslint 0 error，不动 lock 文件。
   - 修完由独立 reviewer 只读审查，最多 2 轮。
4. **发 SIT**：按 `git-workflow.md` 和对应项目的历史合并提交写法，合到部署分支。
   - 用 `--no-track` 从远程切临时分支，cherry-pick 后普通 push，绝不 force。
   - 查 pipeline 结果，并在 SIT 上逐张单回归。
5. **Jira 流转**（只对已修好、已上 SIT 的单）：
   - 点「接受」（已经是处理中的单跳过这步）→ 点「已解决」→ 在弹窗里填三项：
     - **BUG类型**：前端 bug 选「代码问题」；需求理解差异选「需求不明确」；原型就是这么设计的选「需求原型如此」。
     - **提交SIT验证时间**：直接输入 24 小时制，格式 `2026-11-2 17:57`。**不要用日历点「今日」**，它会按 12 小时制存错。
     - **备注**：两行，「原因：…」「解决：…」，需要提醒测试的写在后面（比如「请刷新后重测」）。
   - 最后点弹窗**右下角**的「已解决」提交，刷新页面确认状态变成「待验证」。
   - 先只做一张，确认整个流程走通后再批量处理其余的。
   - 不归我们的单不流转，留给用户自己转。
6. **汇报**：一张表列出单号 / 标题 / 归类 / 结果 / 提交 sha，然后是要转给别人的话（按人分组）、需要用户拍板的点、收尾状态。

## 边界

- 中间不要停下来问用户（见 `autonomy.md`）。只有遇到登录（CAS / Jira / GitLab，agent 触发不了记住密码的下拉框）、
  生产 / UAT / master、共用权限角色、不可逆操作时才暂停。
- 真实下单、撤单、强平、冻结、资金存入这类写操作，在 SIT 也不提交，只核对请求参数。
- 前端只做原型里有的东西。
