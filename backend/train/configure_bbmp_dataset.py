"""
CivicLens — BBMP Grievances Dataset Ingestion & Configuration Pipeline
Dataset: BBMP (Bengaluru Smart City / Sahaaya 2.0 Citizen Grievances)
Source: OpenCity / Bengaluru Smart City Limited Portal

This script:
  1. Downloads `citizen-grievances.csv.gz` (28.8 MB compressed, ~100k real municipal complaints).
  2. Maps BBMP municipal categories and subcategories to CivicLens 8-class taxonomy.
  3. Formulates natural complaint text from grievance descriptors, locations, and remarks.
  4. Runs Stage 1 Preprocessing and extracts independent incident attributes:
     - severity (1-5)
     - immediate_risk (0 or 1)
     - public_exposure (1-5)
     - ongoing_incident (0 or 1)
     - urgency_claim (0 or 1)
  5. Saves a clean, structured training dataset: `data/dataset_bbmp_train.csv`.
"""
import os
import gzip
import csv
import re
import httpx
from pathlib import Path
from typing import Dict, Any, Optional

BBMP_URL = "https://raw.githubusercontent.com/Vonter/bbmp-citizen-grievances/main/data/citizen-grievances.csv.gz"
RAW_GZ_PATH = "data/bbmp_citizen_grievances.csv.gz"
OUTPUT_CSV = "data/dataset_bbmp_train.csv"

# ---------------------------------------------------------------------------
# Category & Subcategory Taxonomy Mapping: BBMP -> CivicLens
# ---------------------------------------------------------------------------
CATEGORY_MAPPING = {
    # BBMP category keywords -> CivicLens Primary Category
    "road": "Infrastructure & Roads",
    "pothole": "Infrastructure & Roads",
    "footpath": "Infrastructure & Roads",
    "traffic": "Traffic & Road Safety",
    "street light": "Electricity & Street Lighting",
    "electrical": "Electricity & Street Lighting",
    "solid waste": "Sanitation & Waste Management",
    "garbage": "Sanitation & Waste Management",
    "storm water": "Water Supply & Drainage",
    "drain": "Water Supply & Drainage",
    "health": "Public Health & Environment",
    "animal": "Public Health & Environment",
    "mosquito": "Public Health & Environment",
    "building": "Building Safety",
    "encroachment": "Infrastructure & Roads",
    "parks": "Parks & Public Spaces",
    "horticulture": "Parks & Public Spaces",
    "tree": "Parks & Public Spaces",
}

SUBCATEGORY_MAPPING = {
    "pothole": "Pothole / Road Damage",
    "road repair": "Pothole / Road Damage",
    "broken footpath": "Broken Footpath",
    "footpath": "Broken Footpath",
    "street light not working": "Streetlight Failure",
    "street light": "Streetlight Failure",
    "cable": "Exposed / Live Wire",
    "wire": "Exposed / Live Wire",
    "garbage dump": "Garbage Pileup",
    "waste collection": "Missed Waste Collection",
    "overflowing drain": "Sewage Overflow",
    "blocked drain": "Drain Blockage",
    "water logging": "Flooding / Waterlogging",
    "mosquito": "Mosquito Breeding / Dengue Risk",
    "stray dog": "Stray Animal Attack",
    "fallen tree": "Fallen Tree",
    "park maintenance": "Poor Maintenance",
    "unsafe building": "Unsafe / Collapsing Structure",
}


def map_bbmp_category(cat: str, subcat: str) -> tuple[str, str]:
    combined = f"{cat} {subcat}".lower()

    # Determine primary category
    matched_cat = "Infrastructure & Roads"  # fallback default
    for kw, target_cat in CATEGORY_MAPPING.items():
        if kw in combined:
            matched_cat = target_cat
            break

    # Determine subcategory
    matched_sub = "General Maintenance"
    for kw, target_sub in SUBCATEGORY_MAPPING.items():
        if kw in combined:
            matched_sub = target_sub
            break

    return matched_cat, matched_sub


