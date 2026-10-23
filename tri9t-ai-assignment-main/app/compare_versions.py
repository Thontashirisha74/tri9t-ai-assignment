
from database import SessionLocal, Document, SectionNode
from ingest import compare_versions

session = SessionLocal()

try:
    document = session.query(Document).filter_by(
        name="CardioTrack CT-200 Manual"
    ).one()

    changes = compare_versions(
        session,
        document.id,
        old_number=1,
        new_number=2,
    )

    counts = {
        "added": 0,
        "changed": 0,
        "removed": 0,
        "unchanged": 0,
    }

    for item in changes:
        counts[item["status"]] += 1

    print("\n=== V1 vs V2 CHANGE SUMMARY ===")
    for status, count in counts.items():
        print(f"{status.title()}: {count}")

    print("\n=== SECTION CHANGES ===")
    for item in changes:
        if item["status"] != "unchanged":
            print(
                f"[{item['status'].upper()}] "
                f"{item['section_number'] or 'Root'} "
                f"- {item['heading']}"
            )

finally:
    session.close()
