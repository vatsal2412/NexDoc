"""Generates a Procurement Dataset for evaluation."""

import os
from pathlib import Path
from openpyxl import Workbook
import fitz
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("dataset/procurement")

def _ensure_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def build_budget():
    wb = Workbook()
    ws = wb.active
    ws.title = "Budget"
    ws.append(["Department", "Category", "Approved Budget"])
    ws.append(["IT", "Software", 50000])
    ws.append(["IT", "Hardware", 100000])
    wb.save(OUT_DIR / "budget.xlsx")

def build_vendor_master():
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendors"
    ws.append(["Vendor ID", "Vendor Name", "Status"])
    ws.append(["V102", "Acme Corp", "Approved"])
    ws.append(["V103", "Globex", "Pending"])
    wb.save(OUT_DIR / "vendor_master.xlsx")

def build_invoice_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    p = OUT_DIR / "invoice.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.drawString(72, 800, "INVOICE")
    c.drawString(72, 780, "Vendor ID: V102")
    c.drawString(72, 760, "Invoice Total: $25,000")
    c.save()

def build_po_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    p = OUT_DIR / "purchase_order.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.drawString(72, 800, "PURCHASE ORDER")
    c.drawString(72, 780, "Vendor ID: V102")
    c.drawString(72, 760, "PO Amount: $25,000")
    c.save()

def build_approval_flow():
    image = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        
    draw.rectangle([50, 50, 200, 100], outline="black", width=2)
    draw.text((60, 60), "Submit PO (V102)", fill="black", font=font)
    
    draw.rectangle([250, 50, 400, 100], outline="black", width=2)
    draw.text((260, 60), "Check Budget", fill="black", font=font)
    
    draw.rectangle([450, 50, 550, 100], outline="black", width=2)
    draw.text((460, 60), "Approved", fill="black", font=font)
    
    # Draw simple lines (Hough transforms in adapter might not catch this easily if not perfect, but it's a mock)
    draw.line([200, 75, 250, 75], fill="black", width=2)
    draw.line([400, 75, 450, 75], fill="black", width=2)

    image.save(OUT_DIR / "approval_flow.png")

if __name__ == "__main__":
    _ensure_dir()
    build_budget()
    build_vendor_master()
    build_invoice_pdf()
    build_po_pdf()
    build_approval_flow()
    print("Dataset generated at dataset/procurement/")
