#!/usr/bin/env python3
"""把 kiro-cli 历史会话（~/.kiro/sessions/cli/*.jsonl）里内嵌的图片块替换成一句文字说明，只保留文字。

- 图片在会话里以 {"kind":"bytes","data":[...整数数组...]} 存储，一张截图就是几十万个数字，
  会话体积 90% 以上是它。换成同结构的文字块后 --resume 仍能正常加载。
  （不要换成 1x1 占位 PNG：resume 时模型 API 会报 Could not process image。）
- 只处理最后修改超过 --min-age-hours 的会话，并跳过当前会话（$KIRO_SESSION_ID），避免和正在写的会话打架。
- 写入用临时文件 + rename，中途失败不会留下半截文件。
- 默认静默（作为 agentSpawn hook 时 stdout 会进上下文）；--verbose 打印统计。
"""
import argparse
import json
import os
import sys
import time

SESSIONS = os.path.expanduser("~/.kiro/sessions/cli")
STATE = os.path.join(SESSIONS, ".strip-images-state.json")
TEXT = "[图片已移除，仅保留文字]"


def strip(o):
    """原地把图片块换成文字块，返回替换的张数。

    会话里图片有两种写法，都出现在列表元素里：
      {"kind": "image", "data": {"format": ..., "source": {"kind": "bytes", ...}}}  -> {"kind": "text", "data": TEXT}
      {"Image": {"format": ..., "source": {...}}}                                -> {"Text": TEXT}
    """
    n = 0
    if isinstance(o, dict):
        for v in o.values():
            n += strip(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, dict) and v.get("kind") == "image":
                o[i] = {"kind": "text", "data": TEXT}
                n += 1
            elif isinstance(v, dict) and set(v) == {"Image"}:
                o[i] = {"Text": TEXT}
                n += 1
            elif isinstance(v, (dict, list)) and not (isinstance(v, list) and v and isinstance(v[0], int)):
                n += strip(v)
    return n


def process(path):
    out_lines, total = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '"bytes"' not in line:
                out_lines.append(line)
                continue
            obj = json.loads(line)
            c = strip(obj)
            total += c
            out_lines.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n" if c else line)
    if total:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        st = os.stat(path)
        os.replace(tmp, path)
        os.utime(path, (st.st_atime, st.st_mtime))  # 保留原修改时间，会话列表的排序不变
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-age-hours", type=float, default=48)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(SESSIONS):
        return
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    current = os.environ.get("KIRO_SESSION_ID", "")
    now, imgs, saved, files = time.time(), 0, 0, 0
    for name in sorted(os.listdir(SESSIONS)):
        if not name.endswith(".jsonl") or (current and name.startswith(current)):
            continue
        p = os.path.join(SESSIONS, name)
        st = os.stat(p)
        if now - st.st_mtime < args.min_age_hours * 3600:
            continue
        if state.get(name) == [st.st_mtime, st.st_size]:
            continue  # 上次处理过且没变化
        try:
            c = process(p)
        except Exception as e:  # 单个文件坏了不影响其他文件
            print(f"skip {name}: {e}", file=sys.stderr)
            continue
        st2 = os.stat(p)
        state[name] = [st2.st_mtime, st2.st_size]
        if c:
            files, imgs, saved = files + 1, imgs + c, saved + st.st_size - st2.st_size
    tmp = STATE + ".tmp"
    json.dump(state, open(tmp, "w"))
    os.replace(tmp, STATE)
    if args.verbose:
        print(f"files={files} images={imgs} saved={saved / 1e6:.0f}MB")


if __name__ == "__main__":
    main()
