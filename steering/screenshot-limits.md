# 截图尺寸限制

## 单边不能超过 2000px

图片进上下文时，**任一边超过 2000 像素**会被 API 拒绝，报错：

```
messages.N.content.1.image.source.base64.data: At least one of the image dimensions
exceed max allowed size for many-image requests: 2000 pixels
```

一旦报错，这张图会卡在会话历史里，**后续每一轮请求都会重复失败**，只能清掉文件并重新开一轮。
所以要在截图那一刻就控制住尺寸，不要等报错。

## 截图时怎么控制

ego-browser 的 `page.screenshot()` 默认按视口尺寸出图，Retina 屏 DPR=2 时实际像素会翻倍
（1920 视口 → 3840px 宽），**很容易直接超限**。

- **不要用 `fullPage: true`**：长页面高度轻易上万像素，必超。
- 用 `clip` 只截需要的区域：

```js
await page.screenshot({
    path: '/tmp/x.png',
    clip: { x: 0, y: 0, width: 1400, height: 900 }
})
```

- 需要整页信息时，优先 `page.evaluate(() => document.body.innerText)` 取文字，
  不要截图；文字够用就不要图。
- 截完先验一下尺寸，超了就缩小再读：

```bash
# macOS 自带 sips
sips -g pixelWidth -g pixelHeight /tmp/x.png
sips -Z 1600 /tmp/x.png          # 长边缩到 1600
```

## Figma / 设计稿类工具

`get_screenshot` 有 `maxDimension` 参数（默认 1024），**不要为了看细节随手调到很大**，
需要看细节时分区域多次截，每次都保持长边 ≤ 1600。

## 用完就删

临时截图一律放 `/tmp`，同一轮里用完就 `rm`，不要在 `/tmp` 里堆积几十张图：
下次误读到旧图同样会触发超限，而且排查时容易看错图。

```bash
rm -f /tmp/xxx.png
```

## 历史会话只保留文字

图片会整张存进会话文件（CLI 存成字节数组，一个走查 UI 的会话能到 100M+；IDE 存成 base64），
用户决定（2026-10-19）：**历史会话只保留文字**，有价值的结论写进全局配置，截图不留。

- `~/.kiro/scripts/strip-session-images.py` 把 48 小时前会话里的图片换成一句
  「[图片已移除，仅保留文字]」，跳过当前会话；只处理有变化的文件，平时几十毫秒。
  - CLI：`sessions/cli/*.jsonl`，挂在 `agents/dev.json` 的 `agentSpawn` hook 上。
  - IDE：`sessions/<工作区>/sess_*/messages.jsonl`，挂在 `hooks/strip-session-images.json`（SessionStart）上。
- CLI 不要换成 1x1 占位图：resume 时模型 API 会报 `Could not process image`，必须换成文字块。
- IDE 的 `publish.cursor`（`<字节偏移>:<seq>`）记录 messages.jsonl 的读取位置，改写文件后必须按
  「旧偏移对应第几行」重算新偏移，seq 不变（seq 不等于行号）。改脚本时别丢掉这一步。
