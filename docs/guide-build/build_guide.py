"""Build the BPMap user guide PDF from the screenshots captured by capture.mjs.

Usage:  node docs/guide-build/capture.mjs   (needs the production build served on :4180)
        python3 docs/guide-build/build_guide.py      (needs Google Chrome; standard library only)

Each screenshot comes with the box of every control it points at (shots/meta.json). Arrows and
numbered markers are drawn here as SVG over the image, so they stay sharp and always land on the
control even when the UI moves. The numbers match the numbered steps beside each screenshot.
"""
import html
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
SHOTS = HERE / "shots"
HTML_OUT = HERE / "BPMap_User_Guide.html"
PDF_OUT = HERE.parent / "BPMap_User_Guide.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ACCENT = "#EA580C"  # arrows: orange is not used by the app's UI, so pointers never blend in

META = json.loads((SHOTS / "meta.json").read_text())

# --------------------------------------------------------------------------- content
# Each section: (title, intro, [panels]); each panel: (shot, [step texts in pointer order], note)
# A step is "Label|Text". Keep text short: one or two lines.
SECTIONS = [
    ("Import your Workday export",
     "BPMap reads the Excel file that Workday produces from View Definition. The file is read in your browser: nothing is uploaded.",
     [("01-start", [
         "Choose files|Click, or drop one or more .xlsx exports on the box. Drop a definition together with its subprocesses (up to 20 files).",
         "Try the sample|No export to hand? Load a synthetic Change Job and explore.",
         "Get the export|In Workday: open the business process definition, View Definition, then the Excel icon at the top. Save the .xlsx.",
         "Local only|Your files and edits stay in this browser. Nothing is sent anywhere.",
         "Theme|Light, dark or follow the system. Exports are always light.",
     ], None)]),
    ("The workspace at a glance",
     "Everything happens on one screen: the diagram in the middle, details on the right.",
     [("02-workspace", [
         "Definition tabs|One tab per imported definition. Add file imports more; × closes a tab.",
         "View|Executive, Process owner or Configurator: the same process at three levels of detail.",
         "Undo / redo|Undo any customisation: labels, notes, answers, positions.",
         "Focus a role|Highlight one security group and jump to its steps.",
         "Step list|Show the process as an accessible table instead of a diagram.",
         "Export|PDF, PowerPoint, draw.io, Excel, SVG, PNG and project files. Copy image and Open sit beside it.",
         "Panels|Step details, Scenario, Health checks and the Import report.",
         "Zoom bar|Arrange, zoom, fit height or fit width. Ctrl/⌘ + mouse wheel zooms; the wheel scrolls.",
         "Status bar|Size of the process and the save status (Saved in this browser).",
     ], None)]),
    ("Reading the diagram",
     "Lanes show who acts, columns show the order Workday runs the steps in, amber shows what is conditional.",
     [("03-reading", [
         "Lanes = who|Each row is a security group. Lane names stay pinned while you scroll sideways.",
         "Stage|Each column is an order stage (a, b, c…). Steps in the same column run in parallel.",
         "Conditional step|Dashed amber outline and a C-badge: the step runs only if its condition is true.",
         "Decision|A conditional approval gets a diamond: Yes runs the approval.",
         "Skip path|No, skip shows where the process continues when the condition is false.",
     ], None),
      ("04-legend", [
         "Legend|Explains every symbol. It is included in every export.",
         "Conditions|Every C-number in full: whether Workday or you own it, and which steps it guards.",
     ], "Legend and conditions stay pinned at the left while you scroll, when the window is wide enough.")]),
    ("Three views for three audiences",
     "Switch with the View control; each definition remembers its view and exports use it.",
     [("05-executive", [
         "Executive|One card per stage: a one-slide overview for leadership.",
         "Stage card|Who acts in the stage, and the conditions it depends on.",
     ], None),
      ("05-configurator", [
         "Configurator|For the people who build the process in Workday.",
         "Detail lines|Due date, alternate, routing, restrictions and notifications on every step.",
     ], "Process owner (the default) is the swimlane diagram with plain labels.")]),
    ("Step details and customising",
     "Click a step (or Tab to it and press Enter). Escape clears the selection.",
     [("06-step", [
         "Selected step|The selected step is outlined; your label replaces the Workday name in the diagram.",
         "Step tab|Opens automatically when you select a step.",
         "Details|Workday task, security group, due date, routing, restrictions and run-as.",
         "Runs only if|The conditions that guard this step.",
         "Label|Rename the step in the diagram. The Workday name stays in Details.",
         "Note|Add a note. The step shows an N badge; the full text goes into Excel exports.",
         "Hide|Remove the step from the diagram, e.g. a step that is switched off.",
     ], "Labels, notes and hidden steps survive when you re-import a newer export.")]),
    ("Scenarios: see the real path for one case",
     "Answer the conditions for one case (for example, a promotion in the Netherlands) and the diagram shows only the steps that run.",
     [("07-scenario", [
         "Active scenario|The status bar and the diagram header list your answers and how many steps are skipped.",
         "Answer|Yes, No or Not set. No removes the steps the condition guards; empty lanes collapse.",
         "Plain words|Rewrite a condition in business language. Shown everywhere, with the Workday text underneath.",
         "Decision|Draw this condition as a yes/no diamond on every step it guards.",
         "Save scenario|Name and save the answers to re-apply them later. Exports use the current scenario.",
         "Reset|Clear all answers.",
     ], None)]),
    ("Health checks",
     "BPMap checks the whole definition for common risks: self-approval, missing alternates or due dates, long serial chains, steps that can never run.",
     [("08-health", [
         "Health tab|The badge counts critical and warning findings.",
         "Finding|What is wrong, why it matters, and a suggested fix.",
         "Show step|Selects and centres the affected step.",
         "Dismiss|Dismiss with a reason. Dismissals survive re-import and can be restored.",
     ], None)]),
    ("Import report and re-importing",
     "Re-import a newer export of the same definition at any time: it replaces the tab and keeps your customisations.",
     [("09-import", [
         "Import tab|What was read: file, rows, steps, conditions, sheets and any warnings with row numbers.",
         "Kept edits|If the new export no longer has a step, your edits on it are listed here, not silently lost.",
         "Remove|Clear those edits once you have reviewed them (undo is available).",
         "Report|Import statistics for this definition.",
     ], None)]),
    ("Focus on one role",
     "Useful in workshops: show one team exactly where they act.",
     [("10-focus", [
         "Choose a role|Every other lane dims and the diagram scrolls to this role's first step.",
         "Previous / next|Step through the role's steps; each one opens in the Step panel.",
         "Role step|Steps of the chosen role stay at full strength.",
         "Other lanes|Dimmed, but still clickable.",
     ], None)]),
    ("Step list",
     "The same process as a table, in Workday order: for screen readers, keyboard users and quick scanning.",
     [("11-step-list", [
         "Step list|Toggle between the diagram and the table.",
         "Order|Stage number and Workday order letter.",
         "Open step|Click a step name to open its details.",
         "Runs only if|Conditions in words (your plain words when you set them).",
     ], None)]),
    ("Arrange the layout",
     "Fine-tune the automatic layout, for example to separate crossing lines before an export.",
     [("12-arrange", [
         "Arrange|Turn on, then drag a step, or select it and use the arrow keys (Shift = bigger moves).",
         "Moved step|Its lane or column grows to make room and the lines follow. A step never leaves its lane or stage.",
         "Reset layout|Put every step back in its automatic position (undo is available).",
     ], "Positions are kept when you re-import.")]),
    ("Subprocesses",
     "Import a definition together with the definitions it calls. Sub-process steps link to them automatically.",
     [("13-subprocess", [
         "Sub-process step|A step that runs another business process.",
         "Runs a subprocess|Shows which definition the step runs.",
         "Open|Opens that definition. If it isn't loaded, BPMap tells you to add its export.",
         "Subprocess tab|Linked definitions are marked ↳ in the tabs.",
     ], None),
      ("13-back", [
         "Back|Returns to the calling step.",
         "Subprocess|The subprocess opens in its own tab.",
     ], None),
      ("13-summary", [
         "Subprocesses|The Import tab lists what this definition calls (loaded or not) and what calls it.",
      ], None)]),
    ("Export and share",
     "Exports use the current view, scenario and customisations, always in the light theme.",
     [("14-export", [
         "PDF|Vector and sharp at any size: the diagram plus a readable conditions page.",
         "PowerPoint|Native shapes you can edit, plus a conditions slide.",
         "Excel|Steps, Conditions and Health sheets for the full definition, ready to filter.",
         "Packs|All open definitions in one file, with a cover listing contents and health.",
         "Project file|Everything (definitions, edits, scenarios) to continue in another browser or as a backup.",
         "Customisations only|Just your edits for one definition, to share with a colleague who has the same export.",
         "Open|Opens a project file or a customisations file.",
     ], "draw.io opens in diagrams.net (save as Visio from there); SVG and PNG are images for wikis and chat; Copy image puts a PNG on the clipboard.")]),
    ("Close and undo",
     "",
     [("15-close", [
         "Close (×)|Closes the definition straight away.",
         "Undo|You have 10 seconds to bring it back with all its edits.",
     ], None)]),
    ("Tablet and dark mode",
     "",
     [("16-tablet", [
         "Details|On narrow screens the details panel opens as a drawer.",
         "Drawer|It also opens when you select a step; close it with × or by tapping outside.",
      ], None),
      ("17-dark", [
         "Theme|Dark mode for the screen. Exports stay light so they print well.",
      ], None)]),
]

