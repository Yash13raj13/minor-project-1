"""
CivicLens Training Data — CSV templates and seed examples.

This script creates labelled datasets matching the CivicLens architecture:
  1. data/dataset_a_classification.csv    — Primary complaint classification + attributes (Unified Multi-Task Dataset)
  2. data/dataset_b_attributes.csv        — Standalone incident attributes
  3. data/dataset_c_duplicates.csv        — Triplet duplicate pairs for BGE-M3 embeddings
  4. data/dataset_c_binary.csv            — Binary duplicate evaluation pairs

Per System Specification (§3.3):
Each complaint has textual & categorical fields:
  - complaint_text, language, category, subcategory
AND separately labelled incident attributes:
  - severity (1-5)
  - immediate_risk (0 or 1 / True or False)
  - public_exposure (1-5)
  - ongoing_incident (0 or 1 / True or False)
  - urgency_claim (0 or 1 / True or False)

Do NOT collapse these into a single label; attributes are extracted independently
and processed by the deterministic priority engine.
"""
import os
import pandas as pd

os.makedirs("data", exist_ok=True)

# ---------------------------------------------------------------------------
# Dataset A: Complaint Classification + Incident Attributes (Unified)
# ---------------------------------------------------------------------------
dataset_records = [
    # Infrastructure & Roads
    {
        "complaint_id": "C0001",
        "complaint_text": "Large pothole near school gate causing accidents",
        "language": "en",
        "category": "Infrastructure & Roads",
        "subcategory": "Pothole / Road Damage",
        "severity": 3,
        "immediate_risk": 1,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    {
        "complaint_id": "C0002",
        "complaint_text": "Road pe bahut bada gaddha hai, accident ho sakta hai",
        "language": "hinglish",
        "category": "Infrastructure & Roads",
        "subcategory": "Pothole / Road Damage",
        "severity": 3,
        "immediate_risk": 1,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0003",
        "complaint_text": "Metro station ke paas footpath broken hai",
        "language": "hinglish",
        "category": "Infrastructure & Roads",
        "subcategory": "Broken Footpath",
        "severity": 2,
        "immediate_risk": 0,
        "public_exposure": 3,
        "ongoing_incident": 0,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0004",
        "complaint_text": "Bridge near sector 12 has visible deep cracks and vibration",
        "language": "en",
        "category": "Infrastructure & Roads",
        "subcategory": "Bridge Damage",
        "severity": 4,
        "immediate_risk": 1,
        "public_exposure": 3,
        "ongoing_incident": 0,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    # Water Supply & Drainage
    {
        "complaint_id": "C0005",
        "complaint_text": "Water pipeline leaking near school for 3 days, clean water wasting",
        "language": "en",
        "category": "Water Supply & Drainage",
        "subcategory": "Pipeline Leakage",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    {
        "complaint_id": "C0006",
        "complaint_text": "Paani ki pipeline leak ho rahi hai sadak par",
        "language": "hinglish",
        "category": "Water Supply & Drainage",
        "subcategory": "Pipeline Leakage",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0007",
        "complaint_text": "No water supply in our colony since yesterday morning",
        "language": "en",
        "category": "Water Supply & Drainage",
        "subcategory": "No Water Supply",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0008",
        "complaint_text": "Naali ka paani sadak par aa raha hai ganda foul smell",
        "language": "hinglish",
        "category": "Water Supply & Drainage",
        "subcategory": "Sewage Overflow",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0009",
        "complaint_text": "Drain is completely blocked and sewage overflowing onto road",
        "language": "en",
        "category": "Water Supply & Drainage",
        "subcategory": "Drain Blockage",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 2,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    # Electricity & Street Lighting
    {
        "complaint_id": "C0010",
        "complaint_text": "Exposed live electric wire hanging near playground, urgent danger",
        "language": "en",
        "category": "Electricity & Street Lighting",
        "subcategory": "Exposed / Live Wire",
        "severity": 5,
        "immediate_risk": 1,
        "public_exposure": 5,
        "ongoing_incident": 1,
        "urgency_claim": 1,
        "evidence_quality": 4,
    },
    {
        "complaint_id": "C0011",
        "complaint_text": "Street light kaam nahi kar rahi pillar 44 ke paas",
        "language": "hinglish",
        "category": "Electricity & Street Lighting",
        "subcategory": "Streetlight Failure",
        "severity": 2,
        "immediate_risk": 0,
        "public_exposure": 2,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0012",
        "complaint_text": "Power outage in ward 7 since 6 AM today",
        "language": "en",
        "category": "Electricity & Street Lighting",
        "subcategory": "Power Outage",
        "severity": 2,
        "immediate_risk": 0,
        "public_exposure": 2,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    # Sanitation & Waste Management
    {
        "complaint_id": "C0013",
        "complaint_text": "Garbage pile near primary school not cleared for 5 days, severe smell",
        "language": "en",
        "category": "Sanitation & Waste Management",
        "subcategory": "Garbage Pileup",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    {
        "complaint_id": "C0014",
        "complaint_text": "Kachra main market ke bahar bahut zyada jama ho gaya hai",
        "language": "hinglish",
        "category": "Sanitation & Waste Management",
        "subcategory": "Garbage Pileup",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0015",
        "complaint_text": "Illegal dumping of construction debris on public sidewalk",
        "language": "en",
        "category": "Sanitation & Waste Management",
        "subcategory": "Illegal Dumping",
        "severity": 2,
        "immediate_risk": 0,
        "public_exposure": 2,
        "ongoing_incident": 0,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    # Public Health & Environment
    {
        "complaint_id": "C0016",
        "complaint_text": "Stagnant water near apartment breeding mosquitoes, dengue risk",
        "language": "en",
        "category": "Public Health & Environment",
        "subcategory": "Mosquito Breeding / Dengue Risk",
        "severity": 3,
        "immediate_risk": 1,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    {
        "complaint_id": "C0017",
        "complaint_text": "Machchar bahut zyada hain open naali ke paas",
        "language": "hinglish",
        "category": "Public Health & Environment",
        "subcategory": "Mosquito Breeding / Dengue Risk",
        "severity": 3,
        "immediate_risk": 0,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0018",
        "complaint_text": "Pack of aggressive stray dogs attacking residents near park gate",
        "language": "en",
        "category": "Public Health & Environment",
        "subcategory": "Stray Animal Attack",
        "severity": 4,
        "immediate_risk": 1,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    # Traffic & Road Safety
    {
        "complaint_id": "C0019",
        "complaint_text": "Traffic signal malfunctioning at main crossing since 2 days",
        "language": "en",
        "category": "Traffic & Road Safety",
        "subcategory": "Signal Failure",
        "severity": 2,
        "immediate_risk": 1,
        "public_exposure": 3,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0020",
        "complaint_text": "Illegal parking blocking emergency hospital ambulance access",
        "language": "en",
        "category": "Traffic & Road Safety",
        "subcategory": "Illegal Parking Obstruction",
        "severity": 3,
        "immediate_risk": 1,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 1,
        "evidence_quality": 2,
    },
    # Building Safety
    {
        "complaint_id": "C0021",
        "complaint_text": "Old commercial building wall showing severe cracks and may collapse",
        "language": "en",
        "category": "Building Safety",
        "subcategory": "Unsafe / Collapsing Structure",
        "severity": 5,
        "immediate_risk": 1,
        "public_exposure": 4,
        "ongoing_incident": 1,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
    # Parks & Public Spaces
    {
        "complaint_id": "C0022",
        "complaint_text": "Fallen heavy tree branch blocking public park entrance walkway",
        "language": "en",
        "category": "Parks & Public Spaces",
        "subcategory": "Fallen Tree",
        "severity": 2,
        "immediate_risk": 0,
        "public_exposure": 2,
        "ongoing_incident": 0,
        "urgency_claim": 0,
        "evidence_quality": 2,
    },
    {
        "complaint_id": "C0023",
        "complaint_text": "Children playground swing chains broken and rusted",
        "language": "en",
        "category": "Parks & Public Spaces",
        "subcategory": "Broken Equipment",
        "severity": 3,
        "immediate_risk": 1,
        "public_exposure": 3,
        "ongoing_incident": 0,
        "urgency_claim": 0,
        "evidence_quality": 3,
    },
]

# Write Dataset A (with both classification and separate attribute columns)
df_all = pd.DataFrame(dataset_records)
df_all.to_csv("data/dataset_a_classification.csv", index=False)
print(f"Dataset A saved: {len(df_all)} rows → data/dataset_a_classification.csv")

# Write Dataset B (standalone attributes tied to complaint_id)
attr_cols = ["complaint_id", "severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim", "evidence_quality"]
df_b = df_all[attr_cols]
df_b.to_csv("data/dataset_b_attributes.csv", index=False)
print(f"Dataset B saved: {len(df_b)} rows → data/dataset_b_attributes.csv")

# ---------------------------------------------------------------------------
# Dataset C: Duplicate Complaint Pairs (triplets and binary)
# ---------------------------------------------------------------------------
dataset_c = [
    {"anchor": "Large pothole near Metro Gate 2", "positive": "Road damaged outside metro gate 2", "negative": "Water shortage in Sector 5", "incident_cluster_id": 1},
    {"anchor": "Road pe bada gaddha hai Gate 2 ke paas", "positive": "Huge crater outside Gate 2 metro", "negative": "Electricity not available in ward 7", "incident_cluster_id": 1},
    {"anchor": "Pipeline leaking near school gate", "positive": "Water leakage outside school", "negative": "Broken streetlight near park", "incident_cluster_id": 2},
    {"anchor": "Paani ki pipeline leak ho rahi school ke bahar", "positive": "Water pipe broken near school", "negative": "Pothole on Ring Road", "incident_cluster_id": 2},
    {"anchor": "Garbage overflowing at Market Road bin", "positive": "Trash piled up at Market Road", "negative": "Signal not working at junction", "incident_cluster_id": 3},
    {"anchor": "Kachra Market Road pe bahut zyada hai", "positive": "Garbage not collected at Market Road for 5 days", "negative": "Mosquito breeding near colony", "incident_cluster_id": 3},
    {"anchor": "Exposed wire near children's park", "positive": "Bare electric cable outside children park", "negative": "No water supply since morning", "incident_cluster_id": 4},
    {"anchor": "Broken street light on Ring Road pillar 44", "positive": "Streetlight not working near pillar 44", "negative": "Sewage overflow in colony", "incident_cluster_id": 5},
    {"anchor": "Dengue risk near Ward 9 stagnant water", "positive": "Stagnant drain water mosquito breeding ward 9", "negative": "Road damage near school", "incident_cluster_id": 6},
    {"anchor": "No water supply since yesterday morning", "positive": "Water nahi aa raha hai colony mein kal se", "negative": "Illegal parking blocking lane", "incident_cluster_id": 7},
    {"anchor": "Pothole on Ring Road", "positive": "No water supply on Ring Road", "negative": "Garbage pileup at junction", "incident_cluster_id": 99},
]

df_c = pd.DataFrame(dataset_c)
df_c.to_csv("data/dataset_c_duplicates.csv", index=False)

binary_pairs = []
for _, row in df_c.iterrows():
    if row["incident_cluster_id"] != 99:
        binary_pairs.append({"complaint_a": row["anchor"], "complaint_b": row["positive"], "label": 1, "incident_cluster_id": row["incident_cluster_id"]})
        binary_pairs.append({"complaint_a": row["anchor"], "complaint_b": row["negative"], "label": 0, "incident_cluster_id": 0})
    else:
        binary_pairs.append({"complaint_a": row["anchor"], "complaint_b": row["positive"], "label": 0, "incident_cluster_id": 0})

df_binary = pd.DataFrame(binary_pairs)
df_binary.to_csv("data/dataset_c_binary.csv", index=False)

print(f"Dataset C saved: {len(df_c)} triplets → data/dataset_c_duplicates.csv")
print(f"Dataset C (binary) saved: {len(df_binary)} pairs → data/dataset_c_binary.csv")
print("\nSchema Verification:")
print(f"Dataset A columns: {list(df_all.columns)}")


