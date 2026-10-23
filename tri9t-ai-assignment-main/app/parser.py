
import hashlib
import json
import re
import uuid
from pathlib import Path

from pypdf import PdfReader


# These are the actual major headings in the CT-200 manual.
# This prevents numbered clinical list items from becoming sections.
MAJOR_HEADINGS = {
    "Device Overview",
    "Physical and Electrical Specifications",
    "Device Operation",
    "Alarms and Safety Behavior",
    "Data Management",
    "Maintenance and Cleaning",
    "Troubleshooting",
    "Regulatory Information",
}

LIST_ITEM_START = re.compile(r"^\s*\d+\.\s+")

HEADING_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$"
)


def normalize_text(text):
    """Normalize whitespace and common PDF ligature artifacts."""
    text = text.replace("\ufb01", "fi")
    text = text.replace("\ufb02", "fl")
    text = text.replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text):
    """Return a stable SHA-256 hash of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_lines(pdf_path):
    """Extract text line by line, retaining source page numbers."""
    reader = PdfReader(str(pdf_path))
    lines = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""

        for line in page_text.splitlines():
            line = normalize_text(line)
            if line:
                lines.append({
                    "page": page_number,
                    "text": line,
                })

    return lines


def identify_heading(line, current_heading=None):
    """Identify CT-200 headings without misclassifying list items."""
    text = line.strip()
    match = HEADING_PATTERN.match(text)

    if not match:
        return None

    number, title = match.groups()
    title = title.strip()

    # Main sections are restricted to the known CT-200 headings.
    if "." not in number:
        if title in MAJOR_HEADINGS:
            return {
                "number": number,
                "title": title,
                "level": 1,
            }

        return None

    # Clinical classification entries are numbered lists, not sections.
    if current_heading == "3.3" and LIST_ITEM_START.match(text):
        return None

    return {
        "number": number,
        "title": title,
        "level": number.count(".") + 1,
    }


def parse_pdf(pdf_path):
    """Build a hierarchy while preserving PDF reading order."""
    lines = extract_lines(pdf_path)

    root = {
        "id": str(uuid.uuid4()),
        "heading": "CardioTrack CT-200 Manual",
        "section_number": None,
        "level": 0,
        "body_text": "",
        "content_hash": content_hash(""),
        "page_start": 1,
        "page_end": len(PdfReader(str(pdf_path)).pages),
        "children": [],
    }

    # Keep an index of section paths already encountered.
    nodes_by_number = {}
    current_node = root
    current_section_number = None

    for item in lines:
        text = item["text"]
        heading = identify_heading(text, current_section_number)

        if heading:
            number = heading["number"]
            level = heading["level"]

            # Use the nearest existing numbered ancestor.
            parent = root
            parts = number.split(".")

            for i in range(len(parts) - 1, 0, -1):
                ancestor = ".".join(parts[:i])
                if ancestor in nodes_by_number:
                    parent = nodes_by_number[ancestor]
                    break

            node = {
                "id": str(uuid.uuid4()),
                "section_number": number,
                "heading": heading["title"],
                "level": level,
                "body_text": "",
                "content_hash": content_hash(""),
                "page_start": item["page"],
                "page_end": item["page"],
                "children": [],
            }

            parent["children"].append(node)

            # Repeated section numbers remain separate nodes in the tree.
            # Only the first is used as an ancestor lookup target.
            nodes_by_number.setdefault(number, node)

            current_node = node
            current_section_number = number
            continue

        # Keep all non-heading text attached to the current section.
        current_node["body_text"] += (
            ("\n" if current_node["body_text"] else "") + text
        )
        current_node["page_end"] = item["page"]

    def finalize(node):
        node["body_text"] = normalize_text(node["body_text"])
        node["content_hash"] = content_hash(
            node["heading"] + "\n" + node["body_text"]
        )

        for child in node["children"]:
            finalize(child)

    finalize(root)
    return root


def main():
    import sys

    if len(sys.argv) != 3:
        print(
            "Usage: python app/parser.py INPUT.pdf OUTPUT.json"
        )
        raise SystemExit(1)

    tree = parse_pdf(Path(sys.argv[1]))
    output_path = Path(sys.argv[2])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(tree, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Parsed document saved to {output_path}")


if __name__ == "__main__":
    main()
