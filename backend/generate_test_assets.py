import os
import json
import random
import re
import socket
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import fitz

# 1. Setup Directories
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Testing", "TestFiles"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Generating test files inside: {OUTPUT_DIR}")

# Seed random generators for repeatability
random.seed(42)

# Sample Pools
FIRST_NAMES = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Peter", "Quinn", "Ryan", "Sophia", "Thomas"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Jackson", "Thompson", "White"]
DEPARTMENTS = ["HR", "Engineering", "Sales", "Marketing", "Finance", "Legal", "Operations", "Product"]
PROJECTS = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Zeta", "Sigma", "Orion"]
DESIGNATIONS = ["Analyst", "Engineer", "Senior Engineer", "Manager", "Director", "VP", "Associate", "Specialist"]
STATUSES = ["Active", "On Leave", "Suspended", "Resigned"]

# Generate ~100 records datasets
records = []
for i in range(1, 101):
    emp_id = f"EMP{i:03d}"
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    dept = random.choice(DEPARTMENTS)
    email = f"{first.lower()}.{last.lower()}@enterprise.com"
    phone = f"+1-555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}"
    salary = random.choice([45000, 60000, 75000, 90000, 110000, 135000, 160000, 185000])
    
    # Introduce different date formats
    base_date = datetime(2018, 1, 1) + timedelta(days=random.randint(0, 3000))
    date_format_choice = random.choice(["iso", "slash", "str", "bad"])
    if date_format_choice == "iso":
        joining_date = base_date.strftime("%Y-%m-%d")
    elif date_format_choice == "slash":
        joining_date = base_date.strftime("%d/%m/%Y")
    elif date_format_choice == "str":
        joining_date = base_date.strftime("%b %d, %Y")
    else:
        # standard ISO for most fallback consistency, but some dirty format
        joining_date = base_date.strftime("%Y/%m/%d")
        
    manager = f"Manager {random.randint(1, 10)}"
    project = random.choice(PROJECTS)
    status = random.choice(STATUSES)
    
    records.append({
        "Employee ID": emp_id,
        "Employee Name": name,
        "Department": dept,
        "Email": email,
        "Phone": phone,
        "Salary": salary,
        "Joining Date": joining_date,
        "Manager": manager,
        "Project": project,
        "Status": status
    })

# Add duplicates
for _ in range(5):
    dup = random.choice(records).copy()
    records.append(dup)

# Add missing/NA records
for _ in range(5):
    nan_rec = random.choice(records).copy()
    nan_rec["Employee Name"] = None
    nan_rec["Salary"] = None
    nan_rec["Email"] = ""
    records.append(nan_rec)

# Let's shuffle
random.shuffle(records)

# ------------------------------------------------------------
# 1. employee_data.xlsx
# ------------------------------------------------------------
df_employees = pd.DataFrame(records)
# Setup sheets
df_depts = pd.DataFrame([
    {"Department": d, "Location": f"Building {random.choice(['A', 'B', 'C'])}", "Cost Center": f"CC-{random.randint(100, 999)}"}
    for d in DEPARTMENTS
])
df_projects = pd.DataFrame([
    {"Project": p, "Budget": random.randint(50000, 500000), "Lead": f"Lead {random.randint(1, 10)}"}
    for p in PROJECTS
])
df_attendance = pd.DataFrame([
    {"Employee ID": r["Employee ID"], "Days Present": random.randint(20, 22), "Leave Days": random.randint(0, 3)}
    for r in records if r["Employee ID"]
])
df_salary = pd.DataFrame([
    {"Employee ID": r["Employee ID"], "Base": r["Salary"], "Bonus": random.randint(1000, 10000) if r["Salary"] else None}
    for r in records if r["Employee ID"]
])

xlsx_path = os.path.join(OUTPUT_DIR, "employee_data.xlsx")
with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
    df_employees.to_excel(writer, sheet_name="Employees", index=False)
    df_depts.to_excel(writer, sheet_name="Departments", index=False)
    df_projects.to_excel(writer, sheet_name="Projects", index=False)
    df_attendance.to_excel(writer, sheet_name="Attendance", index=False)
    df_salary.to_excel(writer, sheet_name="Salary", index=False)
print("Generated employee_data.xlsx successfully.")

