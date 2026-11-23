"""
CivicLens — Master Multi-Dataset Downloader & Configurator
Downloads and configures the top 3 primary civic complaint datasets:
  1. BBMP Grievances (Bengaluru, India) — Real municipal grievance data
  2. NYC 311 Service Requests (OpenData) — Municipal service requests
  3. CPGRAMS Indian Public Grievances — Real & pan-India multilingual grievances
  Bonus: COMI-LINGUA — Hinglish code-mixed normalisation data

Outputs:
  - data/dataset_bbmp_train.csv
  - data/dataset_nyc311_train.csv
  - data/dataset_cpgrams_train.csv
  - data/dataset_comilingua_hinglish.csv
  - data/dataset_civiclens_master_hybrid.csv  (Merged Master Training Set)
"""
import os
import csv
import io
import re
import httpx
from pathlib import Path
from typing import Dict, Any, List

Path("data").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Attribute Extractor Engine (Deterministic Factual Labels)
# ---------------------------------------------------------------------------
def extract_attributes(text: str) -> Dict[str, Any]:
    lower = text.lower()

    # Severity (1-5)
    severity = 2
    if any(k in lower for k in ["fatal", "danger", "electrocution", "severe", "collapse", "life threatening", "deep crater", "heavy flood"]):
        severity = 4
    elif any(k in lower for k in ["huge", "overflow", "damage", "broken", "leakage", "urgent", "major"]):
        severity = 3
    elif any(k in lower for k in ["minor", "small", "cleaning required", "slow"]):
        severity = 1

    # Immediate Risk (0 or 1)
    immediate_risk = 1 if any(k in lower for k in ["accident", "spark", "shock", "collapse", "risk", "hazard", "injury", "danger"]) else 0

    # Public Exposure (1-5)
    exposure = 3
    if any(k in lower for k in ["main road", "junction", "school", "hospital", "bus stop", "market", "metro", "highway"]):
        exposure = 4
    elif any(k in lower for k in ["lane", "cross", "alley", "residential", "apartment"]):
        exposure = 2

    # Ongoing Incident (0 or 1)
    ongoing = 0 if any(k in lower for k in ["resolved", "closed", "fixed", "completed", "attended"]) else 1

    # Urgency Claim (0 or 1 — citizen subjective claim, audit only)
    urgency_claim = 1 if any(k in lower for k in ["urgent", "urgently", "immediately", "asap", "jaldi", "please help", "request immediate"]) else 0

    return {
        "severity": severity,
        "immediate_risk": immediate_risk,
        "public_exposure": exposure,
        "ongoing_incident": ongoing,
        "urgency_claim": urgency_claim,
    }


# ===========================================================================
# 1. NYC 311 Service Requests Downloader
# ===========================================================================
NYC_CATEGORY_MAP = {
    "Pothole": ("Infrastructure & Roads", "Pothole / Road Damage"),
    "Street Condition": ("Infrastructure & Roads", "Pothole / Road Damage"),
    "Sidewalk Condition": ("Infrastructure & Roads", "Broken Footpath"),
    "Bridge Condition": ("Infrastructure & Roads", "Bridge Damage"),
    "Street Light Condition": ("Electricity & Street Lighting", "Streetlight Failure"),
    "Traffic Signal Condition": ("Traffic & Road Safety", "Signal Failure"),
    "Blocked Driveway": ("Traffic & Road Safety", "Illegal Parking Obstruction"),
    "Illegal Parking": ("Traffic & Road Safety", "Illegal Parking Obstruction"),
    "Water System": ("Water Supply & Drainage", "Pipeline Leakage"),
    "Sewer": ("Water Supply & Drainage", "Sewage Overflow"),
    "Water Leak": ("Water Supply & Drainage", "Pipeline Leakage"),
    "Sanitation Condition": ("Sanitation & Waste Management", "Garbage Pileup"),
    "Dirty Condition": ("Sanitation & Waste Management", "Garbage Pileup"),
    "Missed Collection": ("Sanitation & Waste Management", "Missed Waste Collection"),
    "Rodent": ("Public Health & Environment", "Mosquito Breeding / Dengue Risk"),
    "Air Quality": ("Public Health & Environment", "Air / Noise Pollution"),
    "Noise": ("Public Health & Environment", "Air / Noise Pollution"),
    "Building/Use": ("Building Safety", "Unsafe / Collapsing Structure"),
    "Damaged Tree": ("Parks & Public Spaces", "Fallen Tree"),
    "Maintenance or Facility": ("Parks & Public Spaces", "Poor Maintenance"),
}

