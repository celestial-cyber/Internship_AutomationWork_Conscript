"""
Generate Women Story Word documents from the Excel sheet.

Input:
  women story new updated file 4Sept2026 (1).xlsx

Template:
  Entrepreneurial Mindset – Women Founders’ Advice - Part 52 sample.docx

Output:
  ./Women_Story_Word_Documents/<Category>/Part_<N>.docx

Install once:
  pip install pandas openpyxl python-docx
"""

from pathlib import Path
import re
import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ============================================================
# 1. FILES
# ============================================================

EXCEL_FILE = Path(r"women story new updated file 4Sept2026 (1).xlsx")
TEMPLATE_FILE = Path(
    r"Entrepreneurial Mindset – Women Founders’ Advice - Part 52 sample.docx"
)
OUTPUT_DIR = Path("Women_Story_Word_Documents")


# ============================================================
# 2. EXACT CATEGORY + PART LIST GIVEN BY HR
# ============================================================

CATEGORY_PARTS = {
    "Brand Development Techniques": [4, 5],
    "Building Long-Term Relationships": [7],
    "Business Strategy and Execution": list(range(18, 30)),
    "Effective Team Management": [9, 10],
    "Entrepreneurial Mindset": list(range(60, 80)),
    "Ethical - Value Business Practices": [7, 8, 9],
    "Gender Equality in Business": [7],
    "Goal Achievement": [11, 12, 13],
    "Innovation and Creativity": [10],
    "Learning from Failure": [6, 7],
    "Professional Networking Essentials": list(range(12, 18)),
    "Promoting Women's Empowerment": [8, 9],
    "Resilience and Persistence": list(range(45, 58)),
    "Self Development": list(range(31, 36)),
    "Starting a New Business": [10, 11],
    "Visionary Leadership": list(range(17, 26)),
}


# ============================================================
# 3. HELPERS
# ============================================================

