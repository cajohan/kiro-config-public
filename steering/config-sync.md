# 全局规则变更后同步到 GitHub

`~/.kiro` 是一个 git 仓库，远端 `origin` 是 `https://github.com/cajohan/kiro-config.git`（分支 `main`）。
`.gitignore` 是白名单模式（`steering/internal-*.md` 例外排除，只留本地），只放行配置类文件：`steering/`、`skills/`、`agents/`、`hooks/`、`scripts/`、
`powers/installed.json`、`settings/{cli,mcp}.json`、`settings/permissions.yaml`。会话、日志、缓存、
`secrets.json` 都不会进仓库。

## 什么时候要同步

**每次全局规则发生变更之后，当轮就提交并推到 GitHub**，不要攒着。"全局规则"指上面白名单里的任何文件，
典型是：

- 新增 / 修改 / 删除 `~/.kiro/steering/*.md`
- 修改 `~/.kiro/settings/permissions.yaml`、`mcp.json`、`cli.json`
- 修改 `skills/`、`agents/`、`hooks/`、`scripts/` 下的文件

顺序是：**先把规则改完 → 再同步**，同步放在回复结尾之前，不要等用户来催。

## 怎么同步

```bash
cd ~/.kiro
git status --short                      # 先看清楚有哪些改动
git diff -- <文件>                       # 推之前看一遍内容，确认没有密钥 / token
git add <具体文件>                       # 按文件名添加，不要 git add .
git commit -m "<类型>: <改了什么规则>"    # 例如 docs: 新增 master 只能走 MR 的约定
git push origin main
git status -sb | head -1                # 确认没有 [ahead N]
```

要点：

- **推之前必须看 diff**。这是公开可能被看到的仓库，`mcp.json`、`permissions.yaml` 里不能带 token、
  密码、内网凭据。发现疑似密钥就停下，先问用户，不要推。
- 提交信息写清楚改了哪条规则，不要写成 "update"。
- 只提交**与本次规则变更相关**的文件。工作区里如果夹着其他会话留下的、与本次无关的改动，
  先告诉用户有哪些，由用户决定要不要一起提交，不要顺手全推。
- 这个仓库的 `main` 是个人配置仓库，不走 MR，直接 `git push origin main`。
  GitHub 是用户自己的个人仓库，不受「master/main 不能直推」限制；该限制只针对 GitLab
  上的业务仓库，见 `git-workflow.md`，两者不要混淆。

## 失败时

- `push` 被拒（远端比本地新）：先 `git pull --rebase origin main`，有冲突就停下来问用户，不要强推。
- 没有网络 / 认证失败：属于权限类问题，告诉用户，由用户处理，不要重试多次。
- 不要 `git push --force`，不要 `git reset --hard` 丢掉未提交的规则改动。
- `git push` 直接报 `Killed: 9`、没有任何 git 输出：不是 Kiro 权限规则，也不是网络/认证问题，
  见 `internal-project-notes.md`「本机安全软件」。**不要想办法绕过**，本地照常提交，告诉用户还没推上去。
