"""Phase P2b pilot: compare weak-label methods with a leakage-safe TF-IDF encoder.

The encoder is fitted separately inside each outer training window.  This is a
cheap representation diagnostic before spending GPU time on a Transformer.  It
tests RDFL soft labels against hard RDFL labels, ordinary soft labels, and direct
return regression on identical out-of-sample news bags.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier, SGDRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "results" / "rdfl_phafin" / "p1_pilot_labels"
OUT = ROOT / "results" / "rdfl_phafin" / "p2b_tfidf_label_methods"
SEEDS = [11, 23, 42, 71, 101]
BOOTSTRAP_ITER = 5000
BOOTSTRAP_BLOCK = 10
OUTER_STARTS = pd.to_datetime(
    [
        "2024-08-01", "2024-11-01", "2025-02-01", "2025-05-01",
        "2025-08-01", "2025-11-01", "2026-02-01", "2026-05-01",
    ]
)
METHODS = ["ZERO", "DIRECT_HUBER", "HARD_RDFL", "ORDINARY_SOFT", "RDFL_SOFT"]
LABEL_TO_INT = {"NEGATIVE": 0, "LOW_RESPONSE": 1, "POSITIVE": 2}


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def aligned_probabilities(model: SGDClassifier, matrix) -> np.ndarray:
    raw = model.predict_proba(matrix)
    result = np.zeros((matrix.shape[0], 3), dtype=float)
    for position, label in enumerate(model.classes_):
        result[:, int(label)] = raw[:, position]
    return result


def fit_soft_ensemble(x_train, probabilities: np.ndarray, weights: np.ndarray, x_test) -> np.ndarray:
    expanded_x = sparse.vstack([x_train, x_train, x_train], format="csr")
    labels = np.concatenate(
        [np.zeros(x_train.shape[0], dtype=int), np.ones(x_train.shape[0], dtype=int), np.full(x_train.shape[0], 2, dtype=int)]
    )
    expanded_weights = np.concatenate(
        [probabilities[:, 0] * weights, probabilities[:, 1] * weights, probabilities[:, 2] * weights]
    )
    keep = expanded_weights > 1e-10
    predictions = []
    for seed in SEEDS:
        model = SGDClassifier(
            loss="log_loss", penalty="l2", alpha=1e-4, max_iter=3000,
            tol=1e-4, average=True, random_state=seed,
        )
        model.fit(expanded_x[keep], labels[keep], sample_weight=expanded_weights[keep])
        predictions.append(aligned_probabilities(model, x_test))
    return np.mean(predictions, axis=0)


def fit_hard_ensemble(x_train, labels: np.ndarray, x_test) -> np.ndarray:
    predictions = []
    for seed in SEEDS:
        model = SGDClassifier(
            loss="log_loss", penalty="l2", alpha=1e-4, max_iter=3000,
            tol=1e-4, average=True, random_state=seed,
        )
        model.fit(x_train, labels)
        predictions.append(aligned_probabilities(model, x_test))
    return np.mean(predictions, axis=0)


def fit_direct_ensemble(x_train, target: np.ndarray, x_test) -> np.ndarray:
    center = float(np.mean(target))
    scale = float(np.std(target, ddof=1))
    if not np.isfinite(scale) or scale < 1e-8:
        raise RuntimeError("Degenerate direct-return training scale")
    standardized = (target - center) / scale
    predictions = []
    for seed in SEEDS:
        model = SGDRegressor(
            loss="huber", epsilon=1.35, penalty="l2", alpha=1e-4,
            max_iter=3000, tol=1e-4, average=True, random_state=seed,
        )
        model.fit(x_train, standardized)
        predictions.append(model.predict(x_test) * scale + center)
    return np.mean(predictions, axis=0)


def class_centers(target: np.ndarray, probabilities: np.ndarray, confidence: np.ndarray | None = None) -> np.ndarray:
    if confidence is None:
        confidence = np.ones(len(target), dtype=float)
    centers = np.empty(3, dtype=float)
    fallback = float(np.mean(target))
    for label in range(3):
        weight = probabilities[:, label] * confidence
        centers[label] = float(np.sum(weight * target) / np.sum(weight)) if np.sum(weight) > 1e-10 else fallback
    return centers


def load_bags() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(P1 / "stock_day_labels_pilot.csv", low_memory=False)
    panel["Date"] = pd.to_datetime(panel["Date"], errors="raise")
    panel["retain_for_text_training"] = panel["retain_for_text_training"].astype(str).str.lower().eq("true")
    panel["outcome_data_valid"] = panel["outcome_data_valid"].astype(str).str.lower().eq("true")
    articles = pd.read_csv(P1 / "article_to_stock_day_pilot.csv", low_memory=False)
    articles["decision_date"] = pd.to_datetime(articles["decision_date"], errors="coerce")
    assigned = articles.dropna(subset=["decision_date"]).copy()
    assigned["model_text"] = assigned["model_text"].fillna("").astype(str).str.strip()
    assigned = assigned[assigned["model_text"].ne("")]
    text_bags = (
        assigned.groupby(["Symbol", "decision_date"], as_index=False)
        .agg(
            bag_text=("model_text", lambda values: " [ARTICLE] ".join(values.astype(str))),
            bag_article_count=("article_id", "nunique"),
        )
        .rename(columns={"decision_date": "Date"})
    )
    bags = panel.merge(text_bags, on=["Symbol", "Date"], how="inner", validate="one_to_one")
    bags = bags[
        np.isfinite(pd.to_numeric(bags["target_open_close"], errors="coerce"))
        & bags["outcome_data_valid"]
    ].copy()
    return panel, bags.sort_values(["Date", "Symbol"]).reset_index(drop=True)


def ordinary_probabilities(frame: pd.DataFrame, temperature: float = 1.0) -> np.ndarray:
    z = frame["residual_z"].to_numpy(dtype=float)
    volume = frame["volume_deviation"].to_numpy(dtype=float)
    logits = np.column_stack([-z / temperature, 1.0 - np.abs(z) / temperature - volume / temperature, z / temperature])
    return softmax(logits)


def block_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (block, method), group in predictions.groupby(["block", "method"]):
        actual = group["actual"].to_numpy(dtype=float)
        forecast = group["prediction"].to_numpy(dtype=float)
        nonzero = actual != 0
        rows.append(
            {
                "block": block,
                "method": method,
                "n": len(group),
                "rmse": float(np.sqrt(mean_squared_error(actual, forecast))),
                "mae": float(mean_absolute_error(actual, forecast)),
                "directional_accuracy_all": float(np.mean(np.sign(actual) == np.sign(forecast))),
                "directional_accuracy_actual_nonzero": float(np.mean(np.sign(actual[nonzero]) == np.sign(forecast[nonzero]))) if nonzero.any() else np.nan,
                "normalized_mse": float(group["normalized_squared_error"].mean()),
            }
        )
    return pd.DataFrame(rows)


def moving_block_test(predictions: pd.DataFrame, competitor: str) -> dict:
    losses = predictions.pivot(
        index=["Date", "Symbol"], columns="method", values="normalized_squared_error"
    ).dropna(subset=[competitor, "RDFL_SOFT"])
    difference = losses[competitor] - losses["RDFL_SOFT"]
    daily = difference.groupby(level="Date").mean().sort_index().to_numpy(dtype=float)
    observed = float(daily.mean())
    centered = daily - observed
    rng = np.random.default_rng(4200 + METHODS.index(competitor))
    starts = np.arange(len(daily))

    def resample(values: np.ndarray) -> np.ndarray:
        output = np.empty(BOOTSTRAP_ITER)
        for iteration in range(BOOTSTRAP_ITER):
            sample = []
            while len(sample) < len(values):
                start = int(rng.choice(starts))
                indices = (start + np.arange(BOOTSTRAP_BLOCK)) % len(values)
                sample.extend(values[indices].tolist())
            output[iteration] = np.mean(sample[: len(values)])
        return output

    bootstrap = resample(daily)
    null_bootstrap = resample(centered)
    return {
        "competitor": competitor,
        "estimand": "normalized squared loss(competitor) - loss(RDFL_SOFT); positive favors RDFL",
        "n_dates": len(daily),
        "mean_difference": observed,
        "ci_95": [float(np.quantile(bootstrap, 0.025)), float(np.quantile(bootstrap, 0.975))],
        "raw_two_sided_p": float((np.sum(np.abs(null_bootstrap) >= abs(observed)) + 1) / (BOOTSTRAP_ITER + 1)),
    }


def add_holm(results: list[dict]) -> None:
    order = sorted(range(len(results)), key=lambda i: results[i]["raw_two_sided_p"])
    running = 0.0
    m = len(results)
    for rank, index in enumerate(order):
        adjusted = min(1.0, (m - rank) * results[index]["raw_two_sided_p"])
        running = max(running, adjusted)
        results[index]["holm_adjusted_p"] = running


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    panel, bags = load_bags()
    prediction_parts = []
    fold_records = []

    for fold in range(len(OUTER_STARTS) - 1):
        start, stop = OUTER_STARTS[fold], OUTER_STARTS[fold + 1]
        train = bags[bags["Date"] < start].copy().reset_index(drop=True)
        test = bags[(bags["Date"] >= start) & (bags["Date"] < stop)].copy().reset_index(drop=True)
        retained = train[train["retain_for_text_training"]].copy()
        ordinary = train[np.isfinite(train[["residual_z", "volume_deviation"]].to_numpy(dtype=float)).all(axis=1)].copy()
        if len(test) == 0 or len(retained) < 100 or len(ordinary) < 100:
            continue
        label_counts = retained["weak_label"].value_counts()
        if any(label_counts.get(label, 0) < 10 for label in LABEL_TO_INT):
            continue

        vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=3, max_df=0.98,
            max_features=20_000, sublinear_tf=True, norm="l2", dtype=np.float32,
        )
        x_all_train = vectorizer.fit_transform(train["bag_text"])
        x_test = vectorizer.transform(test["bag_text"])
        direct_prediction = fit_direct_ensemble(
            x_all_train, train["target_open_close"].to_numpy(dtype=float), x_test
        )

        retained_positions = retained.index.to_numpy()
        x_retained = x_all_train[retained_positions]
        rdfl_prob_train = retained[["p_negative", "p_low_response", "p_positive"]].to_numpy(dtype=float)
        rdfl_confidence = retained["label_confidence"].to_numpy(dtype=float)
        rdfl_test_prob = fit_soft_ensemble(x_retained, rdfl_prob_train, rdfl_confidence, x_test)
        rdfl_centers = class_centers(
            retained["target_open_close"].to_numpy(dtype=float), rdfl_prob_train, rdfl_confidence
        )
        rdfl_prediction = rdfl_test_prob @ rdfl_centers

        hard_labels = retained["weak_label"].map(LABEL_TO_INT).to_numpy(dtype=int)
        hard_test_prob = fit_hard_ensemble(x_retained, hard_labels, x_test)
        hard_train_prob = np.eye(3, dtype=float)[hard_labels]
        hard_centers = class_centers(retained["target_open_close"].to_numpy(dtype=float), hard_train_prob)
        hard_prediction = hard_test_prob @ hard_centers

        ordinary_positions = ordinary.index.to_numpy()
        ordinary_prob_train = ordinary_probabilities(ordinary)
        ordinary_test_prob = fit_soft_ensemble(
            x_all_train[ordinary_positions], ordinary_prob_train, np.ones(len(ordinary)), x_test
        )
        ordinary_centers = class_centers(
            ordinary["target_open_close"].to_numpy(dtype=float), ordinary_prob_train
        )
        ordinary_prediction = ordinary_test_prob @ ordinary_centers

        block = f"{start.date()}_{(stop - pd.Timedelta(days=1)).date()}"
        training_scales = (
            panel[(panel["Date"] < start) & panel["outcome_data_valid"]]
            .groupby("Symbol")["target_open_close"].std(ddof=1).clip(lower=1e-6)
        )
        predictions = {
            "ZERO": np.zeros(len(test)),
            "DIRECT_HUBER": direct_prediction,
            "HARD_RDFL": hard_prediction,
            "ORDINARY_SOFT": ordinary_prediction,
            "RDFL_SOFT": rdfl_prediction,
        }
        for method, forecast in predictions.items():
            output = test[["Date", "Symbol", "target_open_close"]].copy()
            output = output.rename(columns={"target_open_close": "actual"})
            output["prediction"] = forecast
            output["method"] = method
            output["block"] = block
            output["train_end"] = train["Date"].max()
            output["stock_training_scale"] = output["Symbol"].map(training_scales)
            output["normalized_squared_error"] = (
                (output["actual"] - output["prediction"]) / output["stock_training_scale"]
            ) ** 2
            prediction_parts.append(output)
        fold_records.append(
            {
                "block": block,
                "train_bags": len(train),
                "test_bags": len(test),
                "rdfl_training_bags": len(retained),
                "ordinary_training_bags": len(ordinary),
                "vocabulary_size": len(vectorizer.vocabulary_),
                "rdfl_negative": int(label_counts.get("NEGATIVE", 0)),
                "rdfl_low_response": int(label_counts.get("LOW_RESPONSE", 0)),
                "rdfl_positive": int(label_counts.get("POSITIVE", 0)),
            }
        )

    if not prediction_parts:
        raise RuntimeError("No eligible outer folds; inspect label warm-up and class counts")
    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = block_metrics(predictions)
    aggregate = block_metrics(predictions.assign(block="ALL"))
    comparisons = [moving_block_test(predictions, method) for method in ["DIRECT_HUBER", "HARD_RDFL", "ORDINARY_SOFT"]]
    add_holm(comparisons)

    predictions.to_csv(OUT / "predictions.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "block_metrics.csv", index=False, encoding="utf-8-sig")
    aggregate.to_csv(OUT / "aggregate_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fold_records).to_csv(OUT / "fold_manifest.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(comparisons).to_csv(OUT / "rdfl_pairwise_inference.csv", index=False, encoding="utf-8-sig")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PILOT_ONLY_NOT_CONFIRMATORY",
        "representation": "training-window-only Thai character TF-IDF (3-5 grams)",
        "outer_blocks": int(predictions["block"].nunique()),
        "test_rows_per_method": int(len(predictions) / predictions["method"].nunique()),
        "seeds_ensembled": SEEDS,
        "aggregate_metrics": aggregate.to_dict(orient="records"),
        "rdfl_pairwise_inference": comparisons,
        "versions": {
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "limitations": [
            "TF-IDF is a representation diagnostic, not the final Transformer",
            "P0 timestamp/calendar/price-adjustment gates remain unresolved",
            "text-only news-day evaluation; downstream financial fusion is a later phase",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    metric_lookup = aggregate.set_index("method")
    lines = [
        "# Phase P2b TF-IDF Weak-Label Comparison",
        "",
        "Status: **PILOT ONLY — REPRESENTATION DIAGNOSTIC**",
        "",
        f"Outer blocks: {summary['outer_blocks']}; test rows per method: {summary['test_rows_per_method']:,}",
        "",
        "| Method | RMSE | MAE | Directional accuracy | Normalized MSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        row = metric_lookup.loc[method]
        lines.append(
            f"| {method} | {row['rmse']:.6f} | {row['mae']:.6f} | "
            f"{row['directional_accuracy_all']:.4f} | {row['normalized_mse']:.6f} |"
        )
    lines.extend(["", "Pairwise estimand is competitor loss minus RDFL loss; positive favors RDFL.", ""])
    for result in comparisons:
        lines.append(
            f"- {result['competitor']}: difference={result['mean_difference']:.6f}, "
            f"95% CI=[{result['ci_95'][0]:.6f}, {result['ci_95'][1]:.6f}], "
            f"Holm p={result['holm_adjusted_p']:.6f}"
        )
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
