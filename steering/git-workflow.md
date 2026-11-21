---
inclusion: always
trigger: always_on
---

# Git 工作流约定

## 合并后切回原分支

合并到部署/集成分支后，**必须切回执行合并前所在的工作分支**，不要停留在部署分支上。

```bash
git branch --show-current          # 先记录原分支
git checkout <部署分支>
git fetch origin
git merge --ff-only origin/<部署分支>
git merge <功能分支> --no-edit
git push origin <部署分支>
git checkout <原分支>              # 最后切回来
```

## sit / uat / master 以远程为准，不要依赖本地同名分支

用户明确说明（2026-10-20）：这类分支理论上只会往里合代码，**一律以 `origin/<分支>` 为准**，
本地同名分支可能是很旧的、已经分叉的（subapp-admin-sg 的本地 `sit` 比远程多 74、少 34 个提交）。

- 操作前先 `git fetch origin`，所有判断（差异、冲突、历史风格）都基于 `origin/<分支>`。
- 不要 `git checkout sit` 去用本地同名分支；用 `git switch -c <临时分支> --no-track origin/sit`
  从远程切出来，在上面 cherry-pick / merge，再 `git push origin HEAD:sit`。
- 不要 `git switch -c sit --track origin/sit`：本地已有同名分支时会失败，且之后的 merge 会落到错误的分支上。
- 部署分支会被重置（force push）过：subapp-admin-sg 的 `origin/sit` 在 2026-03-12 被强推重置到以 master 为底的新历史，
  旧提交从远程消失，本地旧 sit 就成了"又领先又落后"。判断方法：`git reflog show origin/sit | grep forced-update`。
  遇到本地和远程双向分叉时**不要 `git pull --rebase`**（会把已被远程丢弃的旧提交重放回 sit，等于把废弃历史再推回去），
  直接以远程为准重建本地分支。
- 不要去 reset / 清理本地旧的 sit，除非用户要求；本地分支用完直接 `git branch -D` 删掉，不用问
  （用户 2026-10-23 确认；`dev.json` 已去掉对 `git branch -D` 的拦截）：
  - 临时分支（从部署分支切出来做 merge / cherry-pick、`git push origin HEAD:sit` 推完即弃的那种）本身不用推到远程，用完直接删。
  - 功能分支删本地前，确认同名远程分支存在且已同步（`git status -sb` 没有 `[ahead N]`，或 `git log origin/<分支>..<分支>` 为空）；没推上去就先推再删。

## 本地 master 时刻保持最新（读代码、切分支前先同步）

用户明确要求（2026-11-09）：**本地的 `master` 要时刻保持最新**，上一节"以远程为准"里 master 这一项以本节为准。
踩过的坑：`user-server` 本地 master 停在 9/24，`origin/master` 已到 11/02（差 45 个提交、53 个文件），
我据此读的交易密码、`checkTradePassword` 等代码是旧版本，方案里引用的行为有一部分已经变了，事后才发现。

- **什么时候同步**：开始一个任务前、读某个仓库的代码前、从 master 切功能分支前，对涉及的仓库先同步一次，
  不要等到用户发现落后才补。涉及多个仓库（如 `user-server` + `user-admin`）每个都同步。
- **怎么同步**（只允许快进，不会丢东西）：

```bash
git fetch origin
# 当前就在 master 上：
git merge --ff-only origin/master
# 当前在别的分支上：不用切换，直接快进本地 master
git fetch origin master:master
```

- 快进失败（本地 master 有自己的提交或已分叉）说明本地 master 被污染过：**不要 reset / 强制覆盖**，
  先告诉用户，说明多出来的是哪些提交，由用户决定。
- 工作区有未提交改动时，`git fetch origin master:master` 不受影响；`merge --ff-only` 遇到冲突会拒绝，同样先告知用户。
- 读别人在做的分支（如同事的 `chance/...`）也一样，先 `git fetch origin` 再看 `origin/<分支>`，
  不要凭上一次 fetch 的结果下"没有提交"这类结论（同事文档的提交是我 fetch 之后才推上来的）。