# ------------------------------------------------------------
# 2. employee_data.csv
# ------------------------------------------------------------
# Create slightly dirtier records for CSV
csv_records = []
for r in records:
    c_rec = r.copy()
    # add extra spaces, symbols, and casing
    if c_rec["Department"]:
        c_rec["Department"] = f"  {c_rec['Department'].lower()}  " if random.random() > 0.5 else c_rec["Department"]
    if c_rec["Salary"] is not None:
        c_rec["Salary"] = f"${c_rec['Salary']:,}" if random.random() > 0.5 else c_rec["Salary"]
    csv_records.append(c_rec)

df_csv = pd.DataFrame(csv_records)
csv_path = os.path.join(OUTPUT_DIR, "employee_data.csv")
df_csv.to_csv(csv_path, index=False, encoding="utf-8")
print("Generated employee_data.csv successfully.")

# ------------------------------------------------------------
# 3. employee_data.json
# ------------------------------------------------------------
company_json = {
    "company": "Enterprise Corp",
    "departments": df_depts.to_dict(orient="records"),
    "projects": df_projects.to_dict(orient="records"),
    "employees": df_employees.to_dict(orient="records"),
    "metadata": {
        "generated_at": datetime.now().isoformat(),
        "schema_version": "1.0"
    }
}
json_path = os.path.join(OUTPUT_DIR, "employee_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(company_json, f, indent=4)
print("Generated employee_data.json successfully.")

# ------------------------------------------------------------
# 4. employee_report.pdf (Digital PDF, ~4 pages)
# ------------------------------------------------------------
pdf_path = os.path.join(OUTPUT_DIR, "employee_report.pdf")
doc = fitz.open()

# Page 1: Cover
page1 = doc.new_page()
page1.insert_text((72, 100), "Enterprise Corp", fontsize=24, color=(0, 0, 0.5))
page1.insert_text((72, 140), "Annual Employee & Operations Report", fontsize=18)
page1.insert_text((72, 200), "Author: Enterprise Platform Team", fontsize=12)
page1.insert_text((72, 220), f"Date: {datetime.now().strftime('%Y-%m-%d')}", fontsize=12)
page1.insert_text((72, 300), "This report outlines company profile metrics, detailed employee demographics,\ndepartment assignments, salary distributions, and current active projects across\nthe enterprise organization structure.", fontsize=11)

# Page 2: Profile & Summary
page2 = doc.new_page()
page2.insert_text((72, 50), "Company Profile Summary", fontsize=16, color=(0, 0, 0.5))
page2.insert_text((72, 90), "Enterprise Corp operates globally with diverse business units across product development,\nsales, marketing, legal compliance, and customer success management.", fontsize=10)
page2.insert_text((72, 140), "Key Stats Summary:", fontsize=12)
y_offset = 160
stats_bullets = [
    "- Total Employees: ~100 Headcount",
    "- Central Offices: Building A, B, and C",
    "- Active Strategic Initiatives: Alpha, Beta, Delta, Gamma, Orion, Sigma",
    "- Financial Health: Growth of 12.4% year-over-year",
]
for bullet in stats_bullets:
    page2.insert_text((80, y_offset), bullet, fontsize=10)
    y_offset += 20

# Page 3: Tables & Details
page3 = doc.new_page()
page3.insert_text((72, 50), "Operational Departments Summary", fontsize=16, color=(0, 0, 0.5))
page3.insert_text((72, 80), "Departmental layout and budget cost centers mapped for the financial year:", fontsize=10)

# Draw simple table lines and headers
page3.draw_rect(fitz.Rect(72, 110, 500, 240), color=(0.7, 0.7, 0.7))
page3.draw_line(fitz.Point(72, 130), fitz.Point(500, 130), color=(0.7, 0.7, 0.7))
page3.insert_text((80, 122), "Department", fontsize=10)
page3.insert_text((220, 122), "Location", fontsize=10)
page3.insert_text((350, 122), "Cost Center", fontsize=10)

y_tbl = 145
for idx, d_rec in enumerate(DEPARTMENTS[:5]):
    loc = f"Building {random.choice(['A', 'B'])}"
    cc = f"CC-40{idx}"
    page3.insert_text((80, y_tbl), d_rec, fontsize=9)
    page3.insert_text((220, y_tbl), loc, fontsize=9)
    page3.insert_text((350, y_tbl), cc, fontsize=9)
    page3.draw_line(fitz.Point(72, y_tbl+5), fitz.Point(500, y_tbl+5), color=(0.9, 0.9, 0.9))
    y_tbl += 18

# Page 4: Strategic Projects Summary
page4 = doc.new_page()
page4.insert_text((72, 50), "Strategic Projects & Execution", fontsize=16, color=(0, 0, 0.5))
page4.insert_text((72, 80), "Enterprise Corp drives multiple strategic projects aimed at consolidating operations\nand implementing AI standard standardizations.", fontsize=10)

y_offset = 130
for p in PROJECTS[:4]:
    page4.insert_text((72, y_offset), f"Project {p}", fontsize=11)
    page4.insert_text((72, y_offset + 15), "Initiative to drive digital standardization and enhance record data governance.", fontsize=9)
    y_offset += 45

# Add page numbers to all pages
for i, page in enumerate(doc):
    page.insert_text((500, 750), f"Page {i+1} of 4", fontsize=9, color=(0.5, 0.5, 0.5))

doc.set_metadata({
    "title": "Employee Report",
    "author": "Enterprise Platform Team",
    "subject": "Enterprise Operations Summary",
    "keywords": "employee, report, summary, departments, projects"
})
doc.save(pdf_path)
doc.close()
print("Generated employee_report.pdf successfully.")

# ------------------------------------------------------------
# 5. employee_card.png (High quality png card for OCR testing)
# ------------------------------------------------------------
png_path = os.path.join(OUTPUT_DIR, "employee_card.png")
# Create high-res blank image
img = Image.new("RGB", (1920, 1080), color=(240, 240, 245))
draw = ImageDraw.Draw(img)

# Draw structured background borders
draw.rectangle([100, 100, 1820, 980], outline=(0, 51, 102), width=10, fill=(255, 255, 255))
draw.rectangle([120, 120, 1800, 250], fill=(0, 51, 102))

# Use simple fallback font drawings
try:
    # Try system fonts
    font_title = ImageFont.truetype("arial.ttf", 64)
    font_label = ImageFont.truetype("arial.ttf", 36)
    font_val = ImageFont.truetype("arial.ttf", 36)
    font_bold = ImageFont.truetype("arial.ttf", 44)
except Exception:
    # Default PIL font
    font_title = font_label = font_val = font_bold = ImageFont.load_default()

# Header
draw.text((150, 150), "ENTERPRISE CORP - IDENTITY CARD", fill=(255, 255, 255), font=font_title)

# Draw Logo Box Placeholder
draw.rectangle([200, 320, 500, 620], outline=(0, 51, 102), width=5, fill=(220, 230, 242))
draw.text((250, 450), "[LOGO]", fill=(0, 51, 102), font=font_bold)

# Employee ID, Name and Details ideal for OCR
fields = [
    ("Employee ID", "EMP088"),
    ("Full Name", "Johnathan Doe"),
    ("Department", "Engineering"),
    ("Designation", "Senior Systems Architect"),
    ("Email", "johnathan.doe@enterprise.com"),
    ("Phone", "+1-555-019-9234"),
    ("Office Address", "Suite 400, Building B, Enterprise HQ"),
    ("Issue Date", "2026-07-15")
]

x_lbl = 550
y_start = 320
for label, val in fields:
    draw.text((x_lbl, y_start), f"{label}:", fill=(80, 80, 80), font=font_label)
    draw.text((x_lbl + 350, y_start), val, fill=(0, 0, 0), font=font_val)
    y_start += 70

# Draw footer banner
draw.rectangle([120, 900, 1800, 960], fill=(220, 230, 242))
draw.text((150, 915), "If found, please return to Enterprise Corporate Security Dept.", fill=(0, 51, 102), font=font_label)

img.save(png_path)
print("Generated employee_card.png successfully.")

# ------------------------------------------------------------
# 6. scanned_invoice.pdf (Pure scanned page pdf to force OCR)
# ------------------------------------------------------------
invoice_pdf_path = os.path.join(OUTPUT_DIR, "scanned_invoice.pdf")

# Generate invoice page image
inv_img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
inv_draw = ImageDraw.Draw(inv_img)

try:
    font_inv_title = ImageFont.truetype("arial.ttf", 48)
    font_inv_header = ImageFont.truetype("arial.ttf", 28)
    font_inv_text = ImageFont.truetype("arial.ttf", 24)
except Exception:
    font_inv_title = font_inv_header = font_inv_text = ImageFont.load_default()

# Header
inv_draw.text((100, 100), "TAX INVOICE", fill=(0, 0, 0), font=font_inv_title)

# Invoice Metadata
inv_draw.text((100, 200), "Invoice Number: INV-2026-0988", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((100, 240), "Invoice Date: 2026-07-28", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((100, 280), "GST Registration: GSTIN9902671A", fill=(0, 0, 0), font=font_inv_text)

# Vendor & Customer
inv_draw.text((100, 360), "Vendor Details:", fill=(0, 0, 0), font=font_inv_header)
inv_draw.text((100, 400), "Enterprise Supplies Corp\n12 Logistics Hub, Ind Area\ncontact@suppliescorp.com", fill=(0, 0, 0), font=font_inv_text)

inv_draw.text((700, 360), "Customer Details:", fill=(0, 0, 0), font=font_inv_header)
inv_draw.text((700, 400), "Enterprise Corp Headquarters\nBuilding B, Suite 400\npayables@enterprise.com", fill=(0, 0, 0), font=font_inv_text)

# Items Table
inv_draw.rectangle([100, 550, 1140, 600], outline=(0, 0, 0), width=2)
inv_draw.text((120, 565), "Item Description", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((600, 565), "Qty", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((750, 565), "Unit Price", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((950, 565), "Total", fill=(0, 0, 0), font=font_inv_text)

y_row = 620
items = [
    ("Premium Enterprise Software License", "10", "$8,500.00", "$85,000.00"),
    ("Cloud Server Cluster Setup Maintenance", "1", "$12,450.00", "$12,450.00"),
    ("Standard Integration Support Hours", "25", "$150.00", "$3,750.00")
]

for desc, qty, unit, total in items:
    inv_draw.text((120, y_row), desc, fill=(0, 0, 0), font=font_inv_text)
    inv_draw.text((600, y_row), qty, fill=(0, 0, 0), font=font_inv_text)
    inv_draw.text((750, y_row), unit, fill=(0, 0, 0), font=font_inv_text)
    inv_draw.text((950, y_row), total, fill=(0, 0, 0), font=font_inv_text)
    inv_draw.line((100, y_row + 40, 1140, y_row + 40), fill=(200, 200, 200), width=1)
    y_row += 60

# Grand Total
inv_draw.rectangle([700, y_row + 40, 1140, y_row + 160], outline=(0, 0, 0), width=3)
inv_draw.text((720, y_row + 60), "Subtotal: $101,200.00", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((720, y_row + 100), "GST (18%): $18,216.00", fill=(0, 0, 0), font=font_inv_text)
inv_draw.text((720, y_row + 140), "Total Amount: $119,416.00", fill=(0, 0, 0), font=font_inv_header)

# Save as Image
temp_inv_img_path = os.path.join(OUTPUT_DIR, "temp_scanned_invoice.png")
inv_img.save(temp_inv_img_path)

# Convert Image into pure Scanned PDF (Forces OCR, no digital text)
doc_inv = fitz.open()
img_rect = fitz.Rect(0, 0, 595, 842) # standard page size A4
page_inv = doc_inv.new_page(width=595, height=842)
page_inv.insert_image(img_rect, filename=temp_inv_img_path)
doc_inv.save(invoice_pdf_path)
doc_inv.close()

# Cleanup temp png
if os.path.exists(temp_inv_img_path):
    os.remove(temp_inv_img_path)

print("Generated scanned_invoice.pdf successfully (Forces OCR).")

# ------------------------------------------------------------
# 7. corrupted.pdf (Broken format header)
# ------------------------------------------------------------
corrupt_path = os.path.join(OUTPUT_DIR, "corrupted.pdf")
with open(corrupt_path, "wb") as f:
    f.write(b"%PDF-1.4\n%invalid_pdf_data_bytes_and_broken_xref_offsets_binary_trash\n")
print("Generated corrupted.pdf successfully.")

# ------------------------------------------------------------
# 8. empty.txt
# ------------------------------------------------------------
empty_path = os.path.join(OUTPUT_DIR, "empty.txt")
with open(empty_path, "wb") as f:
    f.write(b"")
print("Generated empty.txt successfully.")

# ------------------------------------------------------------
# 9. duplicate_test.pdf (Copy of employee_report.pdf)
# ------------------------------------------------------------
dup_pdf_path = os.path.join(OUTPUT_DIR, "duplicate_test.pdf")
import shutil
shutil.copyfile(pdf_path, dup_pdf_path)
print("Generated duplicate_test.pdf successfully.")

# ------------------------------------------------------------
# 10. wrong_extension (Exe signature disguised as pdf)
# ------------------------------------------------------------
wrong_ext_path = os.path.join(OUTPUT_DIR, "wrong_extension.pdf")
with open(wrong_ext_path, "wb") as f:
    f.write(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00" + b"\x00" * 40 + b"This is a disguised executable PE signature payload structure.")
print("Generated wrong_extension.pdf (disguised EXE) successfully.")

print("All enterprise test files generated successfully.")
