#!/usr/bin/env python3
"""
HUD overlay for pipetting-video review.

• 3-well plate map (A1-A3) – top-right, white labels
• Well-state pop-ups – bottom-centre
• Event banner & thinking sidebar
• Tip counter – flashes bottom-right on every other TipChangeEvent
• **BIG WARNING PANEL** – fills ½ width × ½ height, centred, when WarningEvent active
"""

import cv2, json, numpy as np, matplotlib.colors as mcolors
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

# ─────────────────────────  CONFIG  ─────────────────────────────
PLATE_W, PLATE_H = 300, 110
PLATE_MARGIN = 20
TIP_FONT_SCALE = 1.2
TIP_PANEL_ALPHA = 0.75
POPUP_FONT_SCALE = 1.2
BANNER_MAIN_SCALE = 2.8
BANNER_DET_SCALE = 1.8

STATE_COLOURS = {
    "empty": "white",
    "partial": "yellow",
    "complete": "limegreen",
    "contaminated": "red",
}

EVENT_PRIORITY = {
    "warning": 4,
    "dispensing": 3,
    "aspiration": 3,
    "well_state": 2,
    "pipette_setting": 1,
    "tip_change": 0,
}


# ───────────────────────  PLATE MAP  ────────────────────────────
class PlateMap3:
    def __init__(self, goal):
        self.wells = [w["well_id"] for w in goal]
        self.goal = {w["well_id"]: {r["name"] for r in w["reagents"]} for w in goal}
        self.missing = {w: set(self.goal[w]) for w in self.wells}
        self.contaminated = {w: False for w in self.wells}
        self.contam_time = {}

    def record_contamination(self, reagent, t):
        self.contam_time.setdefault(reagent, t)

    def dispense(self, wid, reagent, t):
        if wid not in self.wells:
            return
        if reagent in self.contam_time and t >= self.contam_time[reagent]:
            self.contaminated[wid] = True
        self.missing[wid].discard(reagent)

    def state(self, wid):
        if self.contaminated[wid]:
            return "contaminated"
        if not self.missing[wid]:
            return "complete"
        if self.missing[wid] != self.goal[wid]:
            return "partial"
        return "empty"

    def draw(self, frame, x0, y0, w_inset=PLATE_W, h_inset=PLATE_H):
        cv2.rectangle(
            frame,
            (x0 - 1, y0 - 1),
            (x0 + w_inset + 1, y0 + h_inset + 1),
            (200, 200, 200),
            1,
        )
        n, spacing = len(self.wells), w_inset / len(self.wells)
        rad = int(min(spacing, h_inset) * 0.4)
        for i, wid in enumerate(self.wells):
            cx = int(x0 + spacing * (i + 0.5))
            cy = int(y0 + h_inset / 2)
            rgb = np.array(mcolors.to_rgb(STATE_COLOURS[self.state(wid)])) * 255
            cv2.circle(frame, (cx, cy), rad, tuple(map(int, rgb[::-1])), -1)
            cv2.putText(
                frame,
                wid,
                (cx - rad, cy + rad + 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )


# ───────────────────────  DRAW HELPERS  ─────────────────────────
def _clean(t):
    return t.replace("µ", "u").replace("μ", "u")


def _rect(f, p1, p2, c, a=0.7):
    o = f.copy()
    cv2.rectangle(o, p1, p2, c, -1)
    cv2.addWeighted(o, a, f, 1 - a, 0, f)


def banner_text(f, t, pos, s, col, k=2):
    t = _clean(t)
    (tw, th), bl = cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, s, k)
    x, y = pos
    x -= tw // 2
    y -= th // 2
    _rect(f, (x - 10, y - 10), (x + tw + 10, y + th + bl + 10), (0, 0, 0))
    cv2.putText(f, t, (x, y + th), cv2.FONT_HERSHEY_SIMPLEX, s, col, k, cv2.LINE_AA)


def info_box(f, t, x, y, w_max, s):
    t = _clean(t)
    font = cv2.FONT_HERSHEY_SIMPLEX
    words = t.split()
    lines = []
    cur = ""
    while words:
        w = words.pop(0)
        nxt = (cur + " " + w).strip()
        if cv2.getTextSize(nxt, font, s, 2)[0][0] <= w_max:
            cur = nxt
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
        lines = lines[:4]
    lh = int(30 * s)
    h_box = lh * len(lines) + 20
    _rect(f, (x - 10, y - 10), (x + w_max + 10, y + h_box + 10), (0, 0, 0), 0.85)
    for i, l in enumerate(lines):
        l_w = cv2.getTextSize(l, font, s, 2)[0][0]
        cv2.putText(
            f,
            l,
            (x + (w_max - l_w) // 2, y + lh * (i + 1)),
            font,
            s,
            (200, 200, 200),
            2,
            cv2.LINE_AA,
        )


# ───────────────────────  MAIN  ────────────────────────────────
def create_hud_video_opencv(input_video, timeline_json, output_video):
    data = json.load(open(timeline_json))
    evs = data["timeline"]
    plate = PlateMap3(data["procedure_context"]["goal_wells"])

    for e in evs:
        if e["event_model_type"] == "WarningEvent" and "Contaminated" in e.get(
            "description", ""
        ):
            reagent = " ".join(e["description"].split()[:2])
            plate.record_contamination(reagent, e["start_time"])

    disp = sorted(
        [e for e in evs if e["event_model_type"] == "DispensingEvent"],
        key=lambda e: e["start_time"],
    )
    di = 0
    tip_events = sorted(
        [e for e in evs if e["event_model_type"] == "TipChangeEvent"],
        key=lambda e: e["start_time"],
    )

    cap = cv2.VideoCapture(input_video)
    fps, W, H = (
        cap.get(cv2.CAP_PROP_FPS),
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*"avc1"), fps, (W, H))

    frame = 0
    while cap.isOpened():
        ok, img = cap.read()
        if not ok:
            break
        t = frame / fps

        # update plate state for dispenses
        while di < len(disp) and disp[di]["start_time"] <= t:
            d = disp[di]
            nxt = min(
                (
                    w
                    for w in evs
                    if w["event_model_type"] == "WellStateEvent"
                    and w["start_time"] >= d["start_time"]
                ),
                key=lambda w: w["start_time"],
                default=None,
            )
            if nxt:
                plate.dispense(
                    nxt["event_model"]["well_id"],
                    d["event_model"]["reagent"]["name"],
                    d["start_time"],
                )
            di += 1

        # HIGH-PRIORITY EVENT PICK
        active = [e for e in evs if e["start_time"] <= t <= e["end_time"] + 2]
        active.sort(key=lambda e: -EVENT_PRIORITY.get(e["event_type"], 0))
        top = active[0] if active else None

        # ───── BIG WARNING PANEL ─────
        if top and top["event_type"] == "warning":
            # ---------- HEADER ----------
            header_scale = 4.4  # 3.5 × 1.25  →  +25 %
            header_y = H // 2 - 70
            banner_text(
                img,
                "WARNING",
                (W // 2, header_y),
                header_scale,
                (0, 0, 255),  # red text
                6,  # thicker outline
            )

            # ---------- DESCRIPTION ----------
            desc_scale = 1.5  # 1.2 × 1.25
            max_width = int(W * 0.7)  # wrap width (70 % of frame)
            start_x = (W - max_width) // 2
            start_y = header_y + 80  # a bit below the header
            desc_txt = _clean(top["event_model"].get("description", ""))

            info_box(img, desc_txt, start_x, start_y, max_width, desc_scale)

        # ───── STANDARD BANNER FOR NON-WARNINGS ─────
        elif top:
            em, et = top["event_model"], top["event_model_type"]
            col = {
                "well_state": (0, 255, 0),
                "pipette_setting": (0, 255, 255),
                "aspiration": (255, 255, 0),
                "dispensing": (0, 165, 255),
                "tip_change": (255, 255, 255),
            }.get(top["event_type"], (255, 255, 255))
            if et == "AspirationEvent":
                main = f"ASPIRATING {em['reagent']['name'].replace('Reagent ', '')}"
                det = f"{em['reagent']['volume_ul']}uL"
            elif et == "DispensingEvent":
                main = f"DISPENSING {em['reagent']['name'].replace('Reagent ', '')}"
                det = f"{em['reagent']['volume_ul']}uL"
            elif et == "WellStateEvent":
                wid = em["well_id"]
                st = "COMPLETE" if em["is_complete"] else "PARTIAL"
                main = f"WELL {wid} {st}"
                det = "Contains: " + " + ".join(
                    r["name"].replace("Reagent ", "") for r in em["current_contents"]
                )
            elif et == "PipetteSettingChange":
                main = "PIPETTE SET"
                det = f"{em['new_setting_ul']}uL"
            else:
                main = top["title"]
                det = ""
            banner_text(img, main, (W // 2, int(0.08 * H)), BANNER_MAIN_SCALE, col, 3)
            if det:
                banner_text(
                    img,
                    det,
                    (W // 2, int(0.16 * H)),
                    BANNER_DET_SCALE,
                    (255, 255, 255),
                    2,
                )
            if "thinking" in em:
                info_box(img, em["thinking"], 30, 300, 400, 0.9)

        # WELL-STATE POPUP
        ws = next(
            (
                w
                for w in evs
                if w["event_model_type"] == "WellStateEvent"
                and w["start_time"] <= t <= w["end_time"]
            ),
            None,
        )
        if ws:
            em = ws["event_model"]
            wid = em["well_id"]
            cont = (
                ", ".join(
                    r["name"].replace("Reagent ", "") for r in em["current_contents"]
                )
                or "—"
            )
            miss = (
                ", ".join(
                    r["name"].replace("Reagent ", "") for r in em["missing_reagents"]
                )
                or "—"
            )
            banner_text(
                img,
                f"Well {wid} | Contains: {cont} | Missing: {miss}",
                (W // 2, int(0.92 * H)),
                POPUP_FONT_SCALE,
                (255, 255, 255),
                2,
            )

        # PLATE MAP
        if t >= 3:
            plate.draw(img, W - PLATE_W - PLATE_MARGIN, PLATE_MARGIN, PLATE_W, PLATE_H)

        # TIP COUNTER (every other tip-change)
        tip_idx_act = None
        for idx, tp in enumerate(tip_events):
            if tp["start_time"] <= t <= tp["end_time"] + 1:
                tip_idx_act = idx
                break
        if tip_idx_act is not None and tip_idx_act % 2 == 0:
            tips_used = tip_idx_act // 2 + 1
            txt = f"TIPS USED: {tips_used}"
            tw, th = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, TIP_FONT_SCALE, 2)[
                0
            ]
            rx1, ry1 = W - 20 - tw - 20, int(0.84 * H)
            rx2, ry2 = W - 20, ry1 + th + 20
            _rect(img, (rx1, ry1), (rx2, ry2), (0, 0, 0), TIP_PANEL_ALPHA)
            cv2.putText(
                img,
                txt,
                (rx1 + 10, ry1 + th + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                TIP_FONT_SCALE,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        out.write(img)
        frame += 1

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✓ HUD video written:", output_video)


# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    base = Path(__file__).parent.parent
    create_hud_video_opencv(
        str(base / "videos" / "output_long_again_2.mp4"),
        str(base / "video_processing" / "merged_timeline.json"),
        str(base / "video_processing" / "hud_with_plate_map.mp4"),
    )