- sit / uat 的规则不变：仍然不用本地同名分支，一律从 `origin/<分支>` 切临时分支。
- 阅读只读型代码（比如查别的服务怎么实现）时，同样以最新的 `origin/master` 为准；
  拿不准本地是否最新，就直接 `git show origin/master:<路径>` 读远程版本。

## 确认部署分支的真实名称

- **用 `git ls-remote --heads origin` 看远程真实存在的分支**，并且 fetch 时带 `--prune`。不带 `--prune` 的 fetch 会保留已被删除分支的
  旧引用（`origin/sit` 看着还在，远程其实已经没有了）。2026-11-10 user-admin 就踩了：拿旧的 `origin/sit` 判断冲突、切了 cherry-pick 分支，
  推上去才发现 GitLab 上没有 `sit`（真实是 `sit-261104`），白做一轮还得删掉远程分支重来。

用户说"合到 sit / uat"时，不要想当然合到裸名分支。很多项目的裸名 `sit`/`uat` 已废弃，实际用带日期的分支（如 `sit-20260712`）。先确认：

```bash
git branch -a | grep -i <关键字>
git log -1 --format="%h %ci %s" origin/<候选分支>
```

以最近有提交的那个为准；有多个相近候选且无法判断时，问用户。

## 功能分支任何时候都不得携带 sit / uat 的代码

用户明确规定（2026-10-22），**没有例外**：

1. **只能从 `origin/master` 切**：`git switch -c <分支> --no-track origin/master`。
   不能从 sit / uat 及任何带日期的部署分支（`sit-*`、`uat-*`）切，用户说"基于 sit 上的代码改"也不行，
   遇到这种说法要提醒用户这条规则，改为从 master 切或在对应需求分支上做。
2. **切完之后也不能把 sit / uat 的代码合进来**：功能分支上禁止
   `git merge origin/<sit|uat>`、`merge --ff-only`、`rebase origin/<sit|uat>`、`pull origin <sit|uat>`、
   以及 cherry-pick 部署分支上的合并提交或别人只在部署分支上的提交。
3. **依赖尚未进 master 的需求分支时**：直接在那个需求分支上提交，或从它切
   （`git switch -c <新分支> --no-track origin/<需求分支>`）。前提是该需求分支本身也满足本规则。
4. **提交/推送前自检**：`git log --oneline origin/master..HEAD` 只应出现本需求的提交；
   出现部署分支的合并提交（`Merge ... into sit`/`uat`）或别人的提交，就是违规，停下来处理。
5. 子 agent 的计划里出现「把部署分支合进功能分支」「基于 sit 切」这类步骤，执行前要拦下来。

部署分支自己的操作不受影响：合 sit/uat 时在**临时分支**上从 `origin/<部署分支>` 切出来 merge/cherry-pick，
推完即弃，那是部署分支的提交，不是功能分支。

**后果**（2026-09-22 踩过）：部署分支和 master 之间往往存在历史分歧，可能积累到上千个提交。
功能分支一旦带上部署分支历史，就没法合 master，合到另一个部署分支（如从 master 切的 `sit-260921`）时
还会摆出大量与本次改动无关的冲突。

**2026-10-14 踩过**：`feat/1013_john_securities-sg-i18n` 按规则从 master 切出，但规划时为了拿到页面最新代码
（在一个还没进 master 的需求分支上），第 1 步写成 `git merge --ff-only origin/sit-260805`，
分支瞬间带上 63 个 sit 独有提交，没法合 master，最后被搁置、改动漏发。

## 从远程分支建功能分支时不要设 upstream

`git checkout -b <分支> origin/master` 会顺手把 upstream 设成 `origin/master`，在 `.git/config` 里写下：

```
branch.<分支>.merge = refs/heads/master     ← 坑
```