def extract_attributes_from_text(text: str) -> Dict[str, Any]:
    lower = text.lower()

    # Severity (1 to 5)
    severity = 2
    if any(k in lower for k in ["fatal", "danger", "hazard", "severe", "life", "deep crater", "heavy waterlogging"]):
        severity = 4
    elif any(k in lower for k in ["bad", "huge", "urgent", "overflow", "damage", "broken"]):
        severity = 3
    elif any(k in lower for k in ["minor", "small", "cleaning required"]):
        severity = 1

    # Immediate Risk (0 or 1)
    immediate_risk = 1 if any(k in lower for k in ["accident", "spark", "shock", "collapse", "risk", "danger", "fall", "injury"]) else 0

    # Public Exposure (1 to 5)
    exposure = 3
    if any(k in lower for k in ["main road", "junction", "school", "hospital", "bus stop", "market", "metro"]):
        exposure = 4
    elif any(k in lower for k in ["cross", "lane", "residential"]):
        exposure = 2

    # Ongoing Incident (0 or 1)
    ongoing = 0 if any(k in lower for k in ["resolved", "closed", "fixed", "completed"]) else 1

    # Explicit Urgency (0 or 1, citizen subjective claim)
    urgency_claim = 1 if any(k in lower for k in ["immediately", "urgent", "asap", "jaldi", "please clear", "request immediate"]) else 0

    return {
        "severity": severity,
        "immediate_risk": immediate_risk,
        "public_exposure": exposure,
        "ongoing_incident": ongoing,
        "urgency_claim": urgency_claim,
    }


def download_bbmp_dataset(dest_path: str):
    print(f"Downloading BBMP dataset from: {BBMP_URL}")
    with httpx.stream("GET", BBMP_URL, follow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            downloaded = 0
            for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                print(f"Downloaded {downloaded / (1024 * 1024):.1f} MB...", end="\r")
    print(f"\nDownload completed: {dest_path}")


def process_bbmp_to_civiclens(gz_path: str, output_csv: str, target_count: int = 15000):
    print(f"Processing BBMP records from {gz_path} into CivicLens schema (target: {target_count} records)...")
    processed_records = []
    seen_texts = set()

    with gzip.open(gz_path, mode="rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            bbmp_cat = (row.get("Category") or "").strip()
            bbmp_subcat = (row.get("Sub Category") or "").strip()
            ward = (row.get("Ward Name") or "").strip()
            remarks = (row.get("Staff Remarks") or "").strip()
            complaint_id = (row.get("Complaint ID") or f"BBMP_{i+1}").strip()

            if not bbmp_cat and not bbmp_subcat:
                continue

            # Build natural complaint text
            parts = []
            if bbmp_subcat:
                parts.append(f"{bbmp_subcat} reported")
            if ward:
                parts.append(f"in {ward}")
            if remarks and len(remarks) > 3 and not remarks.lower().startswith("work attended"):
                parts.append(f"Details: {remarks}")

            complaint_text = ". ".join(parts).strip()
            if not complaint_text or len(complaint_text) < 10 or complaint_text in seen_texts:
                continue

            seen_texts.add(complaint_text)

            cat, subcat = map_bbmp_category(bbmp_cat, bbmp_subcat)
            attrs = extract_attributes_from_text(complaint_text)

            record = {
                "complaint_id": complaint_id,
                "complaint_text": complaint_text,
                "language": "en",
                "category": cat,
                "subcategory": subcat,
                "severity": attrs["severity"],
                "immediate_risk": attrs["immediate_risk"],
                "public_exposure": attrs["public_exposure"],
                "ongoing_incident": attrs["ongoing_incident"],
                "urgency_claim": attrs["urgency_claim"],
                "ward": ward,
            }
            processed_records.append(record)

            if len(processed_records) >= target_count:
                break

    print(f"Processed {len(processed_records)} unique civic grievances.")

    # Write output CSV
    fieldnames = [
        "complaint_id", "complaint_text", "language", "category",
        "subcategory", "severity", "immediate_risk", "public_exposure",
        "ongoing_incident", "urgency_claim", "ward"
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_records)

    print(f"✅ Successfully written to {output_csv}")

    # Summary of categories
    from collections import Counter
    cat_counts = Counter(r["category"] for r in processed_records)
    print("\nCivicLens Category Distribution:")
    for c, cnt in cat_counts.most_common():
        print(f"  - {c}: {cnt}")


def main():
    Path("data").mkdir(exist_ok=True)
    if not os.path.exists(RAW_GZ_PATH):
        download_bbmp_dataset(RAW_GZ_PATH)
    else:
        print(f"Existing raw archive found at {RAW_GZ_PATH}, skipping download.")

    process_bbmp_to_civiclens(RAW_GZ_PATH, OUTPUT_CSV, target_count=10000)


if __name__ == "__main__":
    main()

