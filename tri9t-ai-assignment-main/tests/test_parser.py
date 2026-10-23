
import json
import subprocess
import sys
from pathlib import Path

from app.parser import parse_pdf


ROOT = Path(__file__).resolve().parents[1]
V1_PDF = ROOT / "data" / "ct200_manual.pdf"


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def find_section(tree, number):
    return next(
        node for node in walk(tree)
        if node.get("section_number") == number
    )


def find_parent(tree, child):
    return next(
        (
            node for node in walk(tree)
            if child in node.get("children", [])
        ),
        None,
    )


def test_deep_heading_uses_nearest_existing_ancestor():
    tree = parse_pdf(V1_PDF)

    battery = find_section(tree, "2.1.1.1")
    parent = find_parent(tree, battery)

    assert parent is not None
    assert parent["section_number"] == "2.1"


def test_classification_list_stays_inside_section_3_3():
    tree = parse_pdf(V1_PDF)

    section = find_section(tree, "3.3")
    body = section["body_text"]

    assert "Normal:" in body
    assert "Elevated:" in body
    assert "Hypertension Stage 1:" in body
    assert "Hypertension Stage 2:" in body
    assert "Hypertensive Crisis:" in body

    # Numbered clinical classifications are not section nodes.
    assert not any(
        node.get("section_number") in {"1", "2", "3", "4", "5"}
        and node.get("heading", "").startswith(
            ("Normal:", "Elevated:", "Hypertension")
        )
        for node in walk(tree)
    )


def test_same_heading_title_has_distinct_section_nodes():
    tree = parse_pdf(V1_PDF)

    error_sections = [
        node for node in walk(tree)
        if node.get("heading") == "Error Codes"
    ]

    assert len(error_sections) == 2
    assert {
        node["section_number"] for node in error_sections
    } == {"4.2", "7.1"}

    assert len({
        node["id"] for node in error_sections
    }) == 2


def test_all_node_ids_are_unique():
    tree = parse_pdf(V1_PDF)
    ids = [node["id"] for node in walk(tree)]

    assert len(ids) == len(set(ids))
