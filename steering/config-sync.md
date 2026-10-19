# 全局规则变更后本地提交（不推远端）

`~/.kiro` 是一个本地 git 仓库，只用来给全局配置留版本记录，**不推任何远端**。
（2026-10-19 起：公司安全策略管控往 GitHub 上传，用户决定不再同步，见 `internal-project-notes.md`。）

`.gitignore` 是白名单模式，只纳入配置类文件：`steering/`、`skills/`、`agents/`、`hooks/`、`scripts/`、
`powers/installed.json`、`settings/{cli,mcp}.json`、`settings/permissions.yaml`。
`extensions/`、`sessions/`、`logs/` 等大目录（合计几个 G）和 `secrets.json` 都不进仓库；
`steering/internal-*.md` 放公司内部信息，也排除在外。

## 什么时候提交

每次全局规则（上面白名单里的文件）变更后，当轮就本地提交，不要攒着：

```bash
cd ~/.kiro
git status --short
git diff -- <文件>                       # 看一遍内容
git add <具体文件>                       # 按文件名添加，不要 git add .
git commit -m "<类型>: <改了什么规则>"
```

要点：

- 提交信息写清楚改了哪条规则，不要写成 "update"。
- 工作区里有其他会话留下的、与本次无关的改动，先告诉用户，由用户决定要不要一起提交。
- **不要 `git push`，也不要重新添加 remote**。用户以后想同步到别处（如公司 GitLab 个人项目），由用户提出再改这条规则。
- 不要 `git reset --hard` 丢掉未提交的规则改动。
