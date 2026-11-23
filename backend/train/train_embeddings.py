"""
CivicLens Fine-Tuning Script — Semantic Duplicate Detection
Model: karmx/Llama-Karmx-Indic-Embedding-bge-m3  →  Sentence Transformers
Loss: MultipleNegativesRankingLoss (or TripletLoss for explicit pairs)
Libraries: sentence-transformers, datasets, torch, scikit-learn

Usage:
  python train/train_embeddings.py \
    --data_path data/dataset_c_duplicates.csv \
    --output_dir models/embeddings \
    --epochs 5 \
    --batch_size 16

Dataset C expected columns:
  anchor, positive, negative
  (or: complaint_a, complaint_b, label [0=not_dup, 1=dup] for binary mode)

Run from backend/ directory.
"""
import argparse
import os
import pandas as pd
import numpy as np

parser = argparse.ArgumentParser(description="Fine-tune Indic BGE-M3 for CivicLens duplicate detection")
parser.add_argument("--data_path", type=str, default="data/dataset_c_duplicates.csv")
parser.add_argument("--output_dir", type=str, default="models/embeddings")
parser.add_argument("--model_name", type=str, default="karmx/Llama-Karmx-Indic-Embedding-bge-m3")
parser.add_argument("--fallback_model", type=str, default="all-MiniLM-L6-v2")
parser.add_argument("--epochs", type=int, default=5)
parser.add_argument("--batch_size", type=int, default=16)
parser.add_argument("--lr", type=float, default=2e-5)
parser.add_argument("--max_length", type=int, default=256)
parser.add_argument("--mode", choices=["triplet", "binary"], default="triplet",
                    help="'triplet': anchor/positive/negative CSV; 'binary': complaint_a/complaint_b/label CSV")
parser.add_argument("--seed", type=int, default=42)


def prepare_triplet_dataset(df: pd.DataFrame):
    from sentence_transformers import InputExample
    examples = []
    for _, row in df.iterrows():
        anchor = str(row["anchor"])
        positive = str(row["positive"])
        negative = str(row["negative"])
        examples.append(InputExample(texts=[anchor, positive, negative]))
    return examples


def prepare_binary_dataset(df: pd.DataFrame):
    """Convert binary-labelled pairs to triplets using in-batch negatives."""
    from sentence_transformers import InputExample
    duplicates = df[df["label"] == 1]
    non_duplicates = df[df["label"] == 0]["complaint_b"].tolist()

    examples = []
    for _, row in duplicates.iterrows():
        anchor = str(row["complaint_a"])
        positive = str(row["complaint_b"])
        # Random non-duplicate as hard negative
        negative = non_duplicates[np.random.randint(len(non_duplicates))]
        examples.append(InputExample(texts=[anchor, positive, negative]))
    return examples


def evaluate_retrieval(model, val_df: pd.DataFrame, threshold: float = 0.80) -> dict:
    """
    Evaluate precision, recall, F1 on validation duplicate pairs.
    Per spec §5.5: tune threshold on validation, not test data.
    """
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.metrics import precision_score, recall_score, f1_score

    pairs_a = val_df["complaint_a"].tolist()
    pairs_b = val_df["complaint_b"].tolist()
    labels = val_df["label"].tolist()

    emb_a = model.encode(pairs_a, normalize_embeddings=True, batch_size=32)
    emb_b = model.encode(pairs_b, normalize_embeddings=True, batch_size=32)

    sims = np.sum(emb_a * emb_b, axis=1)   # Cosine (normalised dot product)
    preds = (sims >= threshold).astype(int)

    return {
        "precision": round(precision_score(labels, preds), 4),
        "recall": round(recall_score(labels, preds), 4),
        "f1": round(f1_score(labels, preds), 4),
        "threshold_used": threshold,
        "pair_count": len(labels),
    }


def main():
    args = parser.parse_args()
    from sentence_transformers import SentenceTransformer, losses
    from torch.utils.data import DataLoader
    import torch

    os.makedirs(args.output_dir, exist_ok=True)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    print(f"Loading embedding model: {args.model_name}")
    try:
        model = SentenceTransformer(args.model_name)
        print(f"Loaded primary model: {args.model_name}")
    except Exception as e:
        print(f"Primary model unavailable ({e}). Falling back to: {args.fallback_model}")
        model = SentenceTransformer(args.fallback_model)

    model.max_seq_length = args.max_length

    print(f"Loading dataset from: {args.data_path}")
    df = pd.read_csv(args.data_path)

    # Split by incident cluster ID if present (per spec §5.5)
    # Otherwise random split — but keep duplicate pairs together
    if "incident_cluster_id" in df.columns:
        from sklearn.model_selection import GroupShuffleSplit
        gss = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=args.seed)
        train_idx, temp_idx = next(gss.split(df, groups=df["incident_cluster_id"]))
        train_df = df.iloc[train_idx]
        temp_df = df.iloc[temp_idx]
        gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=args.seed)
        val_idx, test_idx = next(gss2.split(temp_df, groups=temp_df["incident_cluster_id"]))
        val_df = temp_df.iloc[val_idx]
        test_df = temp_df.iloc[test_idx]
    else:
        from sklearn.model_selection import train_test_split
        train_df, temp_df = train_test_split(df, test_size=0.30, random_state=args.seed)
        val_df, test_df = train_test_split(temp_df, test_size=0.50, random_state=args.seed)

    print(f"Split — Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    if args.mode == "triplet":
        train_examples = prepare_triplet_dataset(train_df)
    else:
        train_examples = prepare_binary_dataset(train_df)

    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)

    # MultipleNegativesRankingLoss (per spec §5.4)
    train_loss = losses.MultipleNegativesRankingLoss(model=model)

    print(f"Starting fine-tuning for {args.epochs} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=max(100, len(train_dataloader) // 10),
        optimizer_params={"lr": args.lr},
        output_path=args.output_dir,
        show_progress_bar=True,
    )

    # Evaluate on validation set (binary pairs mode)
    if "complaint_a" in val_df.columns and "label" in val_df.columns:
        print("\nEvaluating on validation set...")
        val_metrics = evaluate_retrieval(model, val_df)
        print(f"Validation — Precision: {val_metrics['precision']}, Recall: {val_metrics['recall']}, F1: {val_metrics['f1']}")
        print(f"Tip: Tune similarity threshold on this validation data before testing.")

    if "complaint_a" in test_df.columns and "label" in test_df.columns:
        print("\nFinal evaluation on test set...")
        test_metrics = evaluate_retrieval(model, test_df)
        print(f"Test — Precision: {test_metrics['precision']}, Recall: {test_metrics['recall']}, F1: {test_metrics['f1']}")

    model.save(args.output_dir)
    print(f"\n✅ Embedding model saved to: {args.output_dir}")
    print(f"   Load via: duplicate_service.load_finetuned_model('{args.output_dir}')")


if __name__ == "__main__":
    main()

