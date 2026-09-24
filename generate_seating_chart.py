#!/usr/bin/env python3
"""Generate a vector PDF seating chart from the guest list CSV.

Styled after the wedding website theme (index.html): cream page background,
deep maroon ink/accents, serif type, dotted rules, and rounded "day-card"
style panels.

Page 1: floor plan of all tables (no seats).
Remaining pages: one per table showing each seat's assigned guest.
"""
import csv
import math
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

CSV_PATH = Path(__file__).parent / "guest-list - seating-assignment.csv"
OUT_PATH = Path(__file__).parent / "seating-chart.pdf"

PAGE_W, PAGE_H = letter

# Theme lifted from index.html's maroon-on-cream palette + serif type.
BG = HexColor("#fcf4e3")
CARD_BG = HexColor("#fffbf1")
INK = HexColor("#a62c25")
MAROON = HexColor("#a62c25")
MAROON_DARK = HexColor("#81221d")
DIVIDER = HexColor("#a62c25")

FONT_TITLE = "Times-Bold"
FONT_BODY = "Times-Roman"
FONT_ITALIC = "Times-Italic"

RECT_TABLES = list(range(1, 9))  # vertical rectangles, 4 seats/side
HORIZ_TABLE = 9  # landscape rectangle, 4 seats/side
CIRCLE_TABLES = list(range(10, 28))
TABLE_ORDER = [str(n) for n in range(1, 28)] + ["Sweetheart"]


def load_guests():
    """Return {table: [guest, ...]} ordered by each guest's original CSV seat index.

    Some tables have more guests than nominal seats (duplicate/overflow seat
    indices in the source data) -- keeping a list instead of an index-keyed
    dict preserves every guest instead of silently dropping duplicates.
    """
    tables = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            table = row["Table Assignment"].strip()
            if table == "V" or table == "":
                continue
            seat = row["Seat Assignment"].strip()
            first = row["First Name"].strip()
            last = row["Last Name"].strip()
            rsvp = row["RSVP"].strip()
            tables.setdefault(table, []).append({
                "seat": int(seat),
                "name": f"{first} {last}".strip(),
                "rsvp": rsvp,
            })
    for guest_list in tables.values():
        guest_list.sort(key=lambda g: g["seat"])
    return tables


def seat_capacity(guest_list, base):
    """Nominal seat count, expanded to fit every guest when a table overflows."""
    return max(base, len(guest_list))


# ---------------------------------------------------------------------------
# Shared chrome: page background, dotted rules, day-card panels
# ---------------------------------------------------------------------------

def draw_page_background(c):
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def dotted_rule(c, x1, x2, y):
    c.setStrokeColor(DIVIDER)
    c.setLineWidth(1)
    c.setDash([1, 3], 0)
    c.line(x1, y, x2, y)
    c.setDash([], 0)


def day_card(c, x, y, w, h, radius=18, top_accent=7):
    """Rounded card with a thick maroon top border, echoing .day-card in the site CSS."""
    c.setFillColor(CARD_BG)
    c.setStrokeColor(HexColor("#d9b9a8"))
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    c.setStrokeColor(MAROON)
    c.setLineWidth(top_accent)
    c.setLineCap(1)
    c.line(x + radius, y + h - top_accent / 2, x + w - radius, y + h - top_accent / 2)


# ---------------------------------------------------------------------------
# Seat position helpers (shared between floor plan and per-table pages)
# ---------------------------------------------------------------------------

def circle_seat_pos(cx, cy, radius, i, n=8):
    """Seat i=0 at top (12 o'clock), proceeding clockwise."""
    angle = math.radians(90 - (360 / n) * i)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def rect_side_split(position, n):
    """Split n seats across the two long edges (first side gets any odd extra seat).

    Returns (side, frac) where side is 0 (first edge) or 1 (second edge) and
    frac in (0, 1) is how far along that edge the seat sits.
    """
    left_count = (n + 1) // 2
    right_count = n - left_count
    if position < left_count:
        k = position
        return 0, (k + 0.5) / left_count
    k = right_count - 1 - (position - left_count)
    return 1, (k + 0.5) / right_count


def rect_seat_pos_vertical(cx, cy, width, height, position, n=8):
    """Seats wrap up the left edge (bottom->top), then down the right edge (top->bottom)."""
    half_w, half_h = width / 2, height / 2
    side, frac = rect_side_split(position, n)
    x = cx - half_w if side == 0 else cx + half_w
    y = cy - half_h + height * frac
    return x, y


def rect_seat_pos_horizontal(cx, cy, width, height, position, n=8):
    """Seats wrap left->right along the bottom edge, then right->left along the top edge."""
    half_w, half_h = width / 2, height / 2
    side, frac = rect_side_split(position, n)
    y = cy - half_h if side == 0 else cy + half_h
    x = cx - half_w + width * frac
    return x, y


