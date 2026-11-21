# 全局配置要点速览

`steering/` 里每条规则背后几乎都有一次踩坑。这里按主题归纳要点和来历，详细写法、命令和边界看对应文件（括号内是出处）。

## Git 工作流（`steering/git-workflow.md`，坑最密集）

- 功能分支**只能从 `origin/master` 切**（`--no-track`），任何时候不得 merge/rebase/cherry-pick sit/uat 的代码——部署分支和 master 历史分歧可达上千提交，带上就合不了 master（9-22、10-14 两次踩过）。
- sit/uat **一律以 `origin/` 为准**，不用本地同名分支（会被远程强推重置成「又领先又落后」）；**本地 master 时刻保持最新**（落后 45 个提交时读到旧代码出过事）。
- 操作部署分支前先 `git ls-remote --heads origin` 核实真名——裸名 sit 常已废弃，真身是 `sit-<日期>`（11-10 拿旧引用白做一轮）。
- 从远程切分支**不要设 upstream**：IDE push 按钮读 upstream 拼 refspec，会变成把功能分支直推 master。
- 合并冲突文件**不在本次改动清单里就 abort 改走 cherry-pick**，硬解会把基线旧状态带进部署分支。
- master/main **只走 MR 禁止直推**；构建标记只加在部署分支的合并提交上，格式照历史提交抄。
- **做完一个自洽阶段就提交**：>8 文件或跨两层就拆（22 文件单提交被指出过）。
- 审批弹窗别点 Always deny——会放大成 `deny git *`，全 git 被拦。

## 浏览器与网页（`steering/web-access.md`、`internal-axure-prototype.md`）

- 一切网页访问走 **ego-browser**（复用登录态），不用匿名抓取工具；查 GitHub issue/PR 用 `gh api`——浏览器打开会把通知自动标已读，不可逆。
- 机械性浏览器操作外包给 ego 子 agent（便宜模型跑，截图不污染主会话）；视觉判断、探索性调试不外包。
- CAS 登录页 **agent 触发不了系统记住密码的下拉框**，直接 handOff 让用户点。
- ego 升级前查 `listTaskSpaces()` 和进程，有人在用就不升。
- 内网 Axure 原型要起本地反向代理（PNA 拦截）；教训：「时好时坏」先重复测同输入，稳定复现就找规则，别归因随机。

## 验证与汇报（`steering/verification.md`）

- 自己能查的事实**不要甩给用户确认**（pipeline、线上代码、分支同步都自己查）。
- 下「没有/不支持」结论前**把入口走全**：页面所有 tab、部署分支代码、实际接口都要覆盖（只看默认 tab 误判「没有利率设置」改坏了代码）。
- 「缺接口/等后端」的结论**有时效，汇报前当场复测**（拿一周前的实测汇报，后端早已支持）。
- 有逻辑的改动必须**真实环境实测 + 查数据确认**，单测通过不算；改完逻辑要重测。
- 留给用户的命令**一行 ≤80 字符**，长的写成 `/tmp` 脚本给短命令。

## 命令写法与效率（`steering/shell-commands.md`）

- 复杂脚本（引号嵌套/多行/中文）**写成文件再执行**，不塞 heredoc——解析不了的命令永远匹配不上权限规则，每次都弹审批。
- 临时文件一律 `/tmp/<任务名>/`（写 `.git/` 会触发内置保护弹窗）。
- 改文件直接用编辑工具；**有依赖的调用别并行**（写文件和读它同时发出，读先跑会找不到）。
- 感觉慢先查内存换出（`vm_stat`），别当命令问题反复重试。

## 本地服务与环境（`steering/local-dev-server.md`）

- 构建失败先分**环境问题还是代码问题**：架构/运行时/原生模块字样 → 按 README 切 nvm 版本；**绝不为绕环境改业务代码**（dart-sass 顶 node-sass 被迫改 135 个文件，9 文件需求变 180 文件 diff）。
- dev server **不用 nohup**（孤儿进程占端口），起/验/杀同一轮；**绝不 `pkill node`**——一半是 IDE helper，全杀会打断编辑器。

## 错误处理与成本（`steering/error-handling.md`）

- 工具报错三级降级：重试一次 → 换方法 → 记下跳过继续；**环境/工具链类阻塞直接问用户**，别自己绕。
- 预计烧大量 credits 的动作（反复构建、多轮截图、大范围读写）**先报价再动手**。

## 截图（`steering/screenshot-limits.md`）

- 图片单边 **≤2000px**，超限图卡在会话里每轮请求都失败；Retina 记得 clip 或 `sips -Z`。
- 历史会话只留文字：`scripts/strip-session-images.py` 把 48h 前会话的图片换成占位文字（CLI 不能换 1x1 占位图，IDE 要同步重算 `publish.cursor`）。

## Review 与 effort（`code-review.md`、`effort.md`）

- 业务仓库 commit 前起**独立子 agent review**（不共享上下文，只看需求和 diff）；每段各送审一次。
- 子 agent 的 `effortLevel` **每次显式传 medium**——不传会继承主会话（reviewer 跑成 max：142 次调用 / 2 小时 / 133 credits）。

## 工作方式（`autonomy.md`）

- 需求**一路做完再汇报**，不问「要不要提交/发 sit」；歧义点列「怎么选的、为什么、要改动哪里」。
- 用户前端转后端：后端概念先用前端类比解释一句再做。

## 后端 Java（`internal-project-notes.md`）

- 老项目 **JDK 8 必须**；Maven 私服 http 要在 `~/.m2/settings.xml` 配 mirror。
- 本地起服务不用 `spring-boot:run`（拿旧 SNAPSHOT jar），先关 MQ/调度/服务注册副作用。
- 后端仓库各环境**手动发镜像**：合完部署分支即完，但推送触发的废 pipeline 要**立刻取消**（失败邮件烦）；sit/uat 分支名带日期会变，用前 `ls-remote` 核实。

## 配置仓库自身（`config-sync.md`、README）

- 白名单 gitignore 同步、双远端：公司 GitLab 推全部，GitHub 只推 `public` 脱敏快照；**公司电脑不挂 GitHub 远端**（安全软件 SIGKILL GitHub push，不许绕）。
- **不要给本仓库设 `core.hooksPath`**——会让 `git push` 稳定 137 被杀（11-16 对照实验定位；排障教训：一次只变一个变量、翻转两次再下结论）。
- 规则变更当轮提交推送；`settings/cli.json` 的 `lastUsed` 是运行噪音交给周快照（launchd 周日 21:00）。

## 配套文件速查

| 位置 | 内容 |
|---|---|
| `settings/permissions.yaml` | 全部允许 + 只拦 `git push*master*` |
| `settings/cli.json` | 默认 sonnet-5.5 + effort high，agentEngine v3 |
| `settings/mcp.json` | figma / deepwiki（只读工具白名单放行），fetch 已禁用 |
| `agents/dev.json` | 默认 agent，`agentSpawn` 挂去图脚本 |
| `agents/ego.json` | 浏览器子 agent（便宜模型跑机械操作） |
| `dotfiles/` | 机器 dotfile（maven settings 等，含凭据只进内部 GitLab）；`~/.m2/settings.xml` 软链接过去 |
| `hooks/strip-session-images.json` | SessionStart → 去图脚本 |
| `steering/jira-bugfix.md` | 「处理一下 jira bug 单」一句话启动的完整工作流 |
| `steering/internal-api-docs-navigation.md` | 内网接口文档导航 + 中台地址表 + 测试交易密码 |
| `steering/internal-gitlab-manual-build.md` | CI_COMMIT_MESSAGE 构建触发机制与手动 Run Pipeline |
