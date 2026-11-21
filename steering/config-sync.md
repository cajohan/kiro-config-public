---
inclusion: auto
trigger: model_decision
description: 修改 ~/.kiro 全局配置或规则后需要提交同步时使用；内部 GitLab 推全部，GitHub 只推 publish-public.sh 脱敏快照
---

# 全局规则变更后提交：内部 GitLab 推全部，GitHub 只推脱敏快照

`~/.kiro` 是一个 git 仓库，用来给全局配置留版本记录，并在多台 Mac 之间同步。完整说明（目录、脚本、一条命令发 GitHub、排障）见仓库根目录的 `README.md`，这里只写 agent 需要遵守的规则。

## 两个远端，内容范围不同

| 远端 | 是什么 | 推什么 |
|---|---|---|
| `origin` | 公司内部 GitLab 的个人项目（内部可见，同事能看；已关闭 CI/CD） | **全部**，包括 `steering/internal-*.md` 等公司内部信息，推 `main` |
| GitHub 公开仓库 | 对外展示 | **只能推 `public` 分支**（脱敏快照），绝不能推 `main` |

- **公司电脑上的 `~/.kiro` 只配 `origin`，不要挂 GitHub 远端**（`git remote -v` 里不应该出现 GitHub 地址）。没有这个远端就不可能误推，
  取代了原来的 pre-push 钩子（见下面「踩过的坑」）。
- 具体地址、另一台 Mac 的首次设置见 `internal-project-notes.md`（该文件属内部信息，不会进 GitHub）。
- 分支：`main`，upstream 是 `origin/main`。个人配置仓库，直接推，不走 MR（`git-workflow.md` 里「master/main 只能走 MR」只针对业务仓库）。

## 什么时候提交并推送

每次全局规则（白名单里的文件）变更后，当轮就提交并推送，不要攒着：

```bash
cd ~/.kiro
git status --short
git diff -- <文件>                       # 看一遍内容
git add <具体文件>                       # 按文件名添加，不要 git add .
git commit -m "<类型>: <改了什么规则>"
git push
```

- 提交信息写清楚改了哪条规则，不要写成 "update"。
- 工作区里有其他会话留下的、与本次无关的改动，先告诉用户，由用户决定要不要一起提交。
- `settings/cli.json` 里的 `chat.modelPicker.lastUsed` 每次换模型都会变，属于本机状态噪音，**不要为它单独提交**；
  它会长期显示为已修改，提交其他文件时不要顺手带上，交给周快照。
- 推送被拒（non-fast-forward）说明别的窗口或别的 Mac 推过：`git fetch origin`，确认两边改的文件没有重叠，再 `git rebase origin/main`
  （工作区有未提交改动时用 `git rebase --autostash origin/main`），然后推。
- 不要 `git reset --hard` 丢掉未提交的规则改动，不要 force push。
- 别用 `分支:main` 这种带冒号的 refspec 写法，会命中权限规则里「禁止推 main」。直接 `git push`。

## 周快照

`scripts/weekly-snapshot.sh`（launchd `com.john.kiro-config-snapshot`，每周日 21:00）把已跟踪文件里没人提交的改动
（Kiro 升级迁移、`chat.modelPicker.lastUsed` 这类运行状态）`git add -u` 提交一次并推送，排除机器专属的 `skills/ego-browser` 软链接。
失败只写 `/tmp/kiro-config-snapshot.log`。它**不替代**手动写规则后的及时提交。

## 白名单

`.gitignore` 是白名单模式，纳入：`README.md`、`steering/`（含 `internal-*.md`）、`skills/`、`agents/`、`hooks/`、`scripts/`、
`powers/installed.json`、`settings/{cli,mcp}.json`、`settings/permissions.yaml`。
`extensions/`、`sessions/`、`logs/` 等大目录（合计几个 G）和 `secrets.json` 不进仓库。

## 推 GitHub：只推脱敏快照

在**能访问 GitHub 的机器**上，一条命令（公司电脑会被安全软件拦截，**不要在公司电脑上试**，也不要想办法绕）：

```bash
git clone <origin 地址> /tmp/kiro-config && bash /tmp/kiro-config/scripts/publish-to-github.sh
```

`origin` 地址见 `internal-project-notes.md`。脚本会：加 GitHub 远端、调用 `publish-public.sh` 生成脱敏 `public`
（去掉 `steering/internal-*.md` 和机器专属软链接，把内部域名/账号替换成占位符，再扫一遍公司特征词，**扫到就拒绝生成**）、
再独立检查一遍 `public` 里没有 internal 文件、**只推 `public`**，不推 `main`，不强推。

所以往非 internal 的规则文件里写内部域名、账号、IP 是安全的（会被替换），但新增了脚本没覆盖到的写法时，
`publish-public.sh` 会报错，到时按提示改。想先看生成结果、不推送：`bash ~/.kiro/scripts/publish-public.sh`，只更新本地 `public` 分支。

## 在另一台 Mac 上同步

克隆命令和首次设置见 `internal-project-notes.md`。之后每次拉最新：`git -C ~/.kiro pull --ff-only`。

注意：`skills/ego-browser` 是指向本机 ego 安装目录的软链接，换机器后以那台 ego 安装时生成的为准；
规则里如果写死了本机的用户目录路径，用户名不同时要按实际改。

## 踩过的坑：`git push` 被系统直接杀掉（2026-11-16）

现象：在 `~/.kiro` 里 `git push`（连 `--dry-run` 也一样）退出码 137（SIGKILL），没有任何输出；用户自己新开终端也一样；
同一时间业务仓库推送正常，`fetch`、`ls-remote`、`ssh -T`、`commit` 也正常，读通、写被杀。

根因（对照实验）：仓库里设了 `core.hooksPath=scripts/git-hooks`（为了启用 pre-push 防护）。
同一个仓库、同一个命令，设着它 → 稳定 137，`git config --unset core.hooksPath` → 正常，再设回去 → 又 137，翻转两次稳定复现。
推测是安全软件在拦截执行 `scripts/git-hooks/pre-push` 这个脚本，但「为什么拦」没有证据，别当结论。
最后一次成功推送是 11-13 19:59，钩子文件 11-13 19:26 改过，所以更像是安全软件规则在周末更新了。

处理：删除钩子和 `core.hooksPath` 配置，同时把 GitHub 远端从 `~/.kiro` 里拿掉（防误推的保险改成「根本没有这个远端」），之后 `~/.kiro` 里直接推送恢复正常。

教训：
- **不要再给这个仓库设 `core.hooksPath`**；以后遇到 137 先 `git config --get core.hookspath` 看有没有人重新设过。
- `git -c core.hooksPath=/某个空目录 push` 不等于「没设」，我当时用它测过一次还是被杀，误判成「不是钩子」；要验证必须用 `git config --unset`。
- 排查这类「时好时坏」的问题，**一次只变一个变量，翻转两次再下结论**。当晚先后猜了目录、`-C`、远端、内容，都被后面的实验推翻。
- 绕开的办法（换目录推、中转克隆）能暂时解决，但没找到根因，不要当成方案固化下来。