**后果**：IDE（Kiro / VSCode）的 push 按钮不敲裸 `git push`，而是读 upstream 自己拼显式 refspec，
于是变成把功能分支直接推进 master：

```bash
git push origin <功能分支>:master           # 跳过 sit/uat 与 review，非常危险
```

显式 refspec 会**绕过 `push.default = simple`**——命令行敲裸 `git push` 时 simple 会因
「upstream 名与本地分支名不一致」而拒绝，但 IDE 这条路径不受它保护。

正确做法：

```bash
git switch -c <分支名> --no-track origin/master   # 从远程切出但不设 upstream
# ……开发、提交……
git push -u origin <分支名>                       # 首次 push 时才绑定同名远程分支
```

已经踩了的分支这样补救（不影响提交）：

```bash
git branch --unset-upstream                      # 或直接 git push -u origin <分支名> 覆盖掉
git rev-parse --abbrev-ref @{u}                  # 确认已指向 origin/<同名分支>
```

顺手确认没推错：

```bash
git log --oneline -1 origin/master               # 应停在合并前的位置
git branch -r --contains <本次首个提交>            # 应只列出自己的功能分支
```

## 开发完的改动：ego 验完直接发 sit，不用再问

用户明确说明（2026-10-22）：**只要是开发完的改动，ego 验证通过后直接合到 sit 并推送，不要再问「要不要发 sit」。**

- 流程：改完 → 构建 → ego 验证 → review（按 `code-review.md`）→ commit → 推功能分支 → 合 sit（带构建标记）→ 查 pipeline → SIT 实测。
- **后端（Java）仓库例外**：各环境都是手动发镜像，合完部署分支就停，不加构建标记；但每次推送触发的 pipeline 要立刻取消，见 `internal-project-notes.md`「后端仓库不用管 CI/CD」。
- **没开发完的**（例如接口还没对接、后端未就绪、只做了一半）：只 commit 并推到远程功能分支，**不合 sit**，回复里说明为什么没发。
- uat / master 不在此列：发 uat 仍按用户指示，master 仍只走 MR。

## 本地功能分支要推到远程，并保持同步

功能分支**不要只留在本地**：每次在功能分支上提交后，都推到同名远程分支
（首次 `git push -u origin <分支名>`，之后 `git push`），保证远程和本地一致。
合并到 sit/uat 等部署分支之前，也要先确认功能分支已经推上去。

- 远程功能分支是后面提 MR 合 master 的来源；合入 master 时 MR 会勾选删除源分支，
  不需要自己清理远程分支。
- 只合进部署分支、功能分支本身没推，会出现「改动只在 sit 上、远程找不到功能分支」，
  别人没法 review，本地丢了也找不回（2026-10-12 踩过）。

确认方式：

```bash
git status -sb | head -1        # 应显示 ...origin/<同名分支>，且没有 [ahead N]
```

## 分支命名规范

格式：`<类型>/<日期MMDD>_<作者名>_<JIRA号>_<功能描述>`

示例：`feat/1031_alice_PROJ01_open-account`

- **作者名取 `git config user.name`，不要照抄上面示例里的 `alice`。**
  拿不准时先看仓库历史：`git log -20 --format="%an" | sort -u`。
- 功能描述用英文小写 + 连字符。
- 类型沿用 commit 类型（feat/fix/refactor 等）。

## GitLab 仓库的 master / main 只能通过 MR 合并，禁止本地直推

**对公司 GitLab 上业务仓库的 `master` / `main`，`git push origin master`（或 `main`）一律不允许**，
即使改动很小、即使 uat 已经验收通过、即使用户说"可以发生产"——"发生产"指的是**提 MR 等合并**，
不是自己把 master 推上去。

**适用范围只限公司 GitLab**（主机名见 `internal-project-notes.md`，以 `git remote -v` 为准）。
`~/.kiro` 配置仓库虽然也推公司 GitLab，但属于个人配置仓库，直接推 `main`、不走 MR，见 `config-sync.md`。

sit / uat 等部署分支可以本地合并后 `git push`；**master / main 例外**。

