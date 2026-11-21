---
inclusion: always
trigger: always_on
---

# effort（思考强度）按任务自己调

用户默认模型是 claude-sonnet-5.5，默认 effort 是 high（2026-11-13 起；此前是 opus-5.5 + medium）。**有必要时自己把 effort 往上调，不用请示**；但别为了保险一律拉高，
effort 越高越慢、越贵（2026-10-21 一次 sonnet-5 + max 的 review 跑了 2 小时、约 133 credits）。

## 能调的范围

- **子 agent / workflow**：`run_workflow` 的 `effortLevel` 由我决定，**每次都显式传**。
  不传会继承别的值：2026-10-21 起 review 时没传，reviewer 实际跑成了 `effort max`，一轮跑了一个多小时。
- **主会话**：effort 由用户在 IDE 里设置，我改不了。遇到明显需要更高 effort 的任务，
  就把难点拆成子任务、给子 agent 传更高的 `effortLevel`；确实需要主会话本身提高时，一句话告诉用户原因。

## 什么时候用哪档

| effort | 适用 |
|---|---|
| low | 机械操作：建工作树、跑命令收结果、读日志摘关键行、轮询 pipeline、清理临时文件 |
| medium（默认） | 普通改代码、样式走查、常规 code review、按明确步骤走的流程 |
| high | 根因不明的排查（时好时坏、多因素叠加）、异步时序 / 多模块联动的逻辑改动、构建/发布/签名链路的改动、改动面大或影响共用组件的 review、复审仍有分歧时 |
| max | 不用。真遇到 high 解决不了的，先拆小问题，不要直接拉到 max |

判断口径：**这一步出错的代价大、且靠多想能减少出错（而不是靠多跑几次命令）→ 提到 high**；
纯执行、结果靠工具验证的步骤，保持 low / medium。
