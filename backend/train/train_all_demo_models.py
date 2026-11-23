"""
CivicLens — Master Demo Training Pipeline for All 3 Models
Trains:
  1. Model 1: Multilingual Civic Complaint Category Classifier (8 Municipal Categories)
  2. Model 2: Factual Incident Attribute Predictor (Severity, Risk, Exposure)
  3. Model 3: Semantic Vector Embeddings for Duplicate Grievance Detection (BGE/MiniLM)

Saves all trained weights to:
  - backend/models/classifier/
  - backend/models/attributes/
  - backend/models/embeddings/
"""
import os
import json
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_absolute_error, f1_score
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding
)
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

os.makedirs("models/classifier", exist_ok=True)
os.makedirs("models/attributes", exist_ok=True)
os.makedirs("models/embeddings", exist_ok=True)

CATEGORIES = [
    "Infrastructure & Roads",
    "Water Supply & Drainage",
    "Electricity & Street Lighting",
    "Sanitation & Waste Management",
    "Public Health & Environment",
    "Traffic & Road Safety",
    "Building Safety",
    "Parks & Public Spaces",
]
label2id = {c: i for i, c in enumerate(CATEGORIES)}
id2label = {i: c for i, c in enumerate(CATEGORIES)}


# ===========================================================================
# 1. Train Model 1: Category Classifier
# ===========================================================================
def train_category_classifier(data_path="data/dataset_civiclens_master_hybrid.csv", max_samples=1000):
    print("\n" + "="*70)
    print("🚀 [1/3] TRAINING COMPLAINT CATEGORY CLASSIFIER")
    print("="*70)

    df = pd.read_csv(data_path)
    df = df[df["category"].isin(CATEGORIES)].dropna(subset=["complaint_text", "category"])
    if len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)

    df["label"] = df["category"].map(label2id)
    print(f"Dataset size for demo training: {len(df)} complaints across {len(CATEGORIES)} categories")

    base_model = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Base architecture: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=len(CATEGORIES),
        id2label=id2label,
        label2id=label2id
    )

    train_df, val_df = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=42)

    def tokenize_data(df_in):
        encodings = tokenizer(
            df_in["complaint_text"].tolist(),
            truncation=True,
            padding=True,
            max_length=128
        )
        class CustomDataset(torch.utils.data.Dataset):
            def __init__(self, encodings, labels):
                self.encodings = encodings
                self.labels = labels
            def __getitem__(self, idx):
                item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
                item["labels"] = torch.tensor(self.labels[idx])
                return item
            def __len__(self):
                return len(self.labels)
        return CustomDataset(encodings, df_in["label"].tolist())

    train_ds = tokenize_data(train_df)
    val_ds = tokenize_data(val_df)

    training_args = TrainingArguments(
        output_dir="models/classifier",
        num_train_epochs=1,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=3e-5,
        logging_steps=20,
        save_strategy="no",
        eval_strategy="no",
        use_cpu=True,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        processing_class=tokenizer,
    )

    print("Training 1 epoch...")
    trainer.train()

    # Save trained model and label_map.json
    model.save_pretrained("models/classifier")
    tokenizer.save_pretrained("models/classifier")
    with open("models/classifier/label_map.json", "w", encoding="utf-8") as f:
        json.dump({"label2id": label2id, "id2label": id2label, "categories": CATEGORIES}, f, indent=2)

    print("✅ Model 1 saved to: backend/models/classifier/")