def download_and_configure_nyc311(output_path: str = "data/dataset_nyc311_train.csv", limit: int = 5000):
    print(f"\n[1/3] Downloading NYC 311 Service Requests (target: {limit} records)...")
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    records = []

    try:
        # Fetch in batches of 1000
        for offset in range(0, limit, 1000):
            batch_limit = min(1000, limit - offset)
            params = {"$limit": batch_limit, "$offset": offset}
            r = httpx.get(url, params=params, timeout=20)
            if r.status_code != 200:
                print(f"  NYC 311 batch error at offset {offset}: {r.status_code}")
                break
            batch = r.json()
            if not batch:
                break

            for row in batch:
                c_type = (row.get("complaint_type") or "").strip()
                desc = (row.get("descriptor") or "").strip()
                address = (row.get("incident_address") or row.get("street_name") or "").strip()
                borough = (row.get("borough") or "").strip()
                unique_key = (row.get("unique_key") or f"NYC_{len(records)+1}").strip()

                if not c_type:
                    continue

                # Map to CivicLens taxonomy
                cat = "Infrastructure & Roads"
                subcat = "General Maintenance"
                for key, (mapped_c, mapped_s) in NYC_CATEGORY_MAP.items():
                    if key.lower() in c_type.lower() or key.lower() in desc.lower():
                        cat = mapped_c
                        subcat = mapped_s
                        break

                text_parts = [c_type]
                if desc:
                    text_parts.append(desc)
                if address:
                    text_parts.append(f"near {address}")
                if borough and borough != "Unspecified":
                    text_parts.append(f"in {borough}")
                complaint_text = ". ".join(text_parts).strip()

                attrs = extract_attributes(complaint_text)

                records.append({
                    "complaint_id": f"NYC_{unique_key}",
                    "complaint_text": complaint_text,
                    "language": "en",
                    "category": cat,
                    "subcategory": subcat,
                    "severity": attrs["severity"],
                    "immediate_risk": attrs["immediate_risk"],
                    "public_exposure": attrs["public_exposure"],
                    "ongoing_incident": attrs["ongoing_incident"],
                    "urgency_claim": attrs["urgency_claim"],
                    "source": "NYC_311",
                })

            print(f"  Fetched {len(records)} NYC 311 records...")

        # Save to CSV
        fieldnames = [
            "complaint_id", "complaint_text", "language", "category", "subcategory",
            "severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim", "source"
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"✅ NYC 311 configured: {len(records)} records -> {output_path}")
        return records

    except Exception as e:
        print(f"  Error downloading NYC 311: {e}")
        return []


# ===========================================================================
# 2. CPGRAMS Indian Grievance Dataset Downloader
# ===========================================================================
CPGRAMS_URLS = [
    ("real", "https://raw.githubusercontent.com/HariomPtdr/cpgrams-grievance-dataset/main/data/cpgrams_central.csv"),
    ("multilingual", "https://raw.githubusercontent.com/HariomPtdr/cpgrams-grievance-dataset/main/data/synthetic_grievances.csv"),
]

