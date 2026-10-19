# 本地起服务与构建：版本、进程收尾

## 先按项目要求切 Node 版本，别拿当前版本硬试

老项目的构建链（node-sass、node-gyp 编译的原生模块）**对 Node 版本和 CPU 架构是硬依赖**。
在 Apple Silicon + 新 Node 上，`node-sass` 会直接报：

```
Error: Node Sass does not yet support your current environment:
OS X Unsupported architecture (arm64) with Unsupported runtime (93)
```

这不是代码问题，是环境问题。**先看 README / package.json engines 里写的版本，用 nvm 切过去**：

```bash
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"
nvm ls                      # 看本地装了哪些
nvm use 12                  # 按项目要求切（各项目版本见 internal-project-notes.md）
node -e "require('./node_modules/node-sass')"   # 验一下原生模块能加载
```

`nvm use` 只在当前 shell 生效，所以**每个 shell 调用都要重新 source + use**，
不能指望上一条命令切过了这一条还在。

### 不要为了绕开环境问题去改业务代码

踩过的具体错误：node-sass 跑不起来，就装 dart-sass 顶上，结果 dart-sass 不认
`/deep/`（旧的 deep 选择器语法），于是把全仓 135 个文件的 `/deep/` 批量替换成
`::v-deep` —— 一个改 9 个文件的需求，`git status` 直接变成 180 个文件，用户当场警觉。

判断规则：

- 构建失败时先分辨**是环境问题还是代码问题**。报错里出现架构/运行时/原生模块字样的，一律先切版本。
- 环境问题只在环境层面解决（换 Node、重装依赖、换 shell），**不要动仓库里的文件**。
- 确实需要临时改仓库文件才能验证时：只改与本次需求相关的文件；
  真要大范围改，先跟用户说清楚「这是临时的、验证完会还原」，并且**验证完立刻 `git checkout --` 还原**，
  不要留到最后一起处理（中间被打断就还原不了了）。
- 顺手检查有没有误伤 `yarn.lock` / `package-lock.json`（`npm i` 会重写它们），有就还原。

## 起 dev server 不要用 nohup

`nohup npm run serve &` 起的进程**脱离终端、不随 Kiro 会话结束而退出**。
反复试几次就攒出一堆孤儿进程，端口被占后服务会自动往后挪（3000 → 3001 → 3002 …），
既误导排查（"3004 是谁起的？"）又占内存。

正确做法，二选一：

1. **让用户自己跑**：前端项目用户本地通常已经挂着 dev server，直接问端口，
   自己只负责连上去看结果（配合 ego-browser）。这是首选。
2. **自己跑就自己收尾**：在**同一轮对话里**起、验、杀，不要跨轮留着。
   起之前记下 PID，验完立刻按 PID / 精确命令特征收掉：

```bash
# 起（记 PID）
CLIENT_ENV=localhost npm run serve hk > /tmp/serve.log 2>&1 &
echo $!

# 等编译完再访问，不要盲等固定秒数
for i in $(seq 1 40); do sleep 5; \
  [ "$(curl -s -o /dev/null -w %{http_code} http://localhost:3000/xxx)" = "200" ] && break; done

# 收尾：按项目路径精确匹配，别用 pkill node
pkill -f "<项目名>/server/index"
lsof -nP -iTCP -sTCP:LISTEN | grep -E ":30[0-9][0-9]"   # 确认端口释放
```

### 收尾时绝对不要 `pkill node` / `killall node`

用户机器上的 node 进程一大半是 **Kiro 和 VS Code 自己的 helper**
（eslint server、copilot、json/markdown language server、`node.mojom.NodeService`），
全杀会打断用户的编辑器和当前这个会话。

即使用户说"把全部 node 关了"，也要：

1. 先 `ps -eo pid,etime,command | grep "[n]ode"` 列出来给用户看，标明哪些是自己起的（看 etime）；
2. 只杀**项目服务进程**（按项目路径 / `server/index` / `build/start` 这类特征精确匹配）；
3. 明确说明「IDE 的 helper 进程故意保留，杀了会打断你的编辑器」，不要默默全杀。

## 顺带

- 起服务前先确认端口没被别人占；`lsof -nP -iTCP -sTCP:LISTEN | grep :3000` 一眼就能看出
  在跑的是用户的还是自己的（结合 `ps` 的 etime）。
- 后台任务的日志重定向到 `/tmp`，不要写进仓库目录，免得污染 `git status`。