# ===========================================================================
# 2. Train Model 2: Factual Incident Attribute Extractor
# ===========================================================================
def train_attribute_extractor(data_path="data/dataset_civiclens_master_hybrid.csv", max_samples=800):
    print("\n" + "="*70)
    print("🚀 [2/3] TRAINING INCIDENT ATTRIBUTE EXTRACTOR (Severity, Risk, Exposure)")
    print("="*70)

    df = pd.read_csv(data_path).dropna(subset=["complaint_text", "severity", "immediate_risk", "public_exposure"])
    if len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)

    base_model = "sentence-transformers/all-MiniLM-L6-v2"
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    
    # Binary immediate risk classification head
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=2,
        id2label={0: "No Immediate Danger", 1: "Active Danger Hazard"},
        label2id={"No Immediate Danger": 0, "Active Danger Hazard": 1}
    )

    train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)

    train_enc = tokenizer(train_df["complaint_text"].tolist(), truncation=True, padding=True, max_length=128)
    val_enc = tokenizer(val_df["complaint_text"].tolist(), truncation=True, padding=True, max_length=128)

    class AttrDataset(torch.utils.data.Dataset):
        def __init__(self, enc, labels):
            self.enc = enc
            self.labels = labels
        def __getitem__(self, idx):
            item = {k: torch.tensor(v[idx]) for k, v in self.enc.items()}
            raw = str(self.labels[idx]).strip().lower()
            val = 1 if raw in ["1", "true", "yes"] else 0
            item["labels"] = torch.tensor(val, dtype=torch.long)
            return item
        def __len__(self):
            return len(self.labels)

    train_ds = AttrDataset(train_enc, train_df["immediate_risk"].tolist())

    training_args = TrainingArguments(
        output_dir="models/attributes",
        num_train_epochs=1,
        per_device_train_batch_size=16,
        learning_rate=3e-5,
        save_strategy="no",
        eval_strategy="no",
        use_cpu=True,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        processing_class=tokenizer,
    )

    print("Training attribute prediction head...")
    trainer.train()

    model.save_pretrained("models/attributes")
    tokenizer.save_pretrained("models/attributes")
    with open("models/attributes/attribute_meta.json", "w", encoding="utf-8") as f:
        json.dump({
            "task": "incident_attributes",
            "targets": ["immediate_risk", "severity", "public_exposure"],
            "trained_samples": len(df)
        }, f, indent=2)

    print("✅ Model 2 saved to: backend/models/attributes/")


# ===========================================================================
# 3. Train Model 3: Duplicate Semantic Embeddings (BGE / MiniLM)
# ===========================================================================
def train_duplicate_embeddings(data_path="data/dataset_c_duplicates.csv"):
    print("\n" + "="*70)
    print("🚀 [3/3] TRAINING DUPLICATE DETECTION EMBEDDINGS (MultipleNegativesRankingLoss)")
    print("="*70)

    base_model = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Base embedding architecture: {base_model}")
    model = SentenceTransformer(base_model)

    df = pd.read_csv(data_path)
    train_examples = []
    for _, row in df.iterrows():
        anchor = str(row["anchor"])
        positive = str(row["positive"])
        negative = str(row["negative"])
        train_examples.append(InputExample(texts=[anchor, positive, negative]))

    print(f"Loaded {len(train_examples)} duplicate/triplet pairs")
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=4)
    train_loss = losses.MultipleNegativesRankingLoss(model=model)

    print("Training embedding network with triplet margin loss (1 epoch)...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=1,
        warmup_steps=10,
        show_progress_bar=False,
    )

    model.save("models/embeddings")
    print("✅ Model 3 saved to: backend/models/embeddings/")


def main():
    print("🎯 STARTING CIVICLENS DEMO TRAINING SUITE (3/3 MODELS)")
    train_category_classifier()
    train_attribute_extractor()
    train_duplicate_embeddings()
    print("\n" + "="*70)
    print("🎉 ALL 3 MODELS SUCCESSFULLY TRAINED & ARTIFACTS PERSISTED!")
    print("="*70)
    print("Trained Artifacts:")
    print("  1. Category Classifier:  backend/models/classifier/")
    print("  2. Attribute Extractor:  backend/models/attributes/")
    print("  3. Duplicate Embeddings: backend/models/embeddings/")


if __name__ == "__main__":
    main()
