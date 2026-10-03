"""Phase P2c: strictly forward calibration of P2b text predictions.

For each outer block after the first, a one-dimensional ridge calibrator is fit
only on predictions and outcomes from completed earlier outer blocks.  The
current block is never used to choose its calibration.  This tests whether P2b
mainly failed because class-to-return magnitudes were too large.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit


ROOT = Path(__file__).resolve().parents[2]
P2B = ROOT / "results" / "rdfl_phafin" / "p2b_tfidf_label_methods"
OUT = ROOT / "results" / "rdfl_phafin" / "p2c_forward_calibration"
METHODS = ["ZERO", "DIRECT_HUBER", "HARD_RDFL", "ORDINARY_SOFT", "RDFL_SOFT"]
BOOTSTRAP_ITER = 5000
BOOTSTRAP_BLOCK = 10


def fit_calibrator(history: pd.DataFrame) -> dict:
    history = history.sort_values(["Date", "Symbol"]).reset_index(drop=True)
    x = history["prediction"].to_numpy(dtype=float)
    y = history["actual"].to_numpy(dtype=float)
    x_mean, x_scale = float(x.mean()), float(x.std(ddof=1))
    y_mean, y_scale = float(y.mean()), float(y.std(ddof=1))
    if x_scale < 1e-10 or y_scale < 1e-10:
        return {
            "constant": True, "prediction": y_mean, "x_mean": x_mean,
            "x_scale": x_scale, "y_mean": y_mean, "y_scale": y_scale,
            "model": None, "alpha": None,
        }
    x_standard = ((x - x_mean) / x_scale).reshape(-1, 1)
    y_standard = (y - y_mean) / y_scale
    dates = np.array(sorted(history["Date"].unique()))
    splits = []
    if len(dates) >= 8:
        for train_dates_idx, validation_dates_idx in TimeSeriesSplit(n_splits=3).split(dates):
            train_dates = set(dates[train_dates_idx])
            validation_dates = set(dates[validation_dates_idx])
            train_idx = np.flatnonzero(history["Date"].isin(train_dates).to_numpy())
            validation_idx = np.flatnonzero(history["Date"].isin(validation_dates).to_numpy())
            splits.append((train_idx, validation_idx))
    model = RidgeCV(alphas=[0.1, 1.0, 10.0], cv=splits if splits else None)
    model.fit(x_standard, y_standard)
    return {
        "constant": False, "prediction": None, "x_mean": x_mean,
        "x_scale": x_scale, "y_mean": y_mean, "y_scale": y_scale,
        "model": model, "alpha": float(model.alpha_),
    }


def apply_calibrator(calibrator: dict, values: np.ndarray) -> np.ndarray:
    if calibrator["constant"]:
        return np.full(len(values), calibrator["prediction"], dtype=float)
    standardized = ((values - calibrator["x_mean"]) / calibrator["x_scale"]).reshape(-1, 1)
    return calibrator["model"].predict(standardized) * calibrator["y_scale"] + calibrator["y_mean"]


def metrics(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (block, method), group in frame.groupby(["block", "method"]):
        actual = group["actual"].to_numpy(dtype=float)
        forecast = group["calibrated_prediction"].to_numpy(dtype=float)
        nonzero = actual != 0
        rows.append(
            {
                "block": block, "method": method, "n": len(group),
                "rmse": float(np.sqrt(mean_squared_error(actual, forecast))),
                "mae": float(mean_absolute_error(actual, forecast)),
                "directional_accuracy_all": float(np.mean(np.sign(actual) == np.sign(forecast))),
                "directional_accuracy_actual_nonzero": float(np.mean(np.sign(actual[nonzero]) == np.sign(forecast[nonzero]))) if nonzero.any() else np.nan,
                "normalized_mse": float(group["calibrated_normalized_squared_error"].mean()),
            }
        )
    return pd.DataFrame(rows)


def moving_block_test(predictions: pd.DataFrame, competitor: str) -> dict:
    losses = predictions.pivot(
        index=["Date", "Symbol"], columns="method", values="calibrated_normalized_squared_error"
    ).dropna(subset=[competitor, "RDFL_SOFT"])
    daily = (losses[competitor] - losses["RDFL_SOFT"]).groupby(level="Date").mean().sort_index().to_numpy()
    observed = float(daily.mean())
    centered = daily - observed
    rng = np.random.default_rng(5100 + METHODS.index(competitor))
    starts = np.arange(len(daily))

    def bootstrap(values: np.ndarray) -> np.ndarray:
        output = np.empty(BOOTSTRAP_ITER)
        for iteration in range(BOOTSTRAP_ITER):
            sample = []
            while len(sample) < len(values):
                start = int(rng.choice(starts))
                indices = (start + np.arange(BOOTSTRAP_BLOCK)) % len(values)
                sample.extend(values[indices].tolist())
            output[iteration] = np.mean(sample[: len(values)])
        return output

    distribution = bootstrap(daily)
    null_distribution = bootstrap(centered)
    return {
        "competitor": competitor,
        "estimand": "calibrated normalized loss(competitor) - loss(RDFL); positive favors RDFL",
        "n_dates": len(daily), "mean_difference": observed,
        "ci_95": [float(np.quantile(distribution, 0.025)), float(np.quantile(distribution, 0.975))],
        "raw_two_sided_p": float((np.sum(np.abs(null_distribution) >= abs(observed)) + 1) / (BOOTSTRAP_ITER + 1)),
    }


def add_holm(results: list[dict]) -> None:
    order = sorted(range(len(results)), key=lambda index: results[index]["raw_two_sided_p"])
    running = 0.0
    for rank, index in enumerate(order):
        adjusted = min(1.0, (len(results) - rank) * results[index]["raw_two_sided_p"])
        running = max(running, adjusted)
        results[index]["holm_adjusted_p"] = running


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(P2B / "predictions.csv", low_memory=False)
    raw["Date"] = pd.to_datetime(raw["Date"], errors="raise")
    block_order = (
        raw.groupby("block")["Date"].min().sort_values().index.tolist()
    )
    if len(block_order) < 2:
        raise RuntimeError("At least two completed outer blocks are required for forward calibration")

    calibrated_parts = []
    records = []
    for block_position, block in enumerate(block_order[1:], start=1):
        block_start = raw.loc[raw["block"] == block, "Date"].min()
        for method in METHODS:
            current = raw[(raw["block"] == block) & (raw["method"] == method)].copy()
            if method == "ZERO":
                current["calibrated_prediction"] = 0.0
                records.append(
                    {"block": block, "method": method, "history_rows": 0, "alpha": np.nan, "raw_sd": 0.0, "calibrated_sd": 0.0}
                )
            else:
                history = raw[(raw["Date"] < block_start) & (raw["method"] == method)].copy()
                calibrator = fit_calibrator(history)
                current["calibrated_prediction"] = apply_calibrator(
                    calibrator, current["prediction"].to_numpy(dtype=float)
                )
                records.append(
                    {
                        "block": block, "method": method, "history_rows": len(history),
                        "alpha": calibrator["alpha"],
                        "raw_sd": float(current["prediction"].std(ddof=1)),
                        "calibrated_sd": float(current["calibrated_prediction"].std(ddof=1)),
                    }
                )
            current["calibrated_normalized_squared_error"] = (
                (current["actual"] - current["calibrated_prediction"]) / current["stock_training_scale"]
            ) ** 2
            current["calibration_history_ends_before"] = block_start
            calibrated_parts.append(current)

    predictions = pd.concat(calibrated_parts, ignore_index=True)
    block_table = metrics(predictions)
    aggregate = metrics(predictions.assign(block="ALL"))
    comparisons = [
        moving_block_test(predictions, method)
        for method in ["ZERO", "DIRECT_HUBER", "HARD_RDFL", "ORDINARY_SOFT"]
    ]
    add_holm(comparisons)

    predictions.to_csv(OUT / "calibrated_predictions.csv", index=False, encoding="utf-8-sig")
    block_table.to_csv(OUT / "block_metrics.csv", index=False, encoding="utf-8-sig")
    aggregate.to_csv(OUT / "aggregate_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(records).to_csv(OUT / "calibration_manifest.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(comparisons).to_csv(OUT / "rdfl_pairwise_inference.csv", index=False, encoding="utf-8-sig")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "EXPLORATORY_PILOT_AFTER_P2B_REVIEW",
        "calibration": "global intercept/slope ridge fitted only on completed prior OOS blocks",
        "warmup_block_excluded": block_order[0],
        "evaluated_blocks": len(block_order) - 1,
        "test_rows_per_method": int(len(predictions) / predictions["method"].nunique()),
        "aggregate_metrics": aggregate.to_dict(orient="records"),
        "rdfl_pairwise_inference": comparisons,
        "interpretation_guard": "This analysis was motivated after reviewing P2b and cannot serve as untouched confirmation.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lookup = aggregate.set_index("method")
    lines = [
        "# Phase P2c Forward Calibration",
        "",
        "Status: **EXPLORATORY — DESIGNED AFTER REVIEWING P2b**",
        "",
        f"Warm-up block excluded: {block_order[0]}; evaluated blocks: {len(block_order) - 1}",
        "",
        "| Method | RMSE | MAE | Directional accuracy (nonzero actual) | Normalized MSE |",
        "|---|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        row = lookup.loc[method]
        lines.append(
            f"| {method} | {row['rmse']:.6f} | {row['mae']:.6f} | "
            f"{row['directional_accuracy_actual_nonzero']:.4f} | {row['normalized_mse']:.6f} |"
        )
    lines.extend(["", "Positive pairwise difference favors calibrated RDFL.", ""])
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
