#!/bin/bash
# 每周配置快照：把 ~/.kiro 里已被 git 跟踪、但没人手动提交的改动（Kiro 升级迁移、最近使用的模型等运行状态）
# 提交一次并推到公司 GitLab（origin）。
#
# 约束（见 steering/config-sync.md）：
#   - 只 `git add -u`，只处理已跟踪文件；.gitignore 是白名单，不会带上 sessions、logs、secrets.json
#   - 只推 origin（公司内部 GitLab）。公司电脑上的 ~/.kiro 不挂 GitHub 远端，不可能推到公网
#   - 没有改动就什么都不做；推送失败只记日志，下周再试
#   - skills/ego-browser 是机器专属软链接（指向本机 ego 安装路径），排除在外，不跟着一起提交，
#     否则会把「这台机器的路径」推成仓库基准值，別的机器下次 pull 就会被覆盖（2026-11-16 踩过）
# 由 ~/Library/LaunchAgents/com.john.kiro-config-snapshot.plist 每周日 21:00 触发。

set -u
cd "$HOME/.kiro" || exit 0
LOG=/tmp/kiro-config-snapshot.log
{
  echo "=== $(date '+%F %T') 开始"
  if [ -z "$(git status --porcelain --untracked-files=no -- . ':!skills/ego-browser')" ]; then
    echo "没有改动，跳过"
  else
    git status --short --untracked-files=no -- . ':!skills/ego-browser'
    git add -u -- . ':!skills/ego-browser'
    git commit -q -m "chore: 每周配置快照 $(date +%F)（Kiro 自动迁移/运行状态等未手动提交的改动）" && echo "已提交"
  fi
  # 本地领先 origin 的提交，一并推上去（包括别的窗口提交了但没推的）
  ahead=$(git rev-list --count origin/main..main 2>/dev/null || echo 0)
  if [ "${ahead:-0}" -gt 0 ]; then
    git push origin main 2>&1 && echo "已推送 $ahead 个提交" || echo "推送失败，下周再试"
  else
    echo "没有需要推送的提交"
  fi
  echo "=== 结束"
} >> "$LOG" 2>&1
exit 0
