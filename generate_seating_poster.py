#!/usr/bin/env python3
"""Create a guest-facing seating poster PDF with two tables per page."""
import argparse
import csv
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).parent
DEFAULT_CSV = BASE_DIR / "guest-list - seating-assignment.csv"
DEFAULT_OUTPUT = BASE_DIR / "guest-seating-poster.pdf"
PAGE_W, PAGE_H = letter

BG = HexColor("#fcf4e3")
CARD_BG = HexColor("#fffbf1")
MAROON = HexColor("#a62c25")
MAROON_DARK = HexColor("#81221d")
LINE = HexColor("#d9b9a8")
BODY = HexColor("#542d29")

FONT_NAMES = "PosterTimes"
FONT_NUMBERS = "PosterScript"


def register_fonts():
    """Prefer the requested installed fonts, with portable PDF font fallbacks."""
    global FONT_NAMES, FONT_NUMBERS
    fonts = {
        FONT_NAMES: (
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/Library/Fonts/Times New Roman.ttf",
            "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ),
        FONT_NUMBERS: (
            str(BASE_DIR / "fonts" / "PinyonScript-Regular.ttf"),
        ),
    }
    for font_name, candidates in fonts.items():
        font_path = next((Path(path) for path in candidates if Path(path).is_file()), None)
        if font_path is not None:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        elif font_name == FONT_NAMES:
            FONT_NAMES = "Times-Roman"
        else:
            FONT_NUMBERS = "Times-Italic"


def load_tables(csv_path):
    tables = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            table = row.get("Table Assignment", "").strip()
            if not table or table.upper() == "V":
                continue
            first = row.get("First Name", "").strip()
            last = row.get("Last Name", "").strip()
            name = f"{first} {last}".strip()
            if not name:
                continue
            seat = row.get("Seat Assignment", "").strip()
            tables.setdefault(table, []).append((int(seat) if seat.isdigit() else None, name))

    for guests in tables.values():
        guests.sort(key=lambda guest: (guest[0] is None, guest[0] or 0))
    return tables


def table_sort_key(table):
    if table.isdigit():
        return (0, int(table))
    return (1, table.casefold())


def draw_page_header(pdf, page_number, page_count):
    pdf.setFillColor(BG)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    pdf.setFillColor(MAROON)
    pdf.setFont("Times-Bold", 21)
    pdf.drawCentredString(PAGE_W / 2, PAGE_H - 43, "Jessie & Jude")
    pdf.setFillColor(MAROON_DARK)
    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(PAGE_W / 2, PAGE_H - 62, "Reception Seating")
    pdf.setStrokeColor(MAROON)
    pdf.setLineWidth(1)
    pdf.setDash([1, 3], 0)
    pdf.line(58, PAGE_H - 76, PAGE_W - 58, PAGE_H - 76)
    pdf.setDash([], 0)
    pdf.setFillColor(MAROON_DARK)
    pdf.setFont("Times-Roman", 8)
    pdf.drawCentredString(PAGE_W / 2, 30, f"{page_number} / {page_count}")


def draw_table(pdf, table, guests, x, y, width, height):
    pdf.setFillColor(CARD_BG)
    pdf.setStrokeColor(LINE)
    pdf.setLineWidth(1)
    pdf.roundRect(x, y, width, height, 12, fill=1, stroke=1)

    pdf.setStrokeColor(MAROON)
    pdf.setLineWidth(6)
    pdf.setLineCap(1)
    pdf.line(x + 18, y + height - 3, x + width - 18, y + height - 3)

    heading_y = y + height - 57
    pdf.setFillColor(MAROON)
    pdf.setFont(FONT_NUMBERS, 38)
    pdf.drawCentredString(PAGE_W / 2, heading_y + 2, f"Table {table}")

    rule_y = heading_y - 16
    pdf.setStrokeColor(LINE)
    pdf.setLineWidth(0.8)
    pdf.line(x + 44, rule_y, x + width - 44, rule_y)

    available_height = rule_y - (y + 16)
    leading = min(22, available_height / max(len(guests), 1))
    font_size = min(17, max(11, leading * 0.76))
    pdf.setFillColor(BODY)
    pdf.setFont(FONT_NAMES, font_size)
    first_name_y = rule_y - max(17, (available_height - leading * len(guests)) / 2 + leading * 0.75)
    for index, (_, guest_name) in enumerate(guests):
        pdf.drawCentredString(PAGE_W / 2, first_name_y - index * leading, guest_name)


def create_poster(csv_path, output_path):
    tables = load_tables(csv_path)
    ordered_tables = sorted(tables, key=table_sort_key)
    if not ordered_tables:
        raise ValueError(f"No assigned guests found in {csv_path}")

    register_fonts()
    page_tables = [ordered_tables[index:index + 2] for index in range(0, len(ordered_tables), 2)]
    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    pdf.setTitle("Reception Seating")
    pdf.setAuthor("Jessie & Jude")

    margin = 48
    card_width = PAGE_W - margin * 2
    card_height = 310
    card_y_positions = (PAGE_H - 94 - card_height, 48)
    for page_number, tables_on_page in enumerate(page_tables, start=1):
        draw_page_header(pdf, page_number, len(page_tables))
        for index, table in enumerate(tables_on_page):
            draw_table(pdf, table, tables[table], margin, card_y_positions[index], card_width, card_height)
        pdf.showPage()

    pdf.save()
    print(f"Wrote {output_path} ({len(page_tables)} pages, {len(ordered_tables)} tables)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="guest assignment CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output PDF path")
    args = parser.parse_args()
    create_poster(args.csv, args.output)


if __name__ == "__main__":
    main()