正确流程：

```bash
git push -u origin <功能分支>          # 功能分支推到远程（MR 的来源）
# 然后在 GitLab 提 MR：<功能分支> → master
```

本地**不要**先 `git checkout master && git merge <功能分支>`：master 的合并由 MR 完成，
本地提前合了只会留下一个随时可能被误推的提交。已经合了就回退掉：

```bash
git checkout master
git reset --hard origin/master        # 仅当本地 master 的多余提交确实已存在于功能分支
git checkout <原分支>
```

### MR 的固定勾选项

| 选项 | 怎么选 |
|---|---|
| 审核人 | **选自己**（Assignee：点 "Assign to me"） |
| Delete source branch when merge request is accepted（合并后删除源分支） | **勾选** |
| Squash commits when merge request is accepted（合并后压缩提交） | **不勾选** |

源分支由 MR 自动删除，不用自己 `git push origin --delete`。

### 构建标记写在哪

master 的 pro 构建同样靠 commit message 里的 `--build` 触发（见下一节）。走 MR 时这个标记
要落在**MR 产生的那条合并提交**上，也就是 MR 标题/合并提交信息里带 `--build`——不要为了带标记
而在功能分支的提交上加（功能分支提交不带标记，见下一节）。MR 合并后确认 pipeline 是否真的
触发了，没触发就按 `internal-gitlab-manual-build.md` 手动 Run Pipeline 补一次。

### 合进 master 不等于上线

几乎所有项目的 pro pipeline 都只构建不发布，生产发布由用户本人在 Jenkins 手动发：
agent 做到「MR 合并 → pro pipeline success」为止，汇报「待你发布」，不要自己去点发布。
少数例外项目（如官网走 diamond）的发布步骤和完成标准见 `internal-project-notes.md`。

## 日期以系统时间为准

分支名里的 `<日期MMDD>`、提交说明里的日期，都用 `date` 或 `git log -1 --format=%ci` 取**机器上的实际日期**，
不要用会话上下文里给的"当前日期"（2026-10-14 这次上下文写的是 08-27，导致分支名写成了 `0827`）。

## 审批弹窗不要点「Always deny」

执行 `git push origin master` 这类命中 `ask` 规则的命令时，Kiro 会弹审批框。**别点 Always deny**：
它会把规则放大成整个命令族（这次变成 `deny shell: git *`，所有 git 命令全被拦）。只想拒绝这一次就点 Deny。
误点后的修复是编辑 `~/.kiro/settings/permissions.yaml`，把 `git *` 收窄成 `git push*master*`
（该目录有内置写保护，agent 改不了，要用户自己改）。

## 构建标记只加在部署分支的提交上

- **自己的功能分支提交不要带 `--build`**，功能分支不触发部署构建，加了是噪音。
- **只有合并到 sit/uat/master 等部署分支时**，才在那条合并提交信息里带构建标记
  （格式按目标分支历史，如 `--build -d trade-3`）。

## 合并提交信息是否要带构建标记

各项目 CI 触发方式不同：有的不需要任何标记，有的要 `--build`，有的要 `--build <具体模块>`。
**合并前必须先查目标分支的历史提交，照着已有风格写**，不要凭印象加或不加。

```bash
# 1. 看目标分支最近的合并提交怎么写的
git log --merges -5 --format="%s" origin/<部署分支>

# 2. 看 CI 配置里的触发条件（确认标记名和是否区分模块）
grep -rn -- "--build" .gitlab-ci.yml .github/workflows/ Jenkinsfile 2>/dev/null
```

判断规则：

- 历史合并提交普遍带某个标记 → 本次也带上，格式保持一致。
- 历史提交都不带 → 不要自己加。
- 需要指定模块（`--build <模块>`）时，按本次改动涉及的模块填；无法确定改哪个模块时，问用户。
- CI 配置里的条件（如 `$CI_COMMIT_MESSAGE =~ /\-\-build/`）是最终依据，以它为准。