SHORTCUTS = [
    ("Tab / Shift+Tab", "Move between controls and steps"),
    ("Enter or Space", "Select the focused step"),
    ("Escape", "Clear the selected step"),
    ("← / → on the View control", "Switch view"),
    ("Ctrl/⌘ + mouse wheel", "Zoom around the pointer (the wheel alone scrolls)"),
    ("Arrow keys (Arrange on)", "Move the focused step 8 px; with Shift 32 px"),
]

TIPS = [
    ("Privacy", "Files are read and kept in this browser only. Clearing the browser's site data removes them, so download a Project file as a backup."),
    ("Big processes", "Very wide processes are too large for a PNG in some browsers: BPMap then tells you to use SVG or PDF, which have no size limit."),
    ("Characters in PDF", "PDF exports use standard fonts; characters outside Western European languages show as \"?\". Use SVG, PowerPoint or draw.io for those."),
    ("What the export doesn't contain", "Who may cancel, rescind or correct (the security policy), and the logic inside a condition. BPMap shows what Workday exports."),
]

# --------------------------------------------------------------------------- arrows

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def place_markers(meta):
    """Pick a spot for each numbered marker: near its target, inside the image, away from other
    markers and targets. Returns [(ann, cx, cy, r)]."""
    W, H = meta["w"], meta["h"]
    r = max(11.0, min(W, H) * 0.017)
    placed = []
    lines = []  # arrows already drawn, to avoid crossings
    boxes = []
    for a in meta["anns"]:
        x0, y0 = clamp(a["x"], 0, W), clamp(a["y"], 0, H)
        x1, y1 = clamp(a["x"] + a["w"], 0, W), clamp(a["y"] + a["h"], 0, H)
        # A target mostly outside the screenshot means the capture scrolled it away: the arrow would
        # point at the wrong control. Fail loudly instead of drawing it.
        visible = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if visible < min(0.5 * max(1.0, a["w"] * a["h"]), 4000.0):  # huge bands (lanes) only need a visible part
            sys.exit(f'pointer {a["n"]} ({a["label"]}) is mostly outside its screenshot: fix capture.mjs')
        boxes.append((x0, y0, x1, y1))
    for i, a in enumerate(meta["anns"]):
        x0, y0, x1, y1 = boxes[i]
        cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
        best = None
        # capture.mjs may ask for a side (e.g. "left" for the right-hand panel, so markers sit over the
        # empty lanes instead of on panel text); fall back to any side when there is no room there.
        centre = {"left": 180, "right": 0, "up": 270, "down": 90}.get(a.get("side", ""))
        angle_sets = [[(centre + k) % 360 for k in range(-40, 41, 10)], list(range(0, 360, 20))] if centre is not None else [list(range(0, 360, 20))]
        for angles in angle_sets:
            for dist in (5.0, 7.5, 10.0, 3.5):
                d = r * dist
                for ang in angles:
                    t = math.radians(ang)
                    # start from the box edge in that direction, then step out by d
                    ex = cx0 + math.cos(t) * ((x1 - x0) / 2)
                    ey = cy0 + math.sin(t) * ((y1 - y0) / 2)
                    px, py = ex + math.cos(t) * d, ey + math.sin(t) * d
                    if not (r + 4 <= px <= W - r - 4 and r + 4 <= py <= H - r - 4):
                        continue
                    score = 0.0
                    for (_, qx, qy, _) in placed:  # keep markers apart
                        score -= max(0.0, 6 * r - math.hypot(px - qx, py - qy)) * 4
                    for j, (bx0, by0, bx1, by1) in enumerate(boxes):  # don't sit on any target
                        if bx0 - r < px < bx1 + r and by0 - r < py < by1 + r:
                            score -= 400 if j == i else 120
                    score -= abs(dist - 5.0) * 6  # prefer the standard distance
                    qx, qy = edge_point(boxes[i], px, py, 3.0)
                    for (lx0, ly0, lx1, ly1) in lines:  # crossing arrows are confusing
                        if crosses((px, py), (qx, qy), (lx0, ly0), (lx1, ly1)):
                            score -= 300
                    if best is None or score > best[0]:
                        best = (score, px, py)
                if best and best[0] > -1:
                    break  # a perfect spot at this distance
            if best and best[0] > -100:
                break  # good enough on the preferred side (no overlap with a target or a crossing)
        if best is None:  # no room outside: sit at the box's top-left corner
            best = (0, clamp(x0 + r + 2, r, W - r), clamp(y0 + r + 2, r, H - r))
        placed.append((a, best[1], best[2], r))
        qx, qy = edge_point(boxes[i], best[1], best[2], 3.0)
        lines.append((best[1], best[2], qx, qy))
    return placed, boxes, r


