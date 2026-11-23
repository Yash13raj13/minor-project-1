import os
import csv
from collections import Counter

def merge_all_with_marathi():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    master_path = os.path.join(data_dir, "dataset_civiclens_master_hybrid.csv")
    
    # 1. First re-assemble base datasets (BBMP, NYC, CPGRAMS)
    master_records = []
    seen = set()

    for fname, src in [
        ("dataset_bbmp_train.csv", "BBMP_Bengaluru"),
        ("dataset_nyc311_train.csv", "NYC_311"),
        ("dataset_cpgrams_train.csv", "CPGRAMS_India")
    ]:
        p = os.path.join(data_dir, fname)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    txt = row.get("complaint_text", "").strip()
                    if txt and txt not in seen:
                        seen.add(txt)
                        row["source"] = src
                        # ensure both fields
                        row["complaint_text"] = txt
                        row["text"] = txt
                        master_records.append(row)

    print(f"Base records loaded: {len(master_records)}")

    # 2. Add Marathi dataset (CivicNLP-608)
    marathi_p = os.path.join(data_dir, "dataset_marathi_civic.csv")
    if os.path.exists(marathi_p):
        with open(marathi_p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txt = (row.get("text") or row.get("complaint_text") or row.get("description", "")).strip()
                if txt and txt not in seen:
                    seen.add(txt)
                    row["complaint_text"] = txt
                    row["text"] = txt
                    row["source"] = row.get("source_dataset", "CivicNLP-608-Marathi")
                    master_records.append(row)

    print(f"Total Master Hybrid Records with Marathi: {len(master_records)}")

    fieldnames = [
        "complaint_id", "complaint_text", "text", "language", "category", "subcategory",
        "severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim", "source"
    ]
    with open(master_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(master_records)

    langs = Counter(r.get("language", "Unknown") for r in master_records)
    print("\nLanguages:")
    for l, cnt in langs.items():
        print(f"  - {l}: {cnt}")
    cats = Counter(r.get("category", "Unknown") for r in master_records)
    print("\nCategories:")
    for c, cnt in cats.items():
        print(f"  - {c}: {cnt}")

if __name__ == "__main__":
    merge_all_with_marathi()
