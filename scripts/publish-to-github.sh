#!/bin/bash
# 在「能访问 GitHub 的机器」上，把脱敏快照推到 GitHub 公开仓库的 public 分支。一条命令，克隆下来跑就行：
#
#   git clone <内部 GitLab 仓库地址> /tmp/kiro-config \
#     && bash /tmp/kiro-config/scripts/publish-to-github.sh
#
# 做了什么：
#   1. 添加 GitHub 远端 github-public（已存在就跳过）；
#   2. 调用 publish-public.sh 生成脱敏快照分支 public（去掉内部文件、替换内部域名、扫描公司特征词，扫到就拒绝）；
#   3. 再独立检查 public 里没有 internal 文件；
#   4. 只推 public。绝不推 main，不加 --force：远端 public 有你这里没有的提交时会被拒绝，不会覆盖。
#
# 公司电脑上这样推 GitHub 会被安全软件拦截（见 steering/config-sync.md），不要在公司电脑上用它去「试」。
# 环境变量（仅演练用）：GITHUB_URL 覆盖 GitHub 地址。

set -eu
cd "$(dirname "$0")/.."
GITHUB_URL="${GITHUB_URL:-https://github.com/cajohan/kiro-config-public.git}"

git remote get-url github-public >/dev/null 2>&1 || git remote add github-public "$GITHUB_URL"

bash scripts/publish-public.sh

# 保险：确认 public 里没有 internal 文件（publish-public.sh 已经检查过，这里再独立看一次）
if git ls-tree -r --name-only public | grep -q 'steering/internal-'; then
  echo "✗ 拒绝推送：public 里有 internal 文件" >&2; exit 1
fi

echo "--- 推送 public 到 GitHub（只推 public，不推 main，不强推）"
git push github-public public
echo "✓ 完成。可以删除克隆目录：rm -rf $(pwd)"
