from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import datetime, os, io

app = Flask(__name__)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
HEADER_IMAGE = os.path.join(BASE_DIR, "headerimage.jpg")
FOOTER_IMAGE = os.path.join(BASE_DIR, "headerimage.jpg")
LOGO_IMAGE   = os.path.join(BASE_DIR, "logo.png")

PAGE_W, PAGE_H = A4
GOLD  = colors.HexColor("#C9A84C")
WHITE = colors.white
BLACK = colors.black
DARK  = colors.HexColor("#1A1A2E")
LIGHT = colors.HexColor("#F0EFE9")

# ── Font registration (Windows + Linux + Mac) ─────────────────────────────────
def find_font(win_name, linux_path, mac_path=None):
    win_path = os.path.join(r"C:\Windows\Fonts", win_name)
    if os.path.exists(win_path):   return win_path
    if os.path.exists(linux_path): return linux_path
    if mac_path and os.path.exists(mac_path): return mac_path
    return None

font_regular = (find_font("georgia.ttf",  "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "/Library/Fonts/Georgia.ttf")
             or find_font("times.ttf",    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"))
font_bold    = (find_font("georgiab.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",    "/Library/Fonts/Georgia Bold.ttf")
             or find_font("timesbd.ttf",  "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"))
font_italic  = (find_font("georgiai.ttf","/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",  "/Library/Fonts/Georgia Italic.ttf")
             or find_font("timesi.ttf",   "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"))

if font_regular and font_bold and font_italic:
    pdfmetrics.registerFont(TTFont("Serif",        font_regular))
    pdfmetrics.registerFont(TTFont("Serif-Bold",   font_bold))
    pdfmetrics.registerFont(TTFont("Serif-Italic", font_italic))
    F_REG, F_BOLD, F_ITAL = "Serif", "Serif-Bold", "Serif-Italic"
else:
    F_REG, F_BOLD, F_ITAL = "Times-Roman", "Times-Bold", "Times-Italic"

HEADER_H = 62 * mm
FOOTER_H = 18 * mm
LEFT     = 10 * mm
RIGHT    = PAGE_W - 10 * mm
COL_W    = [100*mm, 32*mm, 26*mm, 37*mm]


def draw_header(c, company_name, company_locations, logo_path, header_image_path):
    """Draw the full branded header (page 1 only)."""
    if header_image_path and os.path.exists(header_image_path):
        c.drawImage(header_image_path, 0, PAGE_H - HEADER_H,
                    width=PAGE_W, height=HEADER_H,
                    preserveAspectRatio=False, mask='auto')
        c.setFillColor(colors.Color(0, 0, 0, alpha=0.58))
        c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
    else:
        c.setFillColor(DARK)
        c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont(F_BOLD, 28)
    c.drawCentredString(PAGE_W/2, PAGE_H - 16*mm, "I N V O I C E")

    c.setFillColor(GOLD)
    c.setFont(F_BOLD, 17)
    c.drawCentredString(PAGE_W/2, PAGE_H - 27*mm, company_name)

    c.setFillColor(WHITE)
    c.setFont(F_REG, 8)
    c.drawCentredString(PAGE_W/2, PAGE_H - 36*mm,
                        "  |  ".join(company_locations).upper())

    # Logo drawn last → above overlay
    if logo_path and os.path.exists(logo_path):
        lw = lh = 26 * mm
        c.drawImage(logo_path, PAGE_W/2 - lw/2, PAGE_H - HEADER_H + 5*mm,
                    width=lw, height=lh, preserveAspectRatio=True, mask='auto')


def draw_continuation_header(c, company_name, page_num):
    """Slim header for page 2+."""
    c.setFillColor(DARK)
    c.rect(0, PAGE_H - 18*mm, PAGE_W, 18*mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(F_BOLD, 11)
    c.drawString(LEFT, PAGE_H - 12*mm, company_name)
    c.setFillColor(WHITE)
    c.setFont(F_REG, 9)
    c.drawRightString(RIGHT, PAGE_H - 12*mm, f"Page {page_num}  (continued)")


def draw_footer(c, phone1, phone2, email, footer_image_path):
    """Draw footer on every page."""
    if footer_image_path and os.path.exists(footer_image_path):
        c.drawImage(footer_image_path, 0, 0,
                    width=PAGE_W, height=FOOTER_H,
                    preserveAspectRatio=False, mask='auto')
        c.setFillColor(colors.Color(0, 0, 0, alpha=0.62))
        c.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)
    else:
        c.setFillColor(DARK)
        c.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont(F_REG, 8.5)
    third = PAGE_W / 3
    c.drawCentredString(third * 0.5, 7*mm, f"Tel: {phone1}")
    c.drawCentredString(third * 1.5, 7*mm, email)
    c.drawCentredString(third * 2.5, 7*mm, f"Tel: {phone2}")


def draw_table_header_row(c, y):
    """Draw the dark column-header row at position y, return new y."""
    row_h = 10 * mm
    c.setFillColor(DARK)
    c.rect(LEFT, y - row_h, sum(COL_W), row_h, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(F_BOLD, 10)
    headers   = ["Item Description", "Price", "Qty", "Amount"]
    positions = [LEFT + 3*mm,
                 LEFT + COL_W[0] + COL_W[1]/2,
                 LEFT + COL_W[0] + COL_W[1] + COL_W[2]/2,
                 LEFT + COL_W[0] + COL_W[1] + COL_W[2] + COL_W[3]/2]
    aligns    = ["left", "center", "center", "center"]
    for txt, x, align in zip(headers, positions, aligns):
        if align == "center":
            c.drawCentredString(x, y - row_h + 3*mm, txt)
        else:
            c.drawString(x, y - row_h + 3*mm, txt)
    return y - row_h


def draw_invoice(buffer, client_name, invoice_date, items,
                 company_name, company_locations, phone1, phone2, email,
                 header_image_path=None, footer_image_path=None, logo_path=None):

    c = canvas.Canvas(buffer, pagesize=A4)
    page_num  = 1
    row_h     = 9 * mm   # height of each data row

    # ── PAGE 1 ────────────────────────────────────────────────────────────────
    draw_header(c, company_name, company_locations, logo_path, header_image_path)
    draw_footer(c, phone1, phone2, email, footer_image_path)

    # Personal info block
    y = PAGE_H - HEADER_H - 14*mm
    c.setFillColor(DARK); c.setFont(F_BOLD, 10)
    c.drawString(LEFT, y, "PERSONAL INFORMATION")
    y -= 6*mm
    c.setStrokeColor(colors.HexColor("#BBBBBB")); c.setLineWidth(0.6)
    c.line(LEFT, y, RIGHT, y)
    y -= 10*mm
    c.setFillColor(BLACK)
    c.setFont(F_BOLD, 11); c.drawString(LEFT, y, "Full Name:")
    c.setFont(F_REG,  11); c.drawString(LEFT + 28*mm, y, client_name)
    c.setFont(F_BOLD, 11); c.drawString(PAGE_W/2, y, "Invoice Date:")
    c.setFont(F_REG,  11); c.drawString(PAGE_W/2 + 34*mm, y, invoice_date)
    y -= 14*mm

    # Table column header
    y = draw_table_header_row(c, y)

    # ── Draw rows across pages ─────────────────────────────────────────────────
    # Bottom boundary = above footer + small margin
    bottom_limit = FOOTER_H + 30*mm   # leave room for total block on last page

    for i, (desc, price, qty) in enumerate(items):
        try:
            p, q = float(price), int(qty)
        except (ValueError, TypeError):
            p, q = 0.0, 0
        amount = p * q

        # Check if we need a new page
        if y - row_h < FOOTER_H + 6*mm:
            c.showPage()
            page_num += 1
            draw_continuation_header(c, company_name, page_num)
            draw_footer(c, phone1, phone2, email, footer_image_path)
            y = PAGE_H - 18*mm - 6*mm   # just below slim header
            y = draw_table_header_row(c, y)

        # Alternating row background
        bg = WHITE if i % 2 == 0 else LIGHT
        c.setFillColor(bg)
        c.rect(LEFT, y - row_h, sum(COL_W), row_h, fill=1, stroke=0)

        # Row border line
        c.setStrokeColor(colors.HexColor("#CCCCCC")); c.setLineWidth(0.4)
        c.rect(LEFT, y - row_h, sum(COL_W), row_h, fill=0, stroke=1)

        # Cell text
        c.setFillColor(BLACK); c.setFont(F_REG, 10)
        text_y = y - row_h + 2.5*mm
        c.drawString(LEFT + 3*mm, text_y, desc)
        c.drawCentredString(LEFT + COL_W[0] + COL_W[1]/2,         text_y, f"${p:,.2f}")
        c.drawCentredString(LEFT + COL_W[0] + COL_W[1] + COL_W[2]/2, text_y, str(q))
        c.drawCentredString(LEFT + COL_W[0] + COL_W[1] + COL_W[2] + COL_W[3]/2, text_y, f"${amount:,.2f}")

        y -= row_h

    # ── TOTAL block ───────────────────────────────────────────────────────────
    grand_total = sum(float(p) * int(q) for _, p, q in items
                      if str(p).replace('.','',1).isdigit())

    # If not enough room for total + message, new page
    if y - 30*mm < FOOTER_H + 6*mm:
        c.showPage()
        page_num += 1
        draw_continuation_header(c, company_name, page_num)
        draw_footer(c, phone1, phone2, email, footer_image_path)
        y = PAGE_H - 18*mm - 10*mm

    total_y = y - 12*mm
    c.setFillColor(DARK)
    c.roundRect(LEFT, total_y - 4*mm, sum(COL_W), 12*mm, 3, fill=1, stroke=0)
    c.setFillColor(GOLD); c.setFont(F_BOLD, 13)
    c.drawString(LEFT + 4*mm, total_y + 2*mm, f"Total:  ${grand_total:,.2f}")

    # MESSAGE
    msg_y = total_y - 18*mm
    c.setFont(F_BOLD, 10); c.setFillColor(DARK)
    c.drawString(LEFT, msg_y, "MESSAGE")
    c.setFont(F_ITAL, 10); c.setFillColor(colors.HexColor("#444444"))
    c.drawString(LEFT, msg_y - 8*mm,
                 f"Thank you for choosing {company_name}. We look forward to making your event truly memorable.")

    c.save()


@app.route("/")
def form():
    return render_template("form.html")


@app.route("/generate", methods=["POST"])
def generate():
    client_name  = request.form.get("client", "Client Name")
    invoice_date = request.form.get("date", str(datetime.date.today()))

    services = request.form.getlist("service")
    qtys     = request.form.getlist("qty")
    prices   = request.form.getlist("price")
    items    = [(s, p, q) for s, p, q in zip(services, prices, qtys) if s.strip()]

    company_name      = request.form.get("company_name", "Witness Event Planners")
    company_locations = [loc.strip() for loc in
                         request.form.get("locations", "Trivandrum,Thiruvalla,Kochi").split(",")]
    phone1 = request.form.get("phone1", "+91 6238191673")
    phone2 = request.form.get("phone2", "+91 9895684105")
    email  = request.form.get("email",  "witnesseventplanners@gmail.com")

    header_image_path = HEADER_IMAGE if os.path.exists(HEADER_IMAGE) else None
    footer_image_path = FOOTER_IMAGE if os.path.exists(FOOTER_IMAGE) else None
    logo_path         = LOGO_IMAGE   if os.path.exists(LOGO_IMAGE)   else None

    buffer = io.BytesIO()
    draw_invoice(buffer, client_name, invoice_date, items,
                 company_name, company_locations, phone1, phone2, email,
                 header_image_path, footer_image_path, logo_path)
    buffer.seek(0)

    filename = f"invoice_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buffer, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True)