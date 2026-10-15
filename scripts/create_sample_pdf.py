#!/usr/bin/env python3
"""Generate a clean sample clinical guidelines PDF for testing local document RAG."""

from __future__ import annotations

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
docs_dir = project_root / "data" / "documents"


def create_minimal_pdf(output_path: Path, title: str, pages_content: list[str]) -> None:
    """Create a multi-page PDF using standard PDF specification."""
    # Build standard PDF structures
    objects = []
    # 1: Catalog
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    # 2: Pages root (will update kids)
    page_obj_ids = []
    
    # Text streams for pages
    content_obj_ids = []
    font_id = len(pages_content) * 2 + 3

    for idx, content in enumerate(pages_content):
        p_id = 3 + idx * 2
        c_id = p_id + 1
        page_obj_ids.append(p_id)
        content_obj_ids.append(c_id)

    # 2 0 obj: Pages
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {len(pages_content)} >>")

    for idx, (p_id, c_id, content) in enumerate(zip(page_obj_ids, content_obj_ids, pages_content)):
        # Page object
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {c_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        )
        # Content stream
        # Escape parenthesis
        lines = content.split("\n")
        stream_ops = ["BT", "/F1 12 Tf", "50 720 Td", "14 TL"]
        for line in lines:
            safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_ops.append(f"({safe_line}) '")
        stream_ops.append("ET")
        stream_data = "\n".join(stream_ops)
        stream_bytes = stream_data.encode("latin1", errors="replace")
        objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n{stream_data}\nendstream")

    # Font object
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Write PDF file with cross-reference table
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        offsets = []
        for i, obj in enumerate(objects, 1):
            offsets.append(f.tell())
            f.write(f"{i} 0 obj\n{obj}\nendobj\n".encode("latin1"))

        xref_start = f.tell()
        f.write(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
        f.write(b"0000000000 65535 f \n")
        for offset in offsets:
            f.write(f"{offset:010d} 00000 n \n".encode("latin1"))

        f.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
                "latin1"
            )
        )


def main() -> None:
    pdf_path = docs_dir / "Clinical_Guidelines_Respiratory_Fever.pdf"
    print(f"Creating sample medical document at {pdf_path}...")

    page_1 = """Clinical Practice Guidelines: Acute Fever and Cough Management
Section 1: Initial Assessment and Patient Triage

Acute fever (defined as body temperature greater than 38.0 C or 100.4 F) accompanied by acute onset cough is a common presentation in primary healthcare.

Key Assessment Steps:
1. Duration of symptoms: Inquire whether symptoms started acutely (within last 24-48 hours) or have been progressive over weeks.
2. Vital signs: Check respiratory rate, oxygen saturation (SpO2), heart rate, and blood pressure.
3. Red Flag Symptoms: Shortness of breath, chest pain, coughing up blood (hemoptysis), confusion, or persistent high fever greater than 39.5 C require urgent hospital evaluation.

Common Causes:
- Acute viral upper respiratory tract infections (common cold, influenza, seasonal viral fever).
- Acute bronchitis or early respiratory tract infection.
- Vector-borne illnesses in endemic areas (such as Dengue or Malaria) when high fever is accompanied by severe body aches."""

    page_2 = """Clinical Practice Guidelines: Acute Fever and Cough Management
Section 2: Evidence-Based Home Care and Supportive Measures

For mild to moderate cases without emergency red flags:
1. Hydration: Maintain adequate oral fluid intake (warm water, broths, electrolyte fluids) to prevent dehydration and soothe throat irritation.
2. Rest: Adequate physical rest is crucial to allow the immune response to fight infection.
3. Antipyretics: Paracetamol (acetaminophen) may be used according to physician guidance for fever and headache relief. Avoid aspirin in children and teenagers.
4. Steam Inhalation and Saline Gargles: Helpful for relieving nasal congestion and soothing upper airway irritation.
5. Monitoring: Monitor temperature twice daily and watch for worsening respiratory symptoms.

Section 3: When to Seek Immediate Medical Attention
Patients should consult a doctor if:
- Fever persists for more than 3 consecutive days.
- Difficulty breathing or wheezing develops.
- Severe weakness, persistent vomiting, or inability to keep fluids down occurs."""

    create_minimal_pdf(
        output_path=pdf_path,
        title="Clinical Guidelines - Respiratory & Fever",
        pages_content=[page_1, page_2],
    )
    print(f"Successfully generated 2-page sample medical PDF: {pdf_path.name}")


if __name__ == "__main__":
    main()
