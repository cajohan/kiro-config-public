#!/bin/zsh
# 每次会话开始时检测 Kiro 版本是否变化，如果变了就提示主 agent 去重新测试 ego 子agent委派 bug 是否修复
# 相关背景：~/.kiro/steering/web-access.md 里记录的已知 bug，issue: https://github.com/kirodotdev/Kiro/issues/11333

STATE_FILE="$HOME/.kiro/.ego-subagent-check-state"
CURRENT_VERSION=$(kiro --version 2>/dev/null | head -1)

if [ -z "$CURRENT_VERSION" ]; then
  # kiro命令不可用，静默退出，不阻塞会话启动
  exit 0
fi

LAST_CHECKED_VERSION=""
if [ -f "$STATE_FILE" ]; then
  LAST_CHECKED_VERSION=$(cat "$STATE_FILE")
fi

if [ "$CURRENT_VERSION" != "$LAST_CHECKED_VERSION" ]; then
  # 版本变了，输出提示给主agent，并更新记录（先更新避免同一版本反复提示，即使这次忘了测）
  echo "$CURRENT_VERSION" > "$STATE_FILE"
  cat <<EOF
检测到 Kiro 版本从「${LAST_CHECKED_VERSION:-未记录}」变为「${CURRENT_VERSION}」。
请在本次会话中找个合适的时机，用 invoke_sub_agent 尝试 name="ego" 委派一次（可以是任意简单任务，比如让它回复一句话确认身份），验证 https://github.com/kirodotdev/Kiro/issues/11333 这个 bug 是否已修复。
- 如果仍报 "Agent 'ego' not found in registry"：bug还没修，不用特别提醒用户，正常继续手头任务即可。
- 如果调用成功：这是好消息，主动告诉用户"ego委派的bug好像修复了"，并更新 ~/.kiro/steering/web-access.md 里的说明（去掉bug警告，恢复"外包给ego省credits"的正常指引）。
EOF
fi
exit 0
