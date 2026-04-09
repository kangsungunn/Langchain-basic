# -*- coding: utf-8 -*-
"""Extract first N pages from first PDF in civil_procedure for structure inspection."""
from pathlib import Path
import sys

project = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project))

base = project / "data" / "raw" / "civil_procedure"
pdfs = list(base.glob("*.pdf"))
if not pdfs:
    print("No PDF found in", base)
    sys.exit(1)

pdf_path = pdfs[0]
print("Using:", pdf_path.name)

try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        full = []
        n = min(30, len(pdf.pages))
        for i in range(n):
            t = pdf.pages[i].extract_text()
            if t:
                full.append("--- PAGE %d ---\n%s" % (i + 1, t))
        text = "\n\n".join(full)
except Exception as e:
    print("pdfplumber:", e)
    import pypdf
    r = pypdf.PdfReader(open(pdf_path, "rb"))
    full = []
    n = min(30, len(r.pages))
    for i in range(n):
        t = r.pages[i].extract_text()
        if t:
            full.append("--- PAGE %d ---\n%s" % (i + 1, t))
    text = "\n\n".join(full)

out = base / "raw_sample_gy.txt"
out.write_text(text, encoding="utf-8")
print("Wrote", out, "chars=", len(text))