CPGRAMS_DEPT_MAP = {
    "roads": ("Infrastructure & Roads", "Pothole / Road Damage"),
    "transport": ("Traffic & Road Safety", "Signal Failure"),
    "waste": ("Sanitation & Waste Management", "Garbage Pileup"),
    "sanitation": ("Sanitation & Waste Management", "Garbage Pileup"),
    "water": ("Water Supply & Drainage", "Pipeline Leakage"),
    "drain": ("Water Supply & Drainage", "Sewage Overflow"),
    "power": ("Electricity & Street Lighting", "Streetlight Failure"),
    "electricity": ("Electricity & Street Lighting", "Power Outage"),
    "health": ("Public Health & Environment", "Mosquito Breeding / Dengue Risk"),
    "pollution": ("Public Health & Environment", "Air / Noise Pollution"),
    "building": ("Building Safety", "Unsafe / Collapsing Structure"),
    "park": ("Parks & Public Spaces", "Poor Maintenance"),
}

def download_and_configure_cpgrams(output_path: str = "data/dataset_cpgrams_train.csv", limit: int = 5000):
    print(f"\n[2/3] Downloading CPGRAMS Indian Grievances (target: {limit} records)...")
    records = []

    try:
        # 1. Fetch real CPGRAMS cases
        r_real = httpx.get(CPGRAMS_URLS[0][1], timeout=20)
        if r_real.status_code == 200:
            reader = csv.DictReader(io.StringIO(r_real.text))
            for row in reader:
                body = (row.get("body") or "").strip()
                title = (row.get("title") or "").strip()
                dept = (row.get("department") or "").strip()
                c_id = (row.get("cpgrams_id") or f"CPG_{len(records)+1}").strip()

                if not body:
                    continue

                complaint_text = f"{title}. {body}".strip() if title else body
                cat = "Public Health & Environment"
                subcat = "General Grievance"
                combined_dept = f"{dept} {title}".lower()
                for key, (mapped_c, mapped_s) in CPGRAMS_DEPT_MAP.items():
                    if key in combined_dept:
                        cat = mapped_c
                        subcat = mapped_s
                        break

                attrs = extract_attributes(complaint_text)
                records.append({
                    "complaint_id": c_id,
                    "complaint_text": complaint_text,
                    "language": "en",
                    "category": cat,
                    "subcategory": subcat,
                    "severity": attrs["severity"],
                    "immediate_risk": attrs["immediate_risk"],
                    "public_exposure": attrs["public_exposure"],
                    "ongoing_incident": attrs["ongoing_incident"],
                    "urgency_claim": attrs["urgency_claim"],
                    "source": "CPGRAMS_Real",
                })

        # 2. Fetch Pan-India Multilingual / Hinglish Grievances
        headers = {"Range": f"bytes=0-{1024*1024*4}"}  # 4MB slice of synthetic_grievances
        r_multi = httpx.get(CPGRAMS_URLS[1][1], headers=headers, timeout=25)
        if r_multi.status_code in (200, 206):
            content = r_multi.text
            # Skip potential partial last line
            lines = content.splitlines()[:-1]
            reader = csv.DictReader(lines)
            for row in reader:
                text = (row.get("text") or "").strip()
                dept = (row.get("department") or "").strip()
                sub = (row.get("sub_category") or "").strip()
                lang = (row.get("language") or "en").strip()
                c_id = (row.get("complaint_id") or f"CPG_MULTI_{len(records)+1}").strip()

                if not text or len(text) < 15:
                    continue

                cat = "Infrastructure & Roads"
                subcat = sub if sub else "General Maintenance"
                combined = f"{dept} {sub}".lower()
                for key, (mapped_c, mapped_s) in CPGRAMS_DEPT_MAP.items():
                    if key in combined:
                        cat = mapped_c
                        if not sub:
                            subcat = mapped_s
                        break

                attrs = extract_attributes(text)
                records.append({
                    "complaint_id": c_id,
                    "complaint_text": text,
                    "language": lang,
                    "category": cat,
                    "subcategory": subcat,
                    "severity": attrs["severity"],
                    "immediate_risk": attrs["immediate_risk"],
                    "public_exposure": attrs["public_exposure"],
                    "ongoing_incident": attrs["ongoing_incident"],
                    "urgency_claim": attrs["urgency_claim"],
                    "source": "CPGRAMS_Multilingual",
                })
                if len(records) >= limit:
                    break

        fieldnames = [
            "complaint_id", "complaint_text", "language", "category", "subcategory",
            "severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim", "source"
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"✅ CPGRAMS configured: {len(records)} records -> {output_path}")
        return records

    except Exception as e:
        print(f"  Error downloading CPGRAMS: {e}")
        return []


