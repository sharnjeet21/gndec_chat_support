"""
scripts/finetune_embeddings.py — Domain Embedding Fine-Tuning Pipeline
=====================================================================
Fine-tunes SentenceTransformer embeddings on GNDEC domain Q&A pairs using
MultipleNegativesRankingLoss (contrastive in-batch negatives) to maximize
retrieval accuracy (Hit@k, MRR@k) for college-specific entities and jargon.

Run:
    python3 scripts/finetune_embeddings.py --epochs 2 --batch-size 32
"""

import os
import sys
import json
import argparse
import logging
import torch
from torch.utils.data import DataLoader
from sentence_transformers import (
    SentenceTransformer,
    InputExample,
    losses,
    evaluation
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
TRAIN_FILE = os.path.join(DATA_DIR, "train_pairs.jsonl")
VAL_FILE = os.path.join(DATA_DIR, "val_pairs.jsonl")
OUTPUT_DIR = os.path.join(ROOT_DIR, "models", "gndec_minilm_finetuned")

def load_dataset(file_path: str):
    examples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            anchor = item.get("anchor", "").strip()
            positive = item.get("positive", "").strip()
            if anchor and positive:
                examples.append(InputExample(texts=[anchor, positive]))
    return examples

def train(base_model: str = "all-MiniLM-L6-v2", epochs: int = 2, batch_size: int = 32, lr: float = 2e-5):
    logging.info(f"🚀 Initializing base model: {base_model}")
    model = SentenceTransformer(base_model)
    model.max_seq_length = 256

    logging.info(f"📂 Loading training pairs from {TRAIN_FILE}")
    train_examples = load_dataset(TRAIN_FILE)
    logging.info(f"📂 Loading validation pairs from {VAL_FILE}")
    val_examples = load_dataset(VAL_FILE)

    logging.info(f"📊 Train samples: {len(train_examples)} | Val samples: {len(val_examples)}")

    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    # Build InformationRetrievalEvaluator for validation
    corpus = {}
    queries = {}
    relevant_docs = {}

    for idx, ex in enumerate(val_examples):
        q_id = f"q_{idx}"
        d_id = f"d_{idx}"
        queries[q_id] = ex.texts[0]
        corpus[d_id] = ex.texts[1]
        relevant_docs[q_id] = {d_id}

    evaluator = evaluation.InformationRetrievalEvaluator(
        queries=queries,
        corpus=corpus,
        relevant_docs=relevant_docs,
        name="gndec-val-eval",
        show_progress_bar=True
    )

    logging.info("🔬 Running pre-training baseline evaluation on validation set...")
    baseline_metrics = evaluator(model)
    logging.info(f"Pre-training Validation Results: {baseline_metrics}")

    warmup_steps = int(len(train_dataloader) * epochs * 0.1)
    logging.info(f"🏋️ Starting fine-tuning: {epochs} epochs, {len(train_dataloader)} steps/epoch, warmup={warmup_steps}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=evaluator,
        epochs=epochs,
        evaluation_steps=len(train_dataloader) // 2,
        warmup_steps=warmup_steps,
        optimizer_params={"lr": lr},
        output_path=OUTPUT_DIR,
        show_progress_bar=True
    )

    logging.info("🔬 Running post-training evaluation on validation set...")
    post_metrics = evaluator(model)
    logging.info(f"Post-training Validation Results: {post_metrics}")

    # Save summary report
    report_path = os.path.join(OUTPUT_DIR, "finetune_report.json")
    report = {
        "base_model": base_model,
        "epochs": epochs,
        "batch_size": batch_size,
        "train_samples": len(train_examples),
        "val_samples": len(val_examples),
        "baseline_metrics": baseline_metrics,
        "post_metrics": post_metrics
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logging.info(f"✅ Domain fine-tuned model and evaluation report saved to {OUTPUT_DIR}")

def main():
    parser = argparse.ArgumentParser(description="Fine-tune embedding model for GNDEC RAG")
    parser.add_argument("--base-model", default="all-MiniLM-L6-v2", help="Base sentence-transformers model")
    parser.add_argument("--epochs", type=int, default=2, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for contrastive training")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    args = parser.parse_args()

    train(base_model=args.base_model, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

if __name__ == "__main__":
    main()