## 冲突不在本次改动范围内时，改走 cherry-pick

合并到部署分支出现冲突，先判断冲突文件是不是本次改动碰过的：

```bash
git diff --name-only --diff-filter=U          # 冲突文件
git diff --name-only <基线> <功能分支HEAD>     # 本次真正改过的文件
git log -1 --format="%h %ci %s" $(git merge-base origin/<部署分支> HEAD)
```

**只要有冲突文件不在本次改动清单里，就不要硬解**——这类冲突来自功能分支基线（通常是 master）
和部署分支之间的历史分歧，硬解会把基线上较旧的状态带进部署分支，覆盖别人的工作。

处理方式：`git merge --abort`，然后从部署分支切新分支、cherry-pick 本次提交：

```bash
git merge --abort
git checkout -b <功能分支>-to-<部署分支> origin/<部署分支>
git cherry-pick <commit1> <commit2> ...        # 按顺序
# 只解自己改动范围内的冲突
git checkout <部署分支>
git merge <功能分支>-to-<部署分支> --no-edit
git push origin <部署分支>
git checkout <原分支>
```

要点：

- cherry-pick 过程中若冲突文件仍不属于本次改动，说明判断有误，停下问用户。
- commit hash 会变，原功能分支保留不动，后续合 master 时用原分支。
- 顺带确认部署分支是否领先基线很多（`git log --oneline <基线>..origin/<部署分支>`），
  领先过多通常意味着有改动漏合回基线，值得提醒用户。

## 合并前后的检查

- 合并出现大量与本次改动无关的冲突时，先停下确认是否合错了分支，不要硬着头皮解冲突。
- push 后用 `git diff origin/<分支> --stat` 确认本地与远端一致。

## 提交习惯

- 只在用户明确要求时创建提交。
- 优先 `git add <具体文件>`，不要 `git add .`。
- 提交前先 `git diff` 复核，确认没有夹带无关改动或调试代码。
- 业务仓库的提交，构建通过后、commit 之前起独立子 agent 做 code review，见 `code-review.md`。

## 做完一段就提交，别攒成一个大 commit

多步任务里每完成一个**自洽且能构建通过**的阶段就提交一次，不要全做完才提。好处：

- 用户能分段 review，不用面对几十个文件的 diff（改动文件数一多用户就会警觉，这是合理反应）。
- 出问题好回退到上一个可用状态。
- 长任务中途可能因为额度/时间中断，已提交的部分不会丢，下次接着干。

要点：

- **每个 commit 自己能构建通过**。强耦合的改动（例如整页重写：组件按 key 取文案，
  组件和文案文件必须同时在）中间没有能编译的切点，那就老实做成一个 commit，
  但要在回复里说明「为什么这段不能再拆」，别让用户以为是偷懒。
- **commit 前硬检查（2026-11-10 踩过：user-server-sg 一个提交塞了 22 个文件，被用户指出）**：
  `git diff --cached --name-only | wc -l` 超过 8 个，或同时包含「基础工具/枚举」「核心逻辑」「对外接口」「钩子接入」
  中的两类以上，就先按依赖顺序拆提交，每个提交单独构建 + 跑相关测试。拆不了才做成一个，并说明为什么。
  新项目不熟时，写代码的同时就按层分批提交，不要等全写完再一次提。
- 已推送的分支要重新拆提交：**不 force push**，从 `origin/master` 新开分支，用 `git checkout <旧分支> -- <文件>`
  按组还原并逐个提交，最后 `git diff <旧分支> HEAD` 确认内容一致；MR 关掉旧的、按新分支重提。
- `git reset --hard` 被权限规则拦，撤销自己暂存的改动用 `git restore --staged --worktree .`。
- `git status` 的文件数明显超出需求范围时，**先停下自查**是不是夹带了临时改动/环境绕路
  （见 `local-dev-server.md`），而不是继续往上堆。
- 每次提交前跑一遍构建；提交后 `git status --short` 确认工作区干净。
