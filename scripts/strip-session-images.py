#!/usr/bin/env python3
"""把 Kiro 历史会话里内嵌的图片替换成一句文字说明，只保留文字。

- CLI：~/.kiro/sessions/cli/*.jsonl；IDE：~/.kiro/sessions/<工作区>/sess_*/messages.jsonl
  （IDE 的 publish.cursor 记录字节偏移，改写后同步重算，否则 IDE 读错位置）。

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

IDE_ROOT = os.path.expanduser("~/.kiro/sessions")


def strip_ide_line(obj):
    """IDE 会话：用户贴的图在 payload.images[]（data/dataUrl 为 base64），清空并在正文后加说明。"""
    pl = obj.get("payload") if isinstance(obj, dict) else None
    imgs = pl.get("images") if isinstance(pl, dict) else None
    if not imgs:
        return 0
    n = len(imgs)
    pl["images"] = []
    if isinstance(pl.get("content"), str):
        pl["content"] += "\n" + (TEXT if n == 1 else f"{TEXT} x{n}")
    return n


def process_ide(sess_dir):
    """改写 messages.jsonl，并同步修正 publish.cursor（格式 "<字节偏移>:<行数>"，偏移按新文件重算）。"""
    path = os.path.join(sess_dir, "messages.jsonl")
    cur_path = os.path.join(sess_dir, "publish.cursor")
    lines, total = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if '"images"' in line and len(line) > 5000:
                obj = json.loads(line)
                c = strip_ide_line(obj)
                if c:
                    total += c
                    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
            lines.append(line)
    if not total:
        return 0
    cursor = None
    if os.path.exists(cur_path):
        # offset 总落在行边界上，但 seq 不等于行号（有些行不计数），所以按「旧 offset 对应第几行」换算
        off, _, seq = open(cur_path).read().strip().partition(":")
        off, old_cum, k = int(off), 0, -1
        with open(path, "rb") as f:
            for k, raw in enumerate(f):
                if old_cum == off:
                    break
                old_cum += len(raw)
            else:
                k += 1
        if old_cum != off:
            raise RuntimeError(f"cursor offset {off} not on a line boundary")
        cursor = f"{sum(len(l.encode('utf-8')) for l in lines[:k])}:{seq}"
    st = os.stat(path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp, path)
    os.utime(path, (st.st_atime, st.st_mtime))
    if cursor is not None:
        cst = os.stat(cur_path)
        with open(cur_path + ".tmp", "w") as f:
            f.write(cursor)
        os.replace(cur_path + ".tmp", cur_path)
        os.utime(cur_path, (cst.st_atime, cst.st_mtime))
    return total


def ide_sessions():
    for ws in os.listdir(IDE_ROOT):
        wdir = os.path.join(IDE_ROOT, ws)
        if ws == "cli" or not os.path.isdir(wdir):
            continue
        for sd in os.listdir(wdir):
            p = os.path.join(wdir, sd)
            if sd.startswith("sess_") and os.path.isfile(os.path.join(p, "messages.jsonl")):
                yield p


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
    for sd in ide_sessions():
        p = os.path.join(sd, "messages.jsonl")
        key = "ide:" + os.path.relpath(sd, IDE_ROOT)
        st = os.stat(p)
        if now - st.st_mtime < args.min_age_hours * 3600 or state.get(key) == [st.st_mtime, st.st_size]:
            continue
        try:
            c = process_ide(sd)
        except Exception as e:
            print(f"skip {key}: {e}", file=sys.stderr)
            continue
        st2 = os.stat(p)
        state[key] = [st2.st_mtime, st2.st_size]
        if c:
            files, imgs, saved = files + 1, imgs + c, saved + st.st_size - st2.st_size
    tmp = STATE + ".tmp"
    json.dump(state, open(tmp, "w"))
    os.replace(tmp, STATE)
    if args.verbose:
        print(f"files={files} images={imgs} saved={saved / 1e6:.0f}MB")


if __name__ == "__main__":
    main()