# ---------------------------------------------------------------------------
# Page 1: floor plan
# ---------------------------------------------------------------------------

def draw_floor_plan(c):
    draw_page_background(c)

    c.setFont(FONT_TITLE, 22)
    c.setFillColor(MAROON)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 46, "Reception Floor Plan")
    c.setFont(FONT_ITALIC, 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 62, "Jessie & Jude \u00b7 Tulsa, Oklahoma")
    dotted_rule(c, 60, PAGE_W - 60, PAGE_H - 76)

    c.setFont(FONT_BODY, 8)
    c.setFillColor(MAROON)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 92, "WINDOWS")
    c.drawCentredString(PAGE_W / 2, 42, "ENTRANCE DOORS")
    c.saveState()
    c.translate(48, PAGE_H / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, "COCKTAIL HOUR DOORS")
    c.restoreState()

    center_x = PAGE_W / 2
    col_gap = 34
    right_col_x = center_x + col_gap
    left_col_x = center_x - col_gap

    rect_w, rect_h = 30, 88
    row_gap = 10
    top_y = PAGE_H - 160

    # Sweetheart table
    sweetheart_r = 24
    sweetheart_cy = top_y + 30
    c.setFillColor(CARD_BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.4)
    p = c.beginPath()
    p.arc(center_x - sweetheart_r, sweetheart_cy - sweetheart_r,
          center_x + sweetheart_r, sweetheart_cy + sweetheart_r, startAng=180, extent=180)
    p.close()
    c.drawPath(p, fill=1, stroke=1)
    c.setFillColor(MAROON)
    c.setFont(FONT_TITLE, 7)
    c.drawCentredString(center_x, sweetheart_cy - 4, "Sweetheart")

    # Rectangular table columns (1,3,5,7 right; 2,4,6,8 left)
    right_labels = [1, 3, 5, 7]
    left_labels = [2, 4, 6, 8]
    for i in range(4):
        cy = top_y - i * (rect_h + row_gap) - rect_h / 2
        draw_rect_floor(c, right_col_x, cy, rect_w, rect_h, right_labels[i])
        draw_rect_floor(c, left_col_x, cy, rect_w, rect_h, left_labels[i])

    col_bottom_y = top_y - 3 * (rect_h + row_gap) - rect_h

    # Table 9: landscape rectangle centered below both columns
    t9_w, t9_h = 100, 26
    t9_cy = col_bottom_y - 34
    draw_rect_floor(c, center_x, t9_cy, t9_w, t9_h, 9)

    # Circle rings flanking the columns: left = 10-18, right = 19-27
    circle_d = 34
    circle_gap = 8
    ring_top_y = top_y - 6
    ring_span_bottom = t9_cy - t9_h / 2
    n = 9
    step = (ring_top_y - ring_span_bottom) / (n - 1)
    left_ring_x = left_col_x - col_gap - rect_w / 2 - circle_d / 2 - circle_gap
    right_ring_x = right_col_x + col_gap + rect_w / 2 + circle_d / 2 + circle_gap
    for i in range(n):
        cy = ring_top_y - i * step
        draw_circle_floor(c, left_ring_x, cy, circle_d / 2, 10 + i)
        draw_circle_floor(c, right_ring_x, cy, circle_d / 2, 19 + i)


def draw_rect_floor(c, cx, cy, w, h, label):
    c.setFillColor(CARD_BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.2)
    c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)
    c.setFillColor(MAROON)
    c.setFont(FONT_TITLE, 9)
    c.drawCentredString(cx, cy - 3, str(label))


def draw_circle_floor(c, cx, cy, r, label):
    c.setFillColor(CARD_BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.2)
    c.circle(cx, cy, r, fill=1, stroke=1)
    c.setFillColor(MAROON)
    c.setFont(FONT_TITLE, 9)
    c.drawCentredString(cx, cy - 3, str(label))


# ---------------------------------------------------------------------------
# Per-table pages
# ---------------------------------------------------------------------------

def seat_label(c, x, y, seat_number, guest, anchor):
    name = guest["name"] if guest else "-- open --"
    note = ""
    if guest and guest["rsvp"] not in ("Attending", ""):
        note = f" ({guest['rsvp']})"
    c.setFont(FONT_BODY, 10)
    c.setFillColor(MAROON_DARK)
    if anchor == "left":
        c.drawRightString(x - 10, y - 3, f"{seat_number}. {name}{note}")
    elif anchor == "right":
        c.drawString(x + 10, y - 3, f"{seat_number}. {name}{note}")
    elif anchor == "top":
        c.drawCentredString(x, y + 12, f"{seat_number}. {name}{note}")
    elif anchor == "bottom":
        c.drawCentredString(x, y - 20, f"{seat_number}. {name}{note}")