# ===========================================================================
# 3. COMI-LINGUA Hinglish Normalisation Dataset Downloader
# ===========================================================================
COMI_URL = "https://huggingface.co/datasets/LingoIITGN/COMI-LINGUA/resolve/main/TN_test.csv"

def download_and_configure_comilingua(output_path: str = "data/dataset_comilingua_hinglish.csv", limit: int = 2000):
    print(f"\n[Bonus] Downloading COMI-LINGUA Hinglish normalisation dataset...")
    records = []

    try:
        r = httpx.get(COMI_URL, follow_redirects=True, timeout=30)
        if r.status_code == 200:
            reader = csv.DictReader(io.StringIO(r.text))
            for i, row in enumerate(reader):
                raw_sent = (row.get("Sentences") or "").strip()
                norm_sent = (row.get("Predicted Tags") or row.get("Annotated by: Annotator 1") or "").strip()

                if not raw_sent or len(raw_sent) < 10:
                    continue

                records.append({
                    "id": f"COMI_{i+1}",
                    "hinglish_raw": raw_sent,
                    "normalised_text": norm_sent,
                    "language": "hinglish",
                })
                if len(records) >= limit:
                    break

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "hinglish_raw", "normalised_text", "language"])
                writer.writeheader()
                writer.writerows(records)

            print(f"✅ COMI-LINGUA configured: {len(records)} Hinglish records -> {output_path}")
            return records
        else:
            print(f"  COMI-LINGUA HTTP status: {r.status_code}")
            return []

    except Exception as e:
        print(f"  Error downloading COMI-LINGUA: {e}")
        return []


# ===========================================================================
# 4. Master Hybrid Dataset Compiler
# ===========================================================================
def compile_master_hybrid_dataset(output_path: str = "data/dataset_civiclens_master_hybrid.csv"):
    print("\n[Compiling] Assembling Master Hybrid Civic Complaint Dataset...")
    master_records = []
    seen = set()

    # Load BBMP dataset
    bbmp_csv = "data/dataset_bbmp_train.csv"
    if os.path.exists(bbmp_csv):
        with open(bbmp_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t = row["complaint_text"].strip()
                if t not in seen:
                    seen.add(t)
                    row["source"] = "BBMP_Bengaluru"
                    master_records.append(row)

    # Load NYC 311 dataset
    nyc_csv = "data/dataset_nyc311_train.csv"
    if os.path.exists(nyc_csv):
        with open(nyc_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t = row["complaint_text"].strip()
                if t not in seen:
                    seen.add(t)
                    master_records.append(row)

    # Load CPGRAMS dataset
    cpg_csv = "data/dataset_cpgrams_train.csv"
    if os.path.exists(cpg_csv):
        with open(cpg_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t = row["complaint_text"].strip()
                if t not in seen:
                    seen.add(t)
                    master_records.append(row)

    print(f"Total Master Hybrid Records Assembled: {len(master_records)}")

    fieldnames = [
        "complaint_id", "complaint_text", "language", "category", "subcategory",
        "severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim", "source"
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(master_records)

    print(f"🏆 Master Hybrid Dataset Ready: {output_path}")

    # Print breakdown
    from collections import Counter
    cats = Counter(r["category"] for r in master_records)
    srcs = Counter(r["source"] for r in master_records)
    print("\nMaster Dataset Category Distribution:")
    for c, cnt in cats.most_common():
        print(f"  - {c}: {cnt}")
    print("\nMaster Dataset Source Breakdown:")
    for s, cnt in srcs.most_common():
        print(f"  - {s}: {cnt}")


def main():
    download_and_configure_nyc311(limit=5000)
    download_and_configure_cpgrams(limit=5000)
    download_and_configure_comilingua(limit=2000)
    compile_master_hybrid_dataset()


if __name__ == "__main__":
    main()

