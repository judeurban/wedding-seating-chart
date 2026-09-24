#!/usr/bin/env python3
"""Generate a vector PDF seating chart from the guest list CSV.

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

INK = HexColor("#2b2b2b")
FILL = HexColor("#f4efe9")
ACCENT = HexColor("#8a6d5c")

RECT_TABLES = list(range(1, 9))  # vertical rectangles, 4 seats/side
HORIZ_TABLE = 9  # landscape rectangle, 4 seats/side
CIRCLE_TABLES = list(range(10, 28))
TABLE_ORDER = [str(n) for n in range(1, 28)] + ["Sweetheart"]


def load_guests():
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
            tables.setdefault(table, {})[int(seat)] = {
                "name": f"{first} {last}".strip(),
                "rsvp": rsvp,
            }
    return tables


# ---------------------------------------------------------------------------
# Seat position helpers (shared between floor plan and per-table pages)
# ---------------------------------------------------------------------------

def circle_seat_pos(cx, cy, radius, i, n=8):
    """Seat i=0 at top (12 o'clock), proceeding clockwise."""
    angle = math.radians(90 - (360 / n) * i)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def rect_seat_pos_vertical(cx, cy, width, height, seat_index):
    """Seats 0-3 up the left edge (bottom->top), 4-7 down the right edge (top->bottom)."""
    half_w, half_h = width / 2, height / 2
    if seat_index < 4:
        k = seat_index
        x = cx - half_w
    else:
        k = 3 - (seat_index - 4)
        x = cx + half_w
    y = cy - half_h + height * (k + 0.5) / 4
    return x, y


def rect_seat_pos_horizontal(cx, cy, width, height, seat_index):
    """Seats 0-3 left->right along bottom edge, 4-7 right->left along top edge."""
    half_w, half_h = width / 2, height / 2
    if seat_index < 4:
        k = seat_index
        y = cy - half_h
    else:
        k = 3 - (seat_index - 4)
        y = cy + half_h
    x = cx - half_w + width * (k + 0.5) / 4
    return x, y


# ---------------------------------------------------------------------------
# Page 1: floor plan
# ---------------------------------------------------------------------------

def draw_floor_plan(c):
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(INK)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 40, "Reception Floor Plan")

    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 58, "WINDOWS")
    c.drawCentredString(PAGE_W / 2, 42, "ENTRANCE DOORS")
    c.saveState()
    c.translate(50, PAGE_H / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, "COCKTAIL HOUR DOORS")
    c.restoreState()

    center_x = PAGE_W / 2
    col_gap = 34
    right_col_x = center_x + col_gap
    left_col_x = center_x - col_gap

    rect_w, rect_h = 30, 88
    row_gap = 10
    top_y = PAGE_H - 130

    # Sweetheart table
    sweetheart_r = 24
    sweetheart_cy = top_y + 30
    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    p = c.beginPath()
    p.arc(center_x - sweetheart_r, sweetheart_cy - sweetheart_r,
          center_x + sweetheart_r, sweetheart_cy + sweetheart_r, startAng=180, extent=180)
    p.close()
    c.drawPath(p, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7)
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
    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 3, str(label))


def draw_circle_floor(c, cx, cy, r, label):
    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.circle(cx, cy, r, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 3, str(label))


# ---------------------------------------------------------------------------
# Per-table pages
# ---------------------------------------------------------------------------

def seat_label(c, x, y, seat_index, guest, anchor):
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(ACCENT)
    name = guest["name"] if guest else "-- open --"
    note = ""
    if guest and guest["rsvp"] not in ("Attending", ""):
        note = f" ({guest['rsvp']})"
    c.setFont("Helvetica", 10)
    c.setFillColor(INK)
    if anchor == "left":
        c.drawRightString(x - 10, y - 3, f"{seat_index}. {name}{note}")
    elif anchor == "right":
        c.drawString(x + 10, y - 3, f"{seat_index}. {name}{note}")
    elif anchor == "top":
        c.drawCentredString(x, y + 12, f"{seat_index}. {name}{note}")
    elif anchor == "bottom":
        c.drawCentredString(x, y - 20, f"{seat_index}. {name}{note}")


def draw_table_header(c, title, subtitle):
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(INK)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 60, title)
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 80, subtitle)


def draw_circle_table_page(c, table_num, seats):
    cx, cy = PAGE_W / 2, PAGE_H / 2 + 30
    r = 175
    seated = sum(1 for i in range(8) if seats.get(i))
    draw_table_header(c, f"Table {table_num}", f"{seated} of 8 seats assigned")

    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2)
    c.circle(cx, cy, r, fill=1, stroke=1)

    for i in range(8):
        sx, sy = circle_seat_pos(cx, cy, r, i)
        c.setFillColor(ACCENT)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        lx, ly = circle_seat_pos(cx, cy, r + 20, i)
        anchor = "top" if i in (0,) else "bottom" if i in (4,) else \
            "left" if i in (5, 6, 7) else "right"
        seat_label(c, lx, ly, i, seats.get(i), anchor)


def draw_rect_table_page(c, table_num, seats, horizontal):
    cx, cy = PAGE_W / 2, PAGE_H / 2 + 30
    if horizontal:
        w, h = 420, 110
    else:
        w, h = 160, 380
    seated = sum(1 for i in range(8) if seats.get(i))
    draw_table_header(c, f"Table {table_num}", f"{seated} of 8 seats assigned")

    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2)
    c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)

    pos_fn = rect_seat_pos_horizontal if horizontal else rect_seat_pos_vertical
    for i in range(8):
        sx, sy = pos_fn(cx, cy, w, h, i)
        c.setFillColor(ACCENT)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        # stagger alternating seats along the long edge so adjacent name labels don't collide
        k = i if i < 4 else 3 - (i - 4)
        stagger = 14 if k % 2 == 0 else 0
        if horizontal:
            lx, ly = pos_fn(cx, cy, w + 30, h + 40, i)
            ly = ly - stagger if i < 4 else ly + stagger
            anchor = "bottom" if i < 4 else "top"
        else:
            lx, ly = pos_fn(cx, cy, w + 40, h + 30, i)
            anchor = "left" if i < 4 else "right"
        seat_label(c, lx, ly, i, seats.get(i), anchor)


def draw_sweetheart_page(c, seats):
    cx, cy = PAGE_W / 2, PAGE_H / 2 + 60
    r = 120
    seated = sum(1 for i in range(2) if seats.get(i))
    draw_table_header(c, "Sweetheart Table", f"{seated} of 2 seats assigned")

    c.setFillColor(FILL)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2)
    p = c.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=180, extent=180)
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    for i, dx in ((0, -r / 2), (1, r / 2)):
        sx, sy = cx + dx, cy
        c.setFillColor(ACCENT)
        c.circle(sx, sy, 6, fill=1, stroke=0)
        seat_label(c, sx, cy - r - 10, i, seats.get(i), "bottom")


# ---------------------------------------------------------------------------


def main():
    tables = load_guests()
    c = canvas.Canvas(str(OUT_PATH), pagesize=letter)

    draw_floor_plan(c)
    c.showPage()

    for table_key in TABLE_ORDER:
        seats = tables.get(table_key, {})
        if table_key == "Sweetheart":
            draw_sweetheart_page(c, seats)
        else:
            n = int(table_key)
            if n in CIRCLE_TABLES:
                draw_circle_table_page(c, n, seats)
            else:
                draw_rect_table_page(c, n, seats, horizontal=(n == HORIZ_TABLE))
        c.showPage()

    c.save()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