def draw_table_header(c, title, subtitle):
    c.setFont(FONT_TITLE, 26)
    c.setFillColor(MAROON)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 100, title)
    c.setFont(FONT_ITALIC, 12)
    c.setFillColor(MAROON_DARK)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 120, subtitle)
    dotted_rule(c, 100, PAGE_W - 100, PAGE_H - 136)


def circle_anchor(sx, sy, cx, cy):
    """Pick a label anchor side from a seat's position relative to the table center."""
    dx, dy = sx - cx, sy - cy
    if abs(dy) > abs(dx) * 2:
        return "top" if dy > 0 else "bottom"
    return "right" if dx > 0 else "left"


def draw_circle_table_page(c, table_num, guest_list):
    draw_page_background(c)
    day_card(c, 50, 60, PAGE_W - 100, PAGE_H - 120)

    cx, cy = PAGE_W / 2, PAGE_H / 2 + 30
    r = 175
    n = seat_capacity(guest_list, base=8)
    draw_table_header(c, f"Table {table_num}", f"{len(guest_list)} of {n} seats assigned")

    c.setFillColor(BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(2)
    c.circle(cx, cy, r, fill=1, stroke=1)

    for position in range(n):
        sx, sy = circle_seat_pos(cx, cy, r, position, n=n)
        c.setFillColor(MAROON)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        lx, ly = circle_seat_pos(cx, cy, r + 20, position, n=n)
        anchor = circle_anchor(sx, sy, cx, cy)
        guest = guest_list[position] if position < len(guest_list) else None
        seat_label(c, lx, ly, position + 1, guest, anchor)


def draw_rect_table_page(c, table_num, guest_list, horizontal):
    draw_page_background(c)
    day_card(c, 50, 60, PAGE_W - 100, PAGE_H - 120)

    cx, cy = PAGE_W / 2, PAGE_H / 2 + 30
    n = seat_capacity(guest_list, base=8)
    if horizontal:
        w, h = max(420, 40 * n), 110
    else:
        w, h = 160, max(380, 42 * n)
    draw_table_header(c, f"Table {table_num}", f"{len(guest_list)} of {n} seats assigned")

    c.setFillColor(BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(2)
    c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)

    pos_fn = rect_seat_pos_horizontal if horizontal else rect_seat_pos_vertical
    for position in range(n):
        sx, sy = pos_fn(cx, cy, w, h, position, n=n)
        c.setFillColor(MAROON)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        # stagger alternating seats along the long edge so adjacent name labels don't collide
        side, frac = rect_side_split(position, n)
        stagger = 14 if position % 2 == 0 else 0
        if horizontal:
            lx, ly = pos_fn(cx, cy, w + 30, h + 40, position, n=n)
            ly = ly - stagger if side == 0 else ly + stagger
            anchor = "bottom" if side == 0 else "top"
        else:
            lx, ly = pos_fn(cx, cy, w + 40, h + 30, position, n=n)
            anchor = "left" if side == 0 else "right"
        guest = guest_list[position] if position < len(guest_list) else None
        seat_label(c, lx, ly, position + 1, guest, anchor)


def draw_sweetheart_page(c, guest_list):
    draw_page_background(c)
    day_card(c, 50, 60, PAGE_W - 100, PAGE_H - 120)

    cx, cy = PAGE_W / 2, PAGE_H / 2 + 60
    r = 120
    n = seat_capacity(guest_list, base=2)
    draw_table_header(c, "Sweetheart Table", f"{len(guest_list)} of {n} seats assigned")

    c.setFillColor(BG)
    c.setStrokeColor(MAROON)
    c.setLineWidth(2)
    p = c.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=180, extent=180)
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    for position in range(n):
        dx = -r / 2 + r * position / max(n - 1, 1) if n > 1 else 0
        sx, sy = cx + dx, cy
        c.setFillColor(MAROON)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        guest = guest_list[position] if position < len(guest_list) else None
        seat_label(c, sx, cy - r - 10, position + 1, guest, "bottom")


# ---------------------------------------------------------------------------


def main():
    tables = load_guests()
    c = canvas.Canvas(str(OUT_PATH), pagesize=letter)

    draw_floor_plan(c)
    c.showPage()

    for table_key in TABLE_ORDER:
        guest_list = tables.get(table_key, [])
        if table_key == "Sweetheart":
            draw_sweetheart_page(c, guest_list)
        else:
            n = int(table_key)
            if n in CIRCLE_TABLES:
                draw_circle_table_page(c, n, guest_list)
            else:
                draw_rect_table_page(c, n, guest_list, horizontal=(n == HORIZ_TABLE))
        c.showPage()

    c.save()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
