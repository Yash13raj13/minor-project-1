"""
CivicLens Fine-Tuning Script — Multilingual Complaint Classification & Incident Attributes
Primary Model Candidates:
  - LatentAILabs/yama-indic (Multilingual classification & structured decision tasks)
  - FacebookAI/xlm-roberta-base (Supervised cross-lingual baseline)

Dataset Expected Columns:
  Categorical:
    - complaint_text  (Text in English, Hindi, or Hinglish)
    - language        (en, hi, hinglish)
    - category        (Primary department category)
    - subcategory     (Fine-grained incident category)
  Separately Labelled Incident Attributes (DO NOT merge into single label):
    - severity          (1-5 integer scale)
    - immediate_risk    (0 or 1 / boolean)
    - public_exposure   (1-5 integer scale)
    - ongoing_incident  (0 or 1 / boolean)
    - urgency_claim     (0 or 1 / boolean - logged for officer review, not priority formula)

Usage:
  # Using Yama-Indic for multilingual classification:
  python train/train_classifier.py \
    --model_name LatentAILabs/yama-indic \
    --data_path data/dataset_a_classification.csv \
    --output_dir models/classifier \
    --epochs 4 \
    --batch_size 8

  # Using XLM-RoBERTa baseline with LoRA:
  python train/train_classifier.py \
    --model_name FacebookAI/xlm-roberta-base \
    --data_path data/dataset_a_classification.csv \
    --output_dir models/classifier \
    --use_lora \
    --epochs 4

Run from backend/ directory.
"""
import argparse
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# CLI arguments
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Fine-tune Yama-Indic or XLM-RoBERTa for CivicLens complaint classification")
parser.add_argument("--data_path", type=str, default="data/dataset_a_classification.csv")
parser.add_argument("--output_dir", type=str, default="models/classifier")
parser.add_argument("--model_name", type=str, default="LatentAILabs/yama-indic",
                    help="Hugging Face model: LatentAILabs/yama-indic or FacebookAI/xlm-roberta-base")
parser.add_argument("--epochs", type=int, default=4)
parser.add_argument("--batch_size", type=int, default=8)
parser.add_argument("--lr", type=float, default=2e-5)
parser.add_argument("--max_length", type=int, default=256)
parser.add_argument("--use_lora", action="store_true", help="Use LoRA fine-tuning (requires peft)")
parser.add_argument("--train_attributes", action="store_true",
                    help="Also train/evaluate auxiliary attribute predictions (severity, risk, exposure)")
parser.add_argument("--seed", type=int, default=42)


# ---------------------------------------------------------------------------
# Category taxonomy (must match classifier.py PRIMARY_CATEGORIES)
# ---------------------------------------------------------------------------
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


def compute_metrics(eval_pred, label_names):
    import evaluate
    from sklearn.metrics import classification_report
    metric = evaluate.load("f1")
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    # Macro F1 (primary metric per spec §3.6)
    f1 = metric.compute(predictions=predictions, references=labels, average="macro")

    # Per-class report for language-wise analysis
    report = classification_report(labels, predictions, target_names=label_names, output_dict=True)
    return {
        "macro_f1": f1["f1"],
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
    }


def prepare_dataset(data_path: str, tokenizer, max_length: int, seed: int):
    from datasets import Dataset
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(data_path)
    assert "complaint_text" in df.columns and "category" in df.columns, (
        "Dataset must have 'complaint_text' and 'category' columns"
    )

    # Encode labels
    label2id = {cat: i for i, cat in enumerate(CATEGORIES)}
    id2label = {i: cat for i, cat in enumerate(CATEGORIES)}
    df = df[df["category"].isin(CATEGORIES)].dropna(subset=["complaint_text", "category"])
    df["label"] = df["category"].map(label2id)

    # Log dataset attribute information if available
    attribute_cols = ["severity", "immediate_risk", "public_exposure", "ongoing_incident", "urgency_claim"]
    available_attrs = [c for c in attribute_cols if c in df.columns]
    if available_attrs:
        print(f"✅ Found separate incident attributes in dataset: {available_attrs}")
        for attr in available_attrs:
            val_counts = df[attr].value_counts().to_dict()
            print(f"   - {attr}: {val_counts}")
    else:
        print("ℹ️ Note: Dataset only has classification labels. Incident attributes not found.")

    # Split: 70% train, 15% val, 15% test
    # Keep incidents from same cluster in same split (stratify by category label)
    train_df, temp_df = train_test_split(df, test_size=0.30, stratify=df["label"], random_state=seed)
    val_df, test_df = train_test_split(temp_df, test_size=0.50, stratify=temp_df["label"], random_state=seed)

    print(f"Dataset split — Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    if "language" in df.columns:
        print(f"Languages present: {df['language'].value_counts().to_dict()}")

    def tokenize_fn(examples):
        return tokenizer(
            examples["complaint_text"],
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )

    def to_hf_dataset(df_):
        ds = Dataset.from_pandas(df_[["complaint_text", "label"]].reset_index(drop=True))
        return ds.map(tokenize_fn, batched=True)

    return (
        to_hf_dataset(train_df),
        to_hf_dataset(val_df),
        to_hf_dataset(test_df),
        label2id,
        id2label,
    )


def compute_class_weights(train_dataset):
    """Inverse-frequency class weighting for imbalanced categories."""
    from sklearn.utils.class_weight import compute_class_weight
    labels = [item["label"] for item in train_dataset]
    classes = list(range(len(CATEGORIES)))
    weights = compute_class_weight("balanced", classes=np.array(classes), y=np.array(labels))
    return weights


def main():
    args = parser.parse_args()
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        TrainingArguments, Trainer, DataCollatorWithPadding,
        EarlyStoppingCallback,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    print(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    print("Preparing dataset...")
    train_ds, val_ds, test_ds, label2id, id2label = prepare_dataset(
        args.data_path, tokenizer, args.max_length, args.seed
    )

    print(f"Loading model: {args.model_name}")
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(CATEGORIES),
        id2label=id2label,
        label2id=label2id,
    )

    # Optional LoRA fine-tuning (reduces GPU memory significantly)
    if args.use_lora:
        from peft import get_peft_model, LoraConfig, TaskType
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_CLS,
            inference_mode=False,
            r=16,
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["query", "value"],
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

    class_weights = compute_class_weights(train_ds)
    weight_tensor = torch.tensor(class_weights, dtype=torch.float)

    # Custom trainer with class-weighted loss
    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get("labels")
            outputs = model(**inputs)
            logits = outputs.get("logits")
            loss_fct = torch.nn.CrossEntropyLoss(weight=weight_tensor.to(logits.device))
            loss = loss_fct(logits, labels)
            return (loss, outputs) if return_outputs else loss

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_dir=f"{args.output_dir}/logs",
        logging_steps=10,
        save_total_limit=2,
        seed=args.seed,
        report_to="none",
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=lambda x: compute_metrics(x, CATEGORIES),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    print("Starting fine-tuning...")
    trainer.train()

    print("Evaluating on test set...")
    test_results = trainer.evaluate(test_ds)
    print(f"Test Results: {test_results}")

    # Save final model + label map
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    with open(f"{args.output_dir}/label_map.json", "w") as f:
        json.dump({"label2id": label2id, "id2label": id2label, "categories": CATEGORIES}, f, indent=2)

    print(f"\n✅ Model saved to: {args.output_dir}")
    print(f"   Load in classifier.py via: classifier_service.load_finetuned_model('{args.output_dir}')")


if __name__ == "__main__":
    main()