def clean(value):
    """Return a clean string; blank/NA values become ''."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "na", "n/a"}:
        return ""
    return text


def safe_filename(text):
    """Make a Windows-safe and Zip-safe filename."""
    # Replace Unicode dashes with standard ASCII hyphen
    text = text.replace("–", "-").replace("—", "-")
    # Remove/replace curly quotes and curly apostrophes
    text = text.replace("’", "").replace("'", "").replace("“", "").replace("”", "")
    # Replace Windows prohibited characters with hyphens
    text = re.sub(r'[<>:"/\\|?*]', "-", text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip().rstrip(".")


def add_hyperlink(paragraph, text, url):
    """Add a clickable hyperlink to a Word paragraph."""
    if not url:
        return

    url = clean(url)
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url

    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    # Blue + underline, like a normal Word hyperlink.
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rPr.append(color)

    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rPr.append(underline)

    run.append(rPr)

    text_element = OxmlElement("w:t")
    text_element.text = text
    run.append(text_element)

    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_labeled_link(doc, label, value):
    """Add e.g. Website: clickable URL."""
    value = clean(value)
    if not value:
        return

    p = doc.add_paragraph()
    run = p.add_run(f"{label}: ")
    run.bold = True
    add_hyperlink(p, value, value)


def add_labeled_text(doc, label, value):
    """Add a simple labeled field."""
    value = clean(value)
    if not value:
        return

    p = doc.add_paragraph()
    run = p.add_run(f"{label}: ")
    run.bold = True
    p.add_run(value)


def clear_document_body(doc):
    """
    Remove the sample document's existing content but KEEP its styles,
    margins, page setup, and other document-level formatting.
    """
    body = doc._element.body

    for child in list(body):
        # Keep section properties; remove paragraphs/tables/etc.
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def make_title(doc, category, part):
    title = f"{category} – Women Founders’ Advice - Part {part}"
    p = doc.add_paragraph(style="Heading 1")
    p.add_run(title)
    return title


def make_featured_section(doc, rows):
    """
    Match the sample's overall structure:
      Featured Women Founders
      Founder 1 – Advice Summary
      Founder 2 – Advice Summary
      ...
    """
    doc.add_paragraph("Featured Women Founders", style="Heading 2")

    for _, row in rows.iterrows():
        founder = clean(row["Founder Name"])
        summary = clean(row["Advice Summary"])

        if not founder:
            continue

        text = founder
        if summary:
            text += f"  {summary}"

        doc.add_paragraph(text)


def add_founder_section(doc, row):
    founder = clean(row["Founder Name"])
    company = clean(row["Company Name"])
    website = clean(row["Website"])
    linkedin = clean(row["SocialMedia"])
    advice = clean(row["Original Advice"])
    summary = clean(row["Advice Summary"])
    blog_link = clean(row["Blog LINK"])

    # Founder heading
    heading_text = founder
    if summary:
        heading_text += f" – {summary}"

    doc.add_paragraph(heading_text, style="Heading 3")

    # Company
    if company:
        p = doc.add_paragraph()
        p.add_run("Founder – ").bold = False
        p.add_run(company)

    # Website / LinkedIn / source article
    add_labeled_link(doc, "Website", website)
    add_labeled_link(doc, "LinkedIn", linkedin)
    add_labeled_link(doc, "Source Article", blog_link)

    # Advice
    if advice:
        p = doc.add_paragraph()
        p.add_run("Advice").bold = True

        # Preserve line breaks from Excel.
        for block in re.split(r"\n\s*\n", advice):
            block = block.strip()
            if not block:
                continue

            # If the Excel advice contains separate lines, preserve them.
            lines = [x.strip() for x in block.splitlines() if x.strip()]
            if len(lines) <= 1:
                doc.add_paragraph(block)
            else:
                for line in lines:
                    doc.add_paragraph(line)

    doc.add_paragraph("")


# ============================================================
# 4. READ EXCEL
# ============================================================

if not EXCEL_FILE.exists():
    raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE.resolve()}")

if not TEMPLATE_FILE.exists():
    raise FileNotFoundError(f"Template file not found: {TEMPLATE_FILE.resolve()}")

df = pd.read_excel(EXCEL_FILE, sheet_name="2026 Advice Analysis")

# Rename Excel columns to easy internal names.
required_columns = {
    "Founder Name": "Founder Name",
    "Business Name": "Company Name",
    "Website": "Website",
    "SocialMedia": "SocialMedia",
    "Original Advice": "Original Advice",
    "Advice Summary": "Advice Summary",
    "Category / Master Tag": "Category",
    "Category Number / Part": "Part",
    "Website Heading": "Website Heading",
    "Blog LINK": "Blog LINK",
}

missing = [c for c in required_columns if c not in df.columns]
if missing:
    raise ValueError(
        "These expected Excel columns were not found:\n"
        + "\n".join(f" - {c}" for c in missing)
    )

df = df.rename(columns=required_columns)

# Normalize category and part values.
df["Category"] = df["Category"].map(clean)
df["Part"] = pd.to_numeric(df["Part"], errors="coerce")

# Remove rows with no founder.
df = df[df["Founder Name"].map(clean) != ""].copy()


# ============================================================
# 5. GENERATE ALL REQUESTED WORD FILES
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

created = []
empty_groups = []

for category, parts in CATEGORY_PARTS.items():

    category_dir = OUTPUT_DIR / safe_filename(category)
    category_dir.mkdir(parents=True, exist_ok=True)

    for part in parts:

        # IMPORTANT:
        # One Word document = one Category + one Part.
        group = df[
            (df["Category"].str.casefold() == category.casefold())
            & (df["Part"] == part)
        ].copy()

        # Keep Excel order.
        group = group.reset_index(drop=True)

        if group.empty:
            empty_groups.append((category, part))
            continue

        # Start from the provided sample so its Word styles/layout are retained.
        doc = Document(TEMPLATE_FILE)
        clear_document_body(doc)

        make_title(doc, category, part)

        # No invented article introduction:
        # the document is built directly from the Excel source data.
        make_featured_section(doc, group)

        for _, row in group.iterrows():
            add_founder_section(doc, row)

        filename = safe_filename(
            f"{category} - Women Founders Advice Part {part}.docx"
        )
        output_file = category_dir / filename

        doc.save(output_file)
        created.append(output_file)


# ============================================================
# 6. REPORT
# ============================================================

print("=" * 70)
print("DONE")
print("=" * 70)
print(f"Documents created: {len(created)}")
print(f"Output folder: {OUTPUT_DIR.resolve()}")

if empty_groups:
    print("\nIMPORTANT — These requested Category + Part combinations had")
    print("no matching rows in the Excel and were NOT created:")
    for category, part in empty_groups:
        print(f"  - {category} | Part {part}")

print("\nCreated files:")
for path in created:
    print(f"  - {path}")