def crosses(p1, p2, p3, p4):
    """Do segments p1-p2 and p3-p4 properly intersect?"""
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def edge_point(box, px, py, pad):
    """Where the line from (px, py) to the box centre crosses the (padded) box edge."""
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = px - cx, py - cy
    if dx == 0 and dy == 0:
        return cx, cy
    tx = (x1 - cx) / abs(dx) if dx else math.inf
    ty = (y1 - cy) / abs(dy) if dy else math.inf
    t = min(tx, ty)
    return cx + dx * t, cy + dy * t


def overlay_svg(name):
    m = META[name]
    W, H = m["w"], m["h"]
    placed, boxes, r = place_markers(m)
    sw = max(2.0, r * 0.2)
    pad = 3.0
    parts = [f'<svg class="ov" viewBox="0 0 {W} {H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">',
             f'<defs><marker id="ah-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="4.2" markerHeight="4.2" orient="auto-start-reverse">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>']
    for (a, px, py, _), box in zip(placed, boxes):
        x0, y0, x1, y1 = box
        parts.append(f'<rect x="{x0 - pad:.1f}" y="{y0 - pad:.1f}" width="{x1 - x0 + 2 * pad:.1f}" height="{y1 - y0 + 2 * pad:.1f}" rx="5" '
                     f'fill="{ACCENT}" fill-opacity="0.07" stroke="#fff" stroke-width="{sw + 2.5:.1f}" stroke-opacity="0.9"/>')
        parts.append(f'<rect x="{x0 - pad:.1f}" y="{y0 - pad:.1f}" width="{x1 - x0 + 2 * pad:.1f}" height="{y1 - y0 + 2 * pad:.1f}" rx="5" '
                     f'fill="none" stroke="{ACCENT}" stroke-width="{sw:.1f}"/>')
        ex, ey = edge_point(box, px, py, pad + sw)
        dist = math.hypot(ex - px, ey - py)
        if dist > r + 4:
            sx, sy = px + (ex - px) * (r / dist), py + (ey - py) * (r / dist)
            parts.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#fff" stroke-width="{sw + 2.5:.1f}" stroke-linecap="round"/>')
            parts.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{ACCENT}" stroke-width="{sw:.1f}" stroke-linecap="round" marker-end="url(#ah-{name})"/>')
    for (a, px, py, _) in placed:
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{ACCENT}" stroke="#fff" stroke-width="{max(2.0, r * 0.18):.1f}"/>')
        parts.append(f'<text x="{px:.1f}" y="{py + r * 0.36:.1f}" text-anchor="middle" font-size="{r * 1.05:.1f}" font-weight="700" fill="#fff" '
                     f'font-family="-apple-system, Helvetica Neue, Arial, sans-serif">{a["n"]}</text>')
    parts.append("</svg>")
    return "".join(parts)

# --------------------------------------------------------------------------- page

CSS = r"""
@page { size: A4 landscape; margin: 11mm 12mm 12mm 12mm;
  @top-left { content: "BPMap for Workday · User guide"; font: 600 7.5pt -apple-system, 'Helvetica Neue', Arial; color: #0F9D8A; }
  @top-right { content: "Screenshots use synthetic sample data"; font: 7.5pt -apple-system, 'Helvetica Neue', Arial; color: #94A3B8; }
  @bottom-left { content: "Independent product · not affiliated with Workday, Inc. Workday® is a trademark of Workday, Inc."; font: 7pt -apple-system, 'Helvetica Neue', Arial; color: #94A3B8; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt -apple-system, 'Helvetica Neue', Arial; color: #64748B; }
}
@page cover { margin: 0; @top-left { content: none } @top-right { content: none } @bottom-left { content: none } @bottom-right { content: none } }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html { font-family: -apple-system, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif; color: #1E293B; font-size: 9.4pt; line-height: 1.42; }
body { margin: 0; }
.cover { page: cover; width: 297mm; height: 210mm; position: relative; overflow: hidden; break-after: page;
  background: linear-gradient(160deg, #0B1B36 0%, #14284B 55%, #0F3B57 100%); color: #fff; padding: 24mm 22mm; }
.cover .eyebrow { letter-spacing: .18em; font-size: 9pt; font-weight: 700; color: #5EEAD4; text-transform: uppercase; }
.cover h1 { font-size: 40pt; line-height: 1.05; margin: 8mm 0 4mm; font-weight: 800; letter-spacing: -.02em; }
.cover h1 span { color: #5EEAD4; }
.cover .tag { font-size: 14pt; color: #CBD5E1; max-width: 150mm; line-height: 1.4; }
.cover .bar { width: 28mm; height: 2.2mm; background: #0F9D8A; border-radius: 2mm; margin: 10mm 0 8mm; }
.cover .meta { font-size: 10pt; color: #CBD5E1; line-height: 1.7; }
.cover .shot { position: absolute; right: -14mm; bottom: -6mm; width: 150mm; border-radius: 4mm; box-shadow: 0 10mm 30mm rgba(0,0,0,.45); transform: rotate(-3deg); }
.cover .foot { position: absolute; left: 22mm; bottom: 12mm; width: 120mm; font-size: 7.6pt; color: #94A3B8; }
.toc-page { break-after: page; }
h2.doc { font-size: 18pt; color: #14284B; margin: 0 0 4mm; letter-spacing: -.01em; }
.toc { columns: 2; column-gap: 14mm; list-style: none; margin: 0; padding: 0; }
.toc li { break-inside: avoid; padding: 1.6mm 0; border-bottom: 1px dotted #CBD5E1; font-size: 10.5pt; }
.toc .num { display: inline-block; width: 9mm; color: #0F9D8A; font-weight: 700; }
.how { margin-top: 7mm; display: flex; gap: 6mm; align-items: center; background: #F1F5F9; border-radius: 3mm; padding: 4mm 5mm; font-size: 9.6pt; }
.how .dot { flex: none; width: 7mm; height: 7mm; border-radius: 50%; background: """ + ACCENT + r"""; color: #fff; font-weight: 700; display: grid; place-items: center; font-size: 10pt; }
section.sec { break-before: page; }
.sec-head { display: flex; align-items: baseline; gap: 3mm; border-bottom: 2px solid #0F9D8A; padding-bottom: 1.6mm; margin-bottom: 1.5mm; }
.sec-head .n { color: #0F9D8A; font-weight: 800; font-size: 15pt; }
.sec-head h2 { margin: 0; font-size: 15pt; color: #14284B; letter-spacing: -.01em; }
.intro { color: #475569; margin: 0 0 3mm; font-size: 9.6pt; }
.panel { display: flex; gap: 6mm; align-items: flex-start; break-inside: avoid; margin-bottom: 4mm; }
.fig { position: relative; flex: none; border: 1px solid #CBD5E1; border-radius: 2mm; overflow: hidden; box-shadow: 0 1mm 3mm rgba(15,23,42,.10); }
.fig img { display: block; width: 100%; height: 100%; }
.fig .ov { position: absolute; inset: 0; width: 100%; height: 100%; }
.steps { flex: 1; min-width: 0; list-style: none; margin: 0; padding: 0; }
.steps li { display: flex; gap: 2.4mm; margin-bottom: 2.1mm; break-inside: avoid; }
.steps .badge { flex: none; width: 5.2mm; height: 5.2mm; border-radius: 50%; background: """ + ACCENT + r"""; color: #fff; font-weight: 700; font-size: 8.2pt; display: grid; place-items: center; margin-top: .2mm; }
.steps b { color: #14284B; }
.note { margin-top: 2.5mm; padding: 2mm 3mm; background: #F0FDFA; border-left: 1.2mm solid #0F9D8A; border-radius: 1mm; color: #134E4A; font-size: 8.8pt; }
table.keys { border-collapse: collapse; width: 100%; font-size: 9.4pt; margin-bottom: 6mm; }
table.keys td { padding: 1.8mm 2.5mm; border-bottom: 1px solid #E2E8F0; vertical-align: top; }
table.keys td:first-child { width: 70mm; font-weight: 600; color: #14284B; white-space: nowrap; }
kbd { font: 600 8.6pt 'SF Mono', Menlo, Consolas, monospace; background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 1mm; padding: .3mm 1.4mm; }
.tips { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
.tip { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 2mm; padding: 3mm 4mm; }
.tip b { display: block; color: #14284B; margin-bottom: 1mm; }
"""

# Content box of a landscape A4 page (mm): 273 wide; ~180 tall after header/footer.
FIG_MAX_W = 186.0
STEPS_MIN_W = 76.0


def fig_size(name, max_h):
    m = META[name]
    aspect = m["w"] / m["h"]
    w = min(FIG_MAX_W, max_h * aspect)
    return w, w / aspect


def panel_html(name, steps, note, max_h):
    m = META[name]
    if len(steps) != len(m["anns"]):
        sys.exit(f"{name}: {len(steps)} step texts but {len(m['anns'])} pointers in meta.json")
    w, h = fig_size(name, max_h)
    items = []
    for i, s in enumerate(steps, 1):
        label, text = s.split("|", 1)
        items.append(f'<li><span class="badge">{i}</span><span><b>{html.escape(label)}.</b> {html.escape(text)}</span></li>')
    note_html = f'<div class="note">{html.escape(note)}</div>' if note else ""
    return (f'<div class="panel"><div class="fig" style="width:{w:.1f}mm;height:{h:.1f}mm">'
            f'<img src="shots/{name}.png" alt="">{overlay_svg(name)}</div>'
            f'<div><ol class="steps">{"".join(items)}</ol>{note_html}</div></div>')


def section_html(i, title, intro, panels):
    # One panel: use the full page height. Several: share it.
    budget = 168.0 if intro else 175.0
    if len(panels) <= 2:
        max_h = budget if len(panels) == 1 else (budget - 4) / 2
        body = "".join(panel_html(n, s, note, max_h) for n, s, note in panels)
    else:  # first panel on its own page, the others share the next one
        rest = panels[1:]
        body = panel_html(*panels[0], budget) + '<div style="break-before: page"></div>' + "".join(
            panel_html(n, s, note, (180.0 - 4 * (len(rest) - 1)) / len(rest)) for n, s, note in rest)
    intro_html = f'<p class="intro">{html.escape(intro)}</p>' if intro else ""
    return (f'<section class="sec"><div class="sec-head"><span class="n">{i}</span><h2>{html.escape(title)}</h2></div>'
            f'{intro_html}{body}</section>')


def build_html():
    toc = "".join(f'<li><span class="num">{i}</span>{html.escape(t)}</li>' for i, (t, _, _) in enumerate(SECTIONS, 1))
    toc += f'<li><span class="num">{len(SECTIONS) + 1}</span>Keyboard, privacy and tips</li>'
    sections = "".join(section_html(i, *s) for i, s in enumerate(SECTIONS, 1))
    keys = "".join(f"<tr><td><kbd>{html.escape(k)}</kbd></td><td>{html.escape(v)}</td></tr>" for k, v in SHORTCUTS)
    tips = "".join(f'<div class="tip"><b>{html.escape(t)}</b>{html.escape(d)}</div>' for t, d in TIPS)
    last = (f'<section class="sec"><div class="sec-head"><span class="n">{len(SECTIONS) + 1}</span><h2>Keyboard, privacy and tips</h2></div>'
            f'<table class="keys">{keys}</table><div class="tips">{tips}</div></section>')
    today = date.today().strftime("%B %Y")
    cover = (f'<div class="cover"><div class="eyebrow">User guide</div>'
             f'<h1>BPMap <span>for Workday</span></h1>'
             f'<div class="tag">See, simulate and share Workday business processes, step by step.</div>'
             f'<div class="bar"></div>'
             f'<div class="meta">Version: Phase 2 release<br>{today}<br>All screenshots use synthetic sample data.</div>'
             f'<img class="shot" src="shots/02-workspace.png" alt="">'
             f'<div class="foot">Independent product, not affiliated with Workday, Inc. Workday® is a trademark of Workday, Inc.</div></div>')
    toc_page = (f'<div class="toc-page"><h2 class="doc">Contents</h2><ol class="toc">{toc}</ol>'
                f'<div class="how"><span class="dot">1</span><span>Numbered orange markers on each screenshot point at a control. '
                f'The matching number beside the screenshot says what it does.</span></div></div>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>BPMap for Workday · User guide</title>'
            f'<style>{CSS}</style></head><body>{cover}{toc_page}{sections}{last}</body></html>')


def main():
    # PNG on purpose: flat UI screenshots are smaller as PNG than as JPEG (tried: 7 MB vs 11 MB)
    HTML_OUT.write_text(build_html(), encoding="utf-8")
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}",
                        "--no-pdf-header-footer", "--virtual-time-budget=4000", f"--print-to-pdf={PDF_OUT}",
                        HTML_OUT.as_uri()], check=True, capture_output=True, timeout=180)
    print(f"wrote {PDF_OUT.relative_to(HERE.parent.parent)} ({PDF_OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
