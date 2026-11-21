#!/bin/bash
# 生成给外部仓库（GitHub）用的脱敏快照分支 `public`：
#   1. 取 main 当前的文件树；
#   2. 去掉 steering/internal-*.md、本机专用的软链接 skills/ego-browser、整个 dotfiles/（含凭据不进公网）；
#   3. 把正文里的内部域名/账号替换成占位符；
#   4. 再扫一遍公司特征词，扫到任何一个就拒绝生成（宁可失败，也不外泄）。
# 历史：public 只有一串「快照提交」，不带 main 的历史（main 历史里含公司内部文件，不能带出去）。
# 用法：bash ~/.kiro/scripts/publish-public.sh
# 只生成/更新本地 public 分支，不推送。推送命令在最后打印，到能访问 GitHub 的机器上执行。

set -e
cd "$(dirname "$0")/.."

src=$(git rev-parse --verify -q main) || { echo "找不到 main 分支" >&2; exit 1; }
tmp=$(mktemp -d -t kiro-public)
idx=$(mktemp -t kiro-public-index)
# 只要一个唯一路径。空文件不是合法索引，所以先删掉，让 git 自己创建
rm -f "$idx"
trap 'rm -rf "$tmp" "$idx"' EXIT

git archive "$src" | tar -x -C "$tmp"

# 2. 整个文件排除
rm -f "$tmp"/steering/internal-*.md
rm -f "$tmp/skills/ego-browser"
rm -rf "$tmp"/dotfiles

# 3. 内部域名/账号 -> 占位符（只处理文本文件）
find "$tmp" -type f \( -name '*.md' -o -name '*.json' -o -name '*.yaml' -o -name '*.sh' -o -name '*.py' -o -name '.gitignore' \) -print0 |
  xargs -0 perl -Mutf8 -CSD -pi -e '
    s{ssh://git\@[\w.-]*yxzq\.com:\d+/[\w.-]+/[\w.-]+\.git}{<内部 GitLab 仓库地址>}g;
    s{https?://[\w.-]*yxzq\.com[^\s`)）」"\x27]*}{<内部地址>}g;
    s{[\w-]+\.yxzq\.com}{<内部域名>}g;
    s{john\.chen}{<你的账号>}g;
  '

# 4. 自检：脚本自己不参与扫描（它里面要写这些词）
markers='yxzq|john\.chen|usmart|finsmart|chenjunhuang|10\.(60|210)\.'
hits=$(grep -rIEn "$markers" "$tmp" --exclude=publish-public.sh || true)
links=$(find "$tmp" -type l -exec readlink {} \; | grep -E "$markers" || true)
if [ -n "$hits$links" ]; then
  echo "✗ 拒绝生成 public：脱敏后仍发现公司特征词，请先改掉这些内容（或扩充上面的替换规则）：" >&2
  echo "$hits" | sed "s#$tmp/##" | cut -c1-170 | head -20 >&2
  [ -n "$links" ] && echo "软链接目标：$links" >&2
  exit 1
fi

export GIT_INDEX_FILE="$idx"
GIT_WORK_TREE="$tmp" git add -A
tree=$(git write-tree)

parent=$(git rev-parse --verify -q refs/heads/public || true)
if [ -n "$parent" ] && [ "$(git rev-parse "$parent^{tree}")" = "$tree" ]; then
  echo "public 已是最新（没有需要同步的变化）：$(git rev-parse --short "$parent")"
  exit 0
fi

msg="sync: 脱敏快照 (main@$(git rev-parse --short "$src"))"
new=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "$msg")
git update-ref refs/heads/public "$new"

# 二次自检：快照里不能有 internal 文件，历史里也不能出现过
if git ls-tree -r --name-only public | grep -q '^steering/internal-'; then
  echo "✗ 自检失败：public 里仍有 internal 文件" >&2; exit 1
fi
if [ -n "$(git log --format=%h public -- 'steering/internal-*.md')" ]; then
  echo "✗ 自检失败：public 历史里出现过 internal 文件" >&2; exit 1
fi

echo "✓ public 已更新到 $(git rev-parse --short public)（$(git rev-list --count public) 个快照提交，已脱敏并通过公司特征词扫描）"
echo "在能访问 GitHub 的机器上推送（只推 public，不要推 main）："
echo "  公司电脑上不要推 GitHub；在能访问 GitHub 的机器上用 scripts/publish-to-github.sh（见 README.md）"
