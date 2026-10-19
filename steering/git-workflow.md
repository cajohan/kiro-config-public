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

## 确认部署分支的真实名称

用户说"合到 sit / uat"时，不要想当然合到裸名分支。很多项目的裸名 `sit`/`uat` 已废弃，实际用带日期的分支（如 `sit-20260712`）。先确认：

```bash
git branch -a | grep -i <关键字>
git log -1 --format="%h %ci %s" origin/<候选分支>
```

以最近有提交的那个为准；有多个相近候选且无法判断时，问用户。

## 切功能分支要从 master，不要从部署分支（sit/uat）切

新功能分支的基线默认从 `origin/master` 切，不要从 `sit`/`uat` 等部署分支切——即使当时
手头正好在看 sit 环境、或者想"基于最新部署的代码写"，也不要图方便直接 `checkout -b <新分支> origin/sit`。

**后果**（2026-09-22 踩过）：部署分支和 master 之间往往存在历史分歧（有的改动只合了部署分支
没合回 master，或者反过来），分歧可能积累到上千个提交。功能分支一旦从部署分支切出，就会带着
这整条分歧历史作为基线。等到需要把这个功能分支合并到**另一个**部署分支（比如项目换了新的部署
分支 `sit-260921`，它是从 master 切的）时，git 会把两条部署分支间的历史分歧全部摆出来比对，
产生大量与本次改动无关的冲突，需要按下面「冲突不在本次改动范围内时，改走 cherry-pick」那一节
去处理，比直接 merge 麻烦得多。

切分支前判断基线：

```bash
git log --oneline origin/master..origin/sit | wc -l   # sit 领先 master 多少
git log --oneline origin/sit..origin/master | wc -l   # master 领先 sit 多少（sit 是否漏合）
```

两边差距很大时，默认还是从 `master` 切；只有确认部署分支和 master 基本同步、或者用户明确要求
"就基于当前 sit 上的代码改"时，才从部署分支切，并且要在切分支时向用户说明这个选择。

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

**适用范围只限 GitLab。** GitHub 上是用户自己的个人仓库（例如 `cajohan/kiro-config`，即 `~/.kiro`），
不受这条限制，可以直接 `git push origin main`，见 `config-sync.md`。判断依据是 `git remote -v` 里的主机名：
公司 GitLab（主机名见 `internal-project-notes.md`）走 MR，`github.com` 的个人仓库直接推。拿不准是不是用户自己的仓库时先问。

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

有的项目 pro pipeline 只构建镜像不发布，还要去部署平台手动发布并验证线上内容，
具体项目和步骤见 `internal-project-notes.md`。"发生产"要做到线上验证通过才算完。

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
- `git status` 的文件数明显超出需求范围时，**先停下自查**是不是夹带了临时改动/环境绕路
  （见 `local-dev-server.md`），而不是继续往上堆。
- 每次提交前跑一遍构建；提交后 `git status --short` 确认工作区干净。
