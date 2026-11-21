# Kiro 全局配置仓库

`~/.kiro` 的版本记录：规则（steering）、技能（skills）、agent、hooks、脚本和少量设置。
用来留痕、回滚，并在多台 Mac 之间同步。

**各条规则背后的踩坑要点和出处速览见 [OVERVIEW.md](OVERVIEW.md)。**

## 里面有什么

`.gitignore` 是**白名单**：默认全部忽略，只放行下面这些。会话、日志、扩展、`secrets.json` 等永远不进仓库。

| 路径 | 内容 |
|---|---|
| `steering/` | 全局规则。`internal-*.md` 是公司内部信息，**不会**进公开快照 |
| `skills/` | 技能（`skills/ego-browser` 是指向本机安装目录的软链接，机器专属） |
| `agents/`、`hooks/` | agent 配置、hooks |
| `scripts/` | 辅助脚本（见下） |
| `settings/` | 只放行 `cli.json`、`mcp.json`、`permissions.yaml` |
| `powers/installed.json` | 只要安装清单 |
| `dotfiles/` | 机器 dotfile（如 maven-settings.xml，含凭据，**不进公开快照**） |

脚本：

| 脚本 | 作用 |
|---|---|
| `scripts/weekly-snapshot.sh` | 每周日 21:00（launchd）把已跟踪文件里没人提交的改动提交并推送 |
| `scripts/publish-public.sh` | 生成脱敏快照分支 `public`（只在本地生成，不推送） |
| `scripts/publish-to-github.sh` | 克隆后一条命令：生成脱敏快照并只把 `public` 推到 GitHub |
| `scripts/strip-session-images.py` | 清理旧会话里的图片 |
| `scripts/check-ego-subagent.sh` | 检查 ego 子 agent 是否可用 |

## 两个远端，内容范围不同

| 远端 | 是什么 | 推什么 |
|---|---|---|
| `origin` | 公司内部 GitLab 的个人项目 | **全部**（含内部规则），推 `main` |
| GitHub 公开仓库 | 对外展示 | **只推 `public` 分支**（脱敏快照），**绝不推 `main`** |

**公司电脑上的 `~/.kiro` 只配 `origin`，不要挂 GitHub 远端。** 没有这个远端就不可能误推；
需要发 GitHub 时用下面的一条命令，在一个临时克隆里完成。

## 日常同步（`origin`）

改完规则，当轮就提交并推送，不要攒着：

```bash
cd ~/.kiro
git status --short
git add <具体文件>            # 按文件名添加，不要 git add .
git commit -m "<类型>: <改了什么规则>"
git push
```

- 个人配置仓库，直接推 `main`，不走 MR。
- 另一台 Mac 拉最新：`git -C ~/.kiro pull --ff-only`。
- `settings/cli.json` 里的 `chat.modelPicker.lastUsed` 每次换模型都会变，是本机运行状态，**不要为它单独提交**，交给周快照。
- 不要 `git reset --hard` 丢掉未提交的改动，不要 force push。

## 发布脱敏快照到 GitHub

在**能访问 GitHub 的机器**上（公司电脑会被安全软件拦截，不要在公司电脑上试），粘贴一条命令：

```bash
git clone "$KIRO_REPO_URL" /tmp/kiro-config && bash /tmp/kiro-config/scripts/publish-to-github.sh
```

`KIRO_REPO_URL` 是 `origin` 的地址，记在内部笔记里。

它会：

1. 添加 GitHub 远端；
2. 调用 `publish-public.sh` 生成 `public`：去掉 `steering/internal-*.md`、`dotfiles/` 和本机专用软链接，
   把内部域名、账号替换成占位符，再扫一遍公司特征词，**扫到任何一个就拒绝生成**；
3. 再独立检查一遍 `public` 里没有 internal 文件；
4. **只推 `public`**，不推 `main`，不加 `--force`，远端 `public` 有你这里没有的提交时会被拒绝，不会覆盖。

推完删掉临时克隆：`rm -rf /tmp/kiro-config`。

想先看生成结果、不推送：在 `~/.kiro` 里 `bash scripts/publish-public.sh`，它只更新本地 `public` 分支。

GitHub 地址默认写在 `publish-to-github.sh` 里，换仓库时用环境变量 `GITHUB_URL=... bash scripts/publish-to-github.sh`。

## 安全原则

- 内部信息（`steering/internal-*.md`、内网地址、账号）只能在公司 GitLab 里，**不能**出现在 GitHub。
- 防线有三层：公司电脑上不挂 GitHub 远端；`publish-public.sh` 生成快照时扫描特征词、扫到就拒绝；
  `publish-to-github.sh` 推送前再检查一次，并且只推 `public`。
- 不要为了推送成功去换协议、改写内容、绕过安全软件。推送被拦截就停下来，找 IT。

## 排障

- **`git push` 被系统直接杀掉（退出码 137，没有任何输出）**：2026-11-16 在这个仓库遇到过。
  原因是仓库配置了 `core.hooksPath` 指向一个 `pre-push` 钩子脚本，安全软件拦截执行它，
  取消这项配置就恢复正常（对照实验翻转 2 次稳定复现）。该钩子已经删除，用「公司电脑不挂 GitHub 远端」取代。
  如果以后又遇到 137，先 `git config --get core.hookspath` 看有没有人重新设了钩子路径。
- **推送被拒绝（non-fast-forward）**：说明远端有别的窗口或别的 Mac 推过。先 `git fetch origin`，
  确认两边改的文件没有重叠，再 `git rebase origin/main`，然后推送。
- **`git status` 总显示 `settings/cli.json` 已修改**：正常，是上面说的运行状态，周快照会处理。
- **`public` 生成失败说扫到了公司特征词**：按提示改掉内容，或者扩充 `publish-public.sh` 里的替换规则。
