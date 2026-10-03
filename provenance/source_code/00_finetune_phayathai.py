"""
00_finetune_phayathai.py
Fine-tune PhayathaiBERT (WangchanBERTa) using ensemble pseudo-labels.

Teacher signals (pseudo-labels):
  ensemble_score = (finbert_score + xlmr_score + gemma_score) / 3
  All 3 scores are taken from the translated English text (Text_EN).
  All 3 source files share the same row order → merge by index.

Student:
  PhayathaiBERT (airesearch/wangchanberta-base-att-spm-uncased)
  Input  : Thai text  (Headline + Description + Text)
  Output : regression score ∈ [−1, +1]  (Tanh head on [CLS])
  Loss   : MSELoss(predicted, ensemble_score)

Saves:
  data/models/phayathai_ft/          ← HuggingFace model + tokenizer
  data/sentiment_scores/phafin/scores_phayathai_ft.csv
  data/sentiment_scores/phafin/ft_build_log.txt
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import math
import random
import copy
from datetime import datetime

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModel,
    get_linear_schedule_with_warmup,
)
from config import (
    SCORE_FINBERT, SCORE_XLMR, SCORE_GEMMA,
    SCORE_PHAYATHAI_FT, FT_MODEL_DIR,
    PHAYATHAI_BASE_MODEL,
    FT_MAX_LEN, FT_BATCH_SIZE, FT_EPOCHS, FT_PATIENCE,
    FT_LR, FT_WEIGHT_DECAY, FT_WARMUP_RATIO,
    FT_TRAIN_RATIO, FT_SEED,
)

LOG_FILE = SCORE_PHAYATHAI_FT.parent / "ft_build_log.txt"

OUT_COLS = [
    "Date", "Symbol", "Source", "Language",
    "Headline", "Description", "Text", "URL",
    "phafin_label", "phafin_pos", "phafin_neg", "phafin_neu",
    "phafin_score",
]


# ─────────────────────────────────────────────────────────────────────────────
# Reproducibility
# ─────────────────────────────────────────────────────────────────────────────

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Build ensemble pseudo-labels
# ─────────────────────────────────────────────────────────────────────────────

def build_pseudo_labels() -> pd.DataFrame:
    """
    Load the 3 score files (same row order), compute ensemble mean.
    Returns DataFrame with Thai articles only + ensemble_score column.
    """
    fb = pd.read_csv(SCORE_FINBERT)
    xl = pd.read_csv(SCORE_XLMR)
    gm = pd.read_csv(SCORE_GEMMA)

    assert len(fb) == len(xl) == len(gm), "Score files have different row counts"

    # Row-wise mean of the 3 scores
    ensemble = (fb["finbert_score"].values +
                xl["xlmr_score"].values +
                gm["gemma_score"].values) / 3.0

    # Base DataFrame from FinBERT (has Thai text columns)
    df = fb[["Date", "Symbol", "Source", "Language",
             "Headline", "Description", "URL"]].copy()

    # Thai text — prefer original from XLM-R/GEMMA file (has "Text" column)
    df["Text"] = xl["Text"].values if "Text" in xl.columns else ""
    df["ensemble_score"] = ensemble.astype(np.float32)

    # TH only
    df_th = df[df["Language"] == "TH"].copy().reset_index(drop=True)
    print(f"  Total articles   : {len(df)}")
    print(f"  TH articles      : {len(df_th)}")
    print(f"  Ensemble score   : mean={df_th['ensemble_score'].mean():.4f}  "
          f"std={df_th['ensemble_score'].std():.4f}  "
          f"min={df_th['ensemble_score'].min():.4f}  "
          f"max={df_th['ensemble_score'].max():.4f}")
    return df_th


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Dataset
# ─────────────────────────────────────────────────────────────────────────────

def make_text(row: pd.Series) -> str:
    """Concatenate Headline + Description + Text for tokenization."""
    parts = []
    for col in ["Headline", "Description", "Text"]:
        v = str(row.get(col, "") or "")
        if v not in ("", "nan", "None"):
            parts.append(v.strip())
    return " ".join(parts)[:2000]   # pre-truncate before tokenizer


class SentimentDataset(Dataset):
    def __init__(self, texts: list, labels: np.ndarray, tokenizer, max_len: int):
        self.texts     = texts
        self.labels    = labels.astype(np.float32)
        self.tokenizer = tokenizer
        self.max_len   = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            max_length      = self.max_len,
            padding         = "max_length",
            truncation      = True,
            return_tensors  = "pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label":          torch.tensor(self.labels[idx]),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Model
# ─────────────────────────────────────────────────────────────────────────────

class PhayathaiRegressor(nn.Module):
    """PhayathaiBERT + linear regression head with Tanh output ∈ [−1, +1]."""
    def __init__(self, model_name: str, dropout: float = 0.1):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden       = self.encoder.config.hidden_size
        self.drop    = nn.Dropout(dropout)
        self.head    = nn.Linear(hidden, 1)
        self.act     = nn.Tanh()

    def forward(self, input_ids, attention_mask):
        out  = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls  = out.last_hidden_state[:, 0, :]   # [CLS] token
        return self.act(self.head(self.drop(cls))).squeeze(-1)


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Training loop
# ─────────────────────────────────────────────────────────────────────────────

def train(
    model: PhayathaiRegressor,
    train_loader: DataLoader,
    val_loader:   DataLoader,
    device: str,
    log: list,
) -> PhayathaiRegressor:
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=FT_LR, weight_decay=FT_WEIGHT_DECAY
    )
    total_steps  = len(train_loader) * FT_EPOCHS
    warmup_steps = int(total_steps * FT_WARMUP_RATIO)
    scheduler    = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    loss_fn = nn.MSELoss()

    best_val  = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    patience   = 0

    for epoch in range(1, FT_EPOCHS + 1):
        # ── Train ──────────────────────────────────────────────────────────
        model.train()
        tr_losses = []
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attn_mask = batch["attention_mask"].to(device)
            labels    = batch["label"].to(device)

            optimizer.zero_grad()
            preds = model(input_ids, attn_mask)
            loss  = loss_fn(preds, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            tr_losses.append(loss.item())

        # ── Validate ───────────────────────────────────────────────────────
        model.eval()
        val_losses, val_preds, val_true = [], [], []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attn_mask = batch["attention_mask"].to(device)
                labels    = batch["label"].to(device)
                preds     = model(input_ids, attn_mask)
                val_losses.append(loss_fn(preds, labels).item())
                val_preds.extend(preds.cpu().numpy())
                val_true.extend(labels.cpu().numpy())

        tr_mse  = float(np.mean(tr_losses))
        val_mse = float(np.mean(val_losses))
        val_corr = float(np.corrcoef(val_true, val_preds)[0, 1])

        msg = (f"  Epoch {epoch}/{FT_EPOCHS}  "
               f"train_MSE={tr_mse:.5f}  val_MSE={val_mse:.5f}  "
               f"val_r={val_corr:.4f}")
        print(msg); log.append(msg)

        if val_mse < best_val - 1e-6:
            best_val   = val_mse
            best_state = copy.deepcopy(model.state_dict())
            patience   = 0
            log.append(f"    -> New best val_MSE={best_val:.5f}  (saved)")
        else:
            patience += 1
            if patience >= FT_PATIENCE:
                msg = f"  Early stop at epoch {epoch} (patience={FT_PATIENCE})"
                print(msg); log.append(msg)
                break

    model.load_state_dict(best_state)
    return model


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Inference on all TH articles
# ─────────────────────────────────────────────────────────────────────────────

def run_inference(
    model: PhayathaiRegressor,
    tokenizer,
    df_th: pd.DataFrame,
    device: str,
) -> np.ndarray:
    model.eval()
    texts    = [make_text(row) for _, row in df_th.iterrows()]
    scores   = []

    batch_size = FT_BATCH_SIZE * 2   # inference can use larger batch
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        enc = tokenizer(
            batch_texts,
            max_length     = FT_MAX_LEN,
            padding        = "max_length",
            truncation     = True,
            return_tensors = "pt",
        )
        with torch.no_grad():
            preds = model(
                enc["input_ids"].to(device),
                enc["attention_mask"].to(device),
            )
        scores.extend(preds.cpu().numpy())

    return np.array(scores, dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    set_seed(FT_SEED)
    log  = [f"[{datetime.now().isoformat()}] PhayathaiBERT fine-tuning started"]
    log.append(f"Base model : {PHAYATHAI_BASE_MODEL}")
    log.append(f"Device     : {'cuda' if torch.cuda.is_available() else 'cpu'}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── 1. Pseudo-labels ─────────────────────────────────────────────────────
    print("Step 1: Building ensemble pseudo-labels ...")
    df_th = build_pseudo_labels()

    # ── 2. Tokenizer & Dataset ───────────────────────────────────────────────
    print(f"Step 2: Loading tokenizer from {PHAYATHAI_BASE_MODEL} ...")
    tokenizer = AutoTokenizer.from_pretrained(PHAYATHAI_BASE_MODEL)

    texts  = [make_text(row) for _, row in df_th.iterrows()]
    labels = df_th["ensemble_score"].values

    n_tr  = int(len(texts) * FT_TRAIN_RATIO)
    idx   = list(range(len(texts)))
    random.shuffle(idx)
    tr_idx, va_idx = idx[:n_tr], idx[n_tr:]

    train_ds = SentimentDataset(
        [texts[i] for i in tr_idx],
        labels[tr_idx], tokenizer, FT_MAX_LEN,
    )
    val_ds = SentimentDataset(
        [texts[i] for i in va_idx],
        labels[va_idx], tokenizer, FT_MAX_LEN,
    )
    train_loader = DataLoader(train_ds, batch_size=FT_BATCH_SIZE, shuffle=True,
                              num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=FT_BATCH_SIZE, shuffle=False,
                              num_workers=0)

    log.append(f"Train samples: {len(train_ds)}  |  Val samples: {len(val_ds)}")
    print(f"  Train: {len(train_ds)}  |  Val: {len(val_ds)}")

    # ── 3. Model + Training ──────────────────────────────────────────────────
    print(f"Step 3: Fine-tuning PhayathaiBERT on {device} ...")
    model = PhayathaiRegressor(PHAYATHAI_BASE_MODEL)
    model = train(model, train_loader, val_loader, device, log)

    # ── 4. Save model ────────────────────────────────────────────────────────
    print(f"Step 4: Saving fine-tuned model -> {FT_MODEL_DIR}")
    FT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.encoder.save_pretrained(FT_MODEL_DIR)
    tokenizer.save_pretrained(FT_MODEL_DIR)
    torch.save(model.state_dict(), FT_MODEL_DIR / "regressor_head.pt")
    log.append(f"Model saved -> {FT_MODEL_DIR}")

    # ── 5. Inference on all TH articles ──────────────────────────────────────
    print("Step 5: Running inference on all TH articles ...")
    ft_scores = run_inference(model, tokenizer, df_th, device)

    # Convert to label
    def score_to_label(s):
        if s > 0.05:  return "positive"
        if s < -0.05: return "negative"
        return "neutral"

    out_df = df_th[["Date", "Symbol", "Source", "Language",
                    "Headline", "Description", "Text", "URL"]].copy()
    out_df["phafin_score"] = ft_scores
    out_df["phafin_label"] = [score_to_label(s) for s in ft_scores]

    # Decompose score into pseudo pos/neg/neu (for compatibility with report)
    out_df["phafin_pos"] = np.clip((ft_scores + 1) / 2, 0, 1)
    out_df["phafin_neg"] = np.clip((-ft_scores + 1) / 2, 0, 1)
    out_df["phafin_neu"] = 1 - np.abs(ft_scores)
    out_df["source_model"] = "phayathai_ft"

    SCORE_PHAYATHAI_FT.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(SCORE_PHAYATHAI_FT, index=False)

    log.append(f"Scores saved -> {SCORE_PHAYATHAI_FT}")
    log.append(f"phafin_score: mean={ft_scores.mean():.4f}  "
               f"std={ft_scores.std():.4f}  "
               f"min={ft_scores.min():.4f}  max={ft_scores.max():.4f}")
    log.append(f"Label counts: {pd.Series([score_to_label(s) for s in ft_scores]).value_counts().to_dict()}")

    log_text = "\n".join(log)
    LOG_FILE.write_text(log_text, encoding="utf-8")
    print(log_text.split("\n")[-4])
    print(f"\nFine-tuning complete.")
    print(f"  Model  -> {FT_MODEL_DIR}")
    print(f"  Scores -> {SCORE_PHAYATHAI_FT}")


if __name__ == "__main__":
    main()
