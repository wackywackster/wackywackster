#!/usr/bin/env python3
"""Solenoid Water Fountain Simulator — terminal animation driven by a JSON sequence file."""

import curses
import json
import sys
import time

NUM_SOLENOIDS = 12
COL_W = 6  # terminal columns per solenoid slot


def load(path: str) -> dict:
    with open(path) as f:
        raw = json.load(f)
    # Accept three formats:
    #   [1,0,...,1]              -> single frame
    #   [[1,0,...],[0,1,...]]    -> bare sequence
    #   {"fps":4,"loop":true,"frames":[[...],...]}
    if isinstance(raw, list):
        if raw and not isinstance(raw[0], list):
            raw = [raw]  # single frame -> wrap in list
        return {"fps": 2, "loop": True, "frames": raw}
    return raw


def normalize(frames: list) -> list:
    out = []
    for frame in frames:
        row = (list(frame) + [0] * NUM_SOLENOIDS)[:NUM_SOLENOIDS]
        out.append([int(bool(v)) for v in row])
    return out


def init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)    # water body
    curses.init_pair(2, curses.COLOR_BLUE, -1)    # basin
    curses.init_pair(3, curses.COLOR_GREEN, -1)   # open solenoid label
    curses.init_pair(4, curses.COLOR_RED, -1)     # closed solenoid label
    curses.init_pair(5, curses.COLOR_WHITE, -1)   # UI text
    curses.init_pair(6, curses.COLOR_YELLOW, -1)  # spray / droplets


def simulate(stdscr, data: dict) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()

    frames = normalize(data.get("frames", [[0] * NUM_SOLENOIDS]))
    fps = max(0.1, float(data.get("fps", 2)))
    loop = bool(data.get("loop", True))
    total = len(frames)

    water = [0.0] * NUM_SOLENOIDS   # current jet height in rows (float for smooth animation)
    frame_idx = 0
    next_frame = time.monotonic() + 1.0 / fps
    last = time.monotonic()

    while True:
        now = time.monotonic()
        dt = min(now - last, 0.1)   # cap dt so a pause doesn't cause a jump
        last = now

        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q'), 27):
            break

        # Advance to next sequence frame on schedule
        if now >= next_frame:
            if loop:
                frame_idx = (frame_idx + 1) % total
            elif frame_idx < total - 1:
                frame_idx += 1
            next_frame = now + 1.0 / fps

        states = frames[frame_idx]
        h, w = stdscr.getmaxyx()
        basin_row = h - 4
        max_jet = max(1, basin_row - 3)

        # Animate water heights toward target (open=full, closed=0)
        for i in range(NUM_SOLENOIDS):
            target = float(max_jet) if states[i] else 0.0
            if water[i] < target:
                water[i] = min(target, water[i] + max_jet * 4.0 * dt)
            else:
                water[i] = max(target, water[i] - max_jet * 2.5 * dt)

        _draw(stdscr, states, frame_idx, total, fps, water, h, w, basin_row, max_jet)
        time.sleep(0.016)  # render at ~60 fps


def _draw(stdscr, states, fidx, total, fps, water, h, w, basin_row, max_jet) -> None:
    ox = max(0, (w - NUM_SOLENOIDS * COL_W) // 2)  # horizontal offset to centre

    stdscr.erase()

    C = curses.color_pair if curses.has_colors() else lambda _: 0

    def put(row, col, text, attr=0):
        if 0 <= row < h and 0 <= col < w:
            try:
                stdscr.addstr(row, col, text[: w - col], attr)
            except curses.error:
                pass

    def putch(row, col, ch, attr=0):
        if 0 <= row < h and 0 <= col < w - 1:
            try:
                stdscr.addch(row, col, ch, attr)
            except curses.error:
                pass

    # ── Header ──────────────────────────────────────────────────────────────
    title = "SOLENOID FOUNTAIN SIMULATOR"
    put(0, (w - len(title)) // 2, title, C(5) | curses.A_BOLD)
    info = f"Frame {fidx + 1}/{total}  |  {fps:.1f} fps  |  [Q] quit"
    put(1, (w - len(info)) // 2, info, C(5))

    # ── Water jets ──────────────────────────────────────────────────────────
    for i in range(NUM_SOLENOIDS):
        cx = ox + i * COL_W + 2   # centre column of this jet
        jh = int(water[i])
        full_ratio = water[i] / max_jet if max_jet else 0.0

        for j in range(jh):
            row = basin_row - 1 - j
            if row <= 1:
                break
            frac = j / max(jh, 1)
            if frac >= 0.85:
                # Near the top: show spread
                putch(row, cx - 1, "(", C(6))
                putch(row, cx,     "|", C(1) | curses.A_BOLD)
                putch(row, cx + 1, ")", C(6))
            else:
                attr = C(1) | (curses.A_BOLD if frac > 0.4 else 0)
                putch(row, cx, "|", attr)

        # Droplet at peak
        if jh > 0:
            top_row = basin_row - 1 - jh
            if top_row >= 2:
                putch(top_row, cx, "o", C(6) | curses.A_BOLD)
            if top_row - 1 >= 2 and full_ratio > 0.93:
                putch(top_row - 1, cx, ".", C(1))

    # ── Basin (water surface) ────────────────────────────────────────────────
    put(basin_row, ox, "~" * (NUM_SOLENOIDS * COL_W), C(2) | curses.A_BOLD)

    # ── Solenoid labels ──────────────────────────────────────────────────────
    sol_row = basin_row + 1
    if sol_row < h - 1:
        for i in range(NUM_SOLENOIDS):
            x = ox + i * COL_W
            if states[i]:
                put(sol_row, x, f"[{i + 1:02d}O]", C(3) | curses.A_BOLD)
            else:
                put(sol_row, x, f"[{i + 1:02d}X]", C(4))

    # ── Status bar ───────────────────────────────────────────────────────────
    open_n = sum(states)
    status = f"Open: {open_n:2d}/12   Closed: {12 - open_n:2d}/12"
    put(h - 1, (w - len(status)) // 2, status, C(5))

    stdscr.refresh()


def usage() -> None:
    print("Usage:  python fountain.py <sequence.json>")
    print()
    print("JSON formats:")
    print("  Single frame  : [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]")
    print("  Bare sequence : [[1,0,...], [0,1,...], ...]")
    print("  Full format   : {\"fps\": 4, \"loop\": true, \"frames\": [[1,0,...], ...]}")
    print()
    print("Each frame is a list of 12 values (0=closed, 1=open).")
    print("Extra values are ignored; missing values default to 0.")


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    try:
        data = load(sys.argv[1])
    except FileNotFoundError:
        sys.exit(f"Error: file not found — {sys.argv[1]}")
    except json.JSONDecodeError as exc:
        sys.exit(f"Error: invalid JSON — {exc}")

    data["frames"] = normalize(data.get("frames", [[0] * NUM_SOLENOIDS]))
    if not data["frames"]:
        sys.exit("Error: sequence contains no frames")

    curses.wrapper(simulate, data)


if __name__ == "__main__":
    main()
