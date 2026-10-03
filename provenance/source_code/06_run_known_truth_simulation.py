"""Phase P3: known-truth simulation for RDFL weak supervision.

The data-generating mechanisms below never call the RDFL labeling rule.  RDFL,
hard labels, ordinary soft labels, direct outcome regression, a random-label
control, and an oracle are trained afterward and evaluated against latent net
effects that are unavailable in the real data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import f1_score


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "rdfl_phafin" / "p3_known_truth_simulation"
SEEDS = list(range(1001, 1031))
N_TRAIN = 2400
N_TEST = 1200
N_FEATURES = 20
CONFIDENCE_MIN = 0.70
BOOTSTRAP_ITER = 5000
EPSILON = 1e-10
METHODS = ["ZERO", "DIRECT", "RANDOM_MATCHED", "HARD_RDFL", "ORDINARY_SOFT", "RDFL_SOFT", "ORACLE_CLASS"]

SCENARIOS = {
    "null_effect": {"signal": 0.0, "noise": 1.0, "response": 1.0, "volume_link": 0.0},
    "strong_signal": {"signal": 1.0, "noise": 0.45, "response": 1.0, "volume_link": 1.0},
    "high_noise": {"signal": 1.0, "noise": 1.80, "response": 1.0, "volume_link": 0.8},
    "cancellation": {"signal": 1.0, "noise": 0.70, "response": 1.0, "volume_link": 0.8},
    "anticipation": {"signal": 1.0, "noise": 0.70, "response": 0.30, "volume_link": 0.7},
    "stale_price": {"signal": 1.0, "noise": 0.70, "response": 1.0, "volume_link": 0.9},
    "nonrandom_missing": {"signal": 1.0, "noise": 0.70, "response": 1.0, "volume_link": 0.8},
    "regime_shift": {"signal": 1.0, "noise": 0.70, "response": 1.0, "volume_link": 0.8},
}


def robust_standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    center = float(np.median(train))
    scale = float(1.4826 * np.median(np.abs(train - center)))
    scale = max(scale, EPSILON)
    return (train - center) / scale, (test - center) / scale, center, scale


def latent_function(features: np.ndarray, shifted: bool = False) -> np.ndarray:
    if shifted:
        raw = -0.55 * features[:, 0] + 0.70 * features[:, 5] - 0.45 * np.tanh(features[:, 2]) + 0.30 * features[:, 6] * features[:, 7]
    else:
        raw = 0.70 * features[:, 0] - 0.50 * features[:, 1] + 0.40 * np.tanh(features[:, 2]) + 0.30 * features[:, 3] * features[:, 4]
    return raw / max(float(np.std(raw, ddof=1)), EPSILON)


def generate(seed: int, scenario: str) -> dict:
    rng = np.random.default_rng(seed)
    params = SCENARIOS[scenario]
    x_train = rng.normal(size=(N_TRAIN, N_FEATURES))
    x_test = rng.normal(size=(N_TEST, N_FEATURES))
    base_train = latent_function(x_train)
    base_test = latent_function(x_test, shifted=scenario == "regime_shift")

    if scenario == "cancellation":
        first_train = params["signal"] * base_train
        first_test = params["signal"] * base_test
        second_train = -0.85 * first_train + 0.30 * latent_function(np.roll(x_train, 5, axis=1))
        second_test = -0.85 * first_test + 0.30 * latent_function(np.roll(x_test, 5, axis=1))
        theta_train = (first_train + second_train) / np.sqrt(2.0)
        theta_test = (first_test + second_test) / np.sqrt(2.0)
        individual_train = np.maximum(np.abs(first_train), np.abs(second_train))
        individual_test = np.maximum(np.abs(first_test), np.abs(second_test))
    else:
        theta_train = params["signal"] * base_train
        theta_test = params["signal"] * base_test
        individual_train = np.abs(theta_train)
        individual_test = np.abs(theta_test)

    observed_train = params["response"] * theta_train + params["noise"] * rng.normal(size=N_TRAIN)
    observed_test = params["response"] * theta_test + params["noise"] * rng.normal(size=N_TEST)

    if scenario == "stale_price":
        stale_train = rng.random(N_TRAIN) < 0.30
        stale_test = rng.random(N_TEST) < 0.30
        observed_train[stale_train] = 0.05 * rng.normal(size=stale_train.sum())
        observed_test[stale_test] = 0.05 * rng.normal(size=stale_test.sum())

    log_volume_train = params["volume_link"] * np.abs(theta_train) + rng.normal(scale=0.75, size=N_TRAIN)
    log_volume_test = params["volume_link"] * np.abs(theta_test) + rng.normal(scale=0.75, size=N_TEST)
    volume_train, volume_test, _, _ = robust_standardize(log_volume_train, log_volume_test)
    volume_deviation_train = np.abs(volume_train)
    volume_deviation_test = np.abs(volume_test)

    keep_train = np.ones(N_TRAIN, dtype=bool)
    if scenario == "nonrandom_missing":
        probability = 0.90 - 0.55 / (1.0 + np.exp(-2.0 * (np.abs(theta_train) - 0.8)))
        keep_train = rng.random(N_TRAIN) < probability

    reference_scale = max(float(np.std(theta_train, ddof=1)), EPSILON)
    threshold = 0.35 * reference_scale
    true_train = np.where(theta_train < -threshold, 0, np.where(theta_train > threshold, 2, 1)).astype(int)
    true_test = np.where(theta_test < -threshold, 0, np.where(theta_test > threshold, 2, 1)).astype(int)
    return {
        "x_train": x_train, "x_test": x_test,
        "theta_train": theta_train, "theta_test": theta_test,
        "observed_train": observed_train, "observed_test": observed_test,
        "volume_train": volume_deviation_train, "volume_test": volume_deviation_test,
        "keep_train": keep_train, "true_train": true_train, "true_test": true_test,
        "individual_train": individual_train, "individual_test": individual_test,
        "threshold": threshold,
    }


def rdfl_labels(observed: np.ndarray, volume: np.ndarray) -> dict:
    z, _, _, _ = robust_standardize(observed, observed)
    magnitude = np.abs(z)
    q_low, q_high = np.quantile(magnitude, [0.30, 0.70])
    v_low, v_high = np.quantile(volume, [0.50, 0.90])
    low_response = np.clip((q_high - magnitude) / max(q_high - q_low, EPSILON), 0.0, 1.0)
    high_response = 1.0 - low_response
    normal_volume = np.clip((v_high - volume) / max(v_high - v_low, EPSILON), 0.0, 1.0)
    memberships = np.column_stack(
        [high_response * (z < 0), np.minimum(low_response, normal_volume), high_response * (z > 0)]
    )
    total = memberships.sum(axis=1)
    probabilities = np.divide(
        memberships, total[:, None], out=np.zeros_like(memberships), where=total[:, None] > EPSILON
    )
    confidence = memberships.max(axis=1)
    retain = (total > EPSILON) & (confidence >= CONFIDENCE_MIN)
    return {
        "z": z, "probabilities": probabilities, "confidence": confidence,
        "retain": retain, "hard": probabilities.argmax(axis=1),
    }


def ordinary_labels(observed: np.ndarray, volume: np.ndarray) -> np.ndarray:
    z, _, _, _ = robust_standardize(observed, observed)
    logits = np.column_stack([-z, 1.0 - np.abs(z) - volume, z])
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def fit_soft_classifier(x: np.ndarray, probabilities: np.ndarray, weights: np.ndarray) -> dict:
    expanded_x = np.vstack([x, x, x])
    labels = np.concatenate(
        [np.zeros(len(x), dtype=int), np.ones(len(x), dtype=int), np.full(len(x), 2, dtype=int)]
    )
    expanded_weights = np.concatenate(
        [probabilities[:, 0] * weights, probabilities[:, 1] * weights, probabilities[:, 2] * weights]
    )
    keep = expanded_weights > EPSILON
    model = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs")
    model.fit(expanded_x[keep], labels[keep], sample_weight=expanded_weights[keep])
    return {"kind": "model", "model": model}


def fit_hard_classifier(x: np.ndarray, labels: np.ndarray) -> dict:
    classes = np.unique(labels)
    if len(classes) == 1:
        probabilities = np.zeros(3, dtype=float)
        probabilities[int(classes[0])] = 1.0
        return {"kind": "constant", "probabilities": probabilities}
    model = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs")
    model.fit(x, labels)
    return {"kind": "model", "model": model}


def predict_probabilities(fitted: dict, x: np.ndarray) -> np.ndarray:
    if fitted["kind"] == "constant":
        return np.tile(fitted["probabilities"], (len(x), 1))
    raw = fitted["model"].predict_proba(x)
    aligned = np.zeros((len(x), 3), dtype=float)
    for column, label in enumerate(fitted["model"].classes_):
        aligned[:, int(label)] = raw[:, column]
    return aligned


def class_centers(target: np.ndarray, probabilities: np.ndarray, weights: np.ndarray) -> np.ndarray:
    centers = np.empty(3, dtype=float)
    fallback = float(np.mean(target))
    for label in range(3):
        combined = probabilities[:, label] * weights
        centers[label] = float(np.sum(combined * target) / np.sum(combined)) if combined.sum() > EPSILON else fallback
    return centers


def classification_metrics(true: np.ndarray, probabilities: np.ndarray) -> dict:
    prediction = probabilities.argmax(axis=1)
    present = sorted(np.unique(true).tolist())
    one_hot = np.eye(3)[true]
    return {
        "accuracy": float(np.mean(prediction == true)),
        "macro_f1_present": float(f1_score(true, prediction, labels=present, average="macro", zero_division=0)),
        "brier": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
    }


def method_row(
    scenario: str, seed: int, method: str, theta: np.ndarray, theta_prediction: np.ndarray,
    true_class: np.ndarray, probabilities: np.ndarray | None, coverage: float,
    ess: float, false_net_absence: float, false_causal_absence: float,
) -> dict:
    mse = float(np.mean((theta - theta_prediction) ** 2))
    zero_mse = float(np.mean(theta**2))
    if probabilities is None:
        predicted_class = np.where(theta_prediction < 0, 0, np.where(theta_prediction > 0, 2, 1))
        accuracy = float(np.mean(predicted_class == true_class))
        macro = float(f1_score(true_class, predicted_class, labels=sorted(np.unique(true_class)), average="macro", zero_division=0))
        brier = np.nan
    else:
        scores = classification_metrics(true_class, probabilities)
        accuracy, macro, brier = scores["accuracy"], scores["macro_f1_present"], scores["brier"]
    return {
        "scenario": scenario, "seed": seed, "method": method,
        "latent_effect_mse": mse,
        "latent_effect_skill_vs_zero": (1.0 - mse / zero_mse) if zero_mse > EPSILON else np.nan,
        "mean_abs_predicted_effect": float(np.mean(np.abs(theta_prediction))),
        "class_accuracy": accuracy, "macro_f1_present": macro, "brier": brier,
        "training_coverage": coverage, "effective_sample_size": ess,
        "false_net_absence": false_net_absence,
        "false_causal_absence": false_causal_absence,
    }


def run_replication(seed: int, scenario: str) -> list[dict]:
    data = generate(seed, scenario)
    keep = data["keep_train"]
    x_train = data["x_train"][keep]
    observed_train = data["observed_train"][keep]
    volume_train = data["volume_train"][keep]
    theta_train = data["theta_train"][keep]
    true_train = data["true_train"][keep]
    individual_train = data["individual_train"][keep]
    x_test = data["x_test"]
    theta_test = data["theta_test"]
    true_test = data["true_test"]
    threshold = data["threshold"]
    rows = []

    zero_prob = np.tile(np.array([0.0, 1.0, 0.0]), (len(x_test), 1))
    rows.append(method_row(
        scenario, seed, "ZERO", theta_test, np.zeros_like(theta_test), true_test, zero_prob,
        1.0, float(len(x_train)), np.nan, np.nan,
    ))

    direct = Ridge(alpha=1.0).fit(x_train, observed_train)
    direct_prediction = direct.predict(x_test)
    rows.append(method_row(
        scenario, seed, "DIRECT", theta_test, direct_prediction, true_test, None,
        1.0, float(len(x_train)), np.nan, np.nan,
    ))

    rdfl = rdfl_labels(observed_train, volume_train)
    retained = rdfl["retain"]
    probabilities = rdfl["probabilities"][retained]
    confidence = rdfl["confidence"][retained]
    coverage = float(retained.mean())
    ess = float(confidence.sum() ** 2 / max(np.sum(confidence**2), EPSILON))
    true_retained = true_train[retained]
    individual_retained = individual_train[retained]
    absence_weight = probabilities[:, 1] * confidence
    false_net_absence = float(
        np.sum(absence_weight * (true_retained != 1)) / max(absence_weight.sum(), EPSILON)
    )
    false_causal_absence = float(
        np.sum(absence_weight * (individual_retained > threshold)) / max(absence_weight.sum(), EPSILON)
    )

    rdfl_model = fit_soft_classifier(x_train[retained], probabilities, confidence)
    rdfl_test_probability = predict_probabilities(rdfl_model, x_test)
    rdfl_centers = class_centers(observed_train[retained], probabilities, confidence)
    rdfl_effect = rdfl_test_probability @ rdfl_centers
    rows.append(method_row(
        scenario, seed, "RDFL_SOFT", theta_test, rdfl_effect, true_test, rdfl_test_probability,
        coverage, ess, false_net_absence, false_causal_absence,
    ))

    hard_labels = rdfl["hard"][retained]
    hard_model = fit_hard_classifier(x_train[retained], hard_labels)
    hard_test_probability = predict_probabilities(hard_model, x_test)
    hard_train_probability = np.eye(3)[hard_labels]
    hard_centers = class_centers(observed_train[retained], hard_train_probability, np.ones(retained.sum()))
    hard_effect = hard_test_probability @ hard_centers
    rows.append(method_row(
        scenario, seed, "HARD_RDFL", theta_test, hard_effect, true_test, hard_test_probability,
        coverage, float(retained.sum()), false_net_absence, false_causal_absence,
    ))

    rng = np.random.default_rng(seed + 90_000)
    randomized_probability = probabilities[rng.permutation(len(probabilities))]
    random_model = fit_soft_classifier(x_train[retained], randomized_probability, confidence)
    random_test_probability = predict_probabilities(random_model, x_test)
    random_centers = class_centers(observed_train[retained], randomized_probability, confidence)
    random_effect = random_test_probability @ random_centers
    rows.append(method_row(
        scenario, seed, "RANDOM_MATCHED", theta_test, random_effect, true_test, random_test_probability,
        coverage, ess, false_net_absence, false_causal_absence,
    ))

    ordinary_probability = ordinary_labels(observed_train, volume_train)
    ordinary_model = fit_soft_classifier(x_train, ordinary_probability, np.ones(len(x_train)))
    ordinary_test_probability = predict_probabilities(ordinary_model, x_test)
    ordinary_centers = class_centers(observed_train, ordinary_probability, np.ones(len(x_train)))
    ordinary_effect = ordinary_test_probability @ ordinary_centers
    rows.append(method_row(
        scenario, seed, "ORDINARY_SOFT", theta_test, ordinary_effect, true_test, ordinary_test_probability,
        1.0, float(len(x_train)), np.nan, np.nan,
    ))

    oracle_model = fit_hard_classifier(x_train, true_train)
    oracle_test_probability = predict_probabilities(oracle_model, x_test)
    oracle_train_probability = np.eye(3)[true_train]
    oracle_centers = class_centers(theta_train, oracle_train_probability, np.ones(len(x_train)))
    oracle_effect = oracle_test_probability @ oracle_centers
    rows.append(method_row(
        scenario, seed, "ORACLE_CLASS", theta_test, oracle_effect, true_test, oracle_test_probability,
        1.0, float(len(x_train)), 0.0, 0.0,
    ))
    return rows


def bootstrap_pair(raw: pd.DataFrame, scenario: str, competitor: str, metric: str) -> dict:
    subset = raw[(raw["scenario"] == scenario) & raw["method"].isin([competitor, "RDFL_SOFT"])]
    wide = subset.pivot(index="seed", columns="method", values=metric).dropna()
    difference = wide[competitor].to_numpy() - wide["RDFL_SOFT"].to_numpy()
    rng = np.random.default_rng(700_000 + sum(map(ord, scenario + competitor + metric)))
    distribution = np.empty(BOOTSTRAP_ITER)
    for iteration in range(BOOTSTRAP_ITER):
        distribution[iteration] = rng.choice(difference, size=len(difference), replace=True).mean()
    return {
        "scenario": scenario, "metric": metric, "competitor": competitor,
        "estimand": f"{metric}(competitor)-{metric}(RDFL); positive favors RDFL for loss metrics",
        "mean_difference": float(difference.mean()),
        "ci_95": [float(np.quantile(distribution, 0.025)), float(np.quantile(distribution, 0.975))],
        "replications": len(difference),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            rows.extend(run_replication(seed, scenario))
        print(f"completed {scenario}: {len(SEEDS)} replications", flush=True)
    raw = pd.DataFrame(rows)
    raw.to_csv(OUT / "replication_metrics.csv", index=False, encoding="utf-8-sig")

    metrics = [
        "latent_effect_mse", "latent_effect_skill_vs_zero", "mean_abs_predicted_effect",
        "class_accuracy", "macro_f1_present", "brier", "training_coverage",
        "effective_sample_size", "false_net_absence", "false_causal_absence",
    ]
    summary = (
        raw.groupby(["scenario", "method"])[metrics]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    summary.columns = [
        "_".join(str(part) for part in column if part).rstrip("_") if isinstance(column, tuple) else column
        for column in summary.columns
    ]
    summary.to_csv(OUT / "scenario_summary.csv", index=False, encoding="utf-8-sig")

    pairwise = []
    for scenario in SCENARIOS:
        for competitor in ["DIRECT", "RANDOM_MATCHED", "HARD_RDFL", "ORDINARY_SOFT"]:
            pairwise.append(bootstrap_pair(raw, scenario, competitor, "latent_effect_mse"))
            if competitor != "DIRECT":
                pairwise.append(bootstrap_pair(raw, scenario, competitor, "brier"))
    pairwise_frame = pd.DataFrame(pairwise)
    pairwise_frame["ci_low"] = pairwise_frame["ci_95"].map(lambda value: value[0])
    pairwise_frame["ci_high"] = pairwise_frame["ci_95"].map(lambda value: value[1])
    pairwise_frame.drop(columns="ci_95").to_csv(OUT / "paired_bootstrap.csv", index=False, encoding="utf-8-sig")

    configuration = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "KNOWN_TRUTH_SIMULATION",
        "seeds": SEEDS, "n_train": N_TRAIN, "n_test": N_TEST,
        "n_features": N_FEATURES, "confidence_min": CONFIDENCE_MIN,
        "scenarios": SCENARIOS,
        "versions": {
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "interpretation": {
            "net_truth": "latent net return-window effect used for primary metrics",
            "causal_warning": "in cancellation, false_causal_absence checks whether net-low labels hide strong opposing individual effects",
            "oracle_class": "classification upper-bound diagnostic; its three-class centers are not an oracle for continuous-effect MSE",
        },
    }
    (OUT / "simulation_config.json").write_text(json.dumps(configuration, indent=2), encoding="utf-8")

    mean_table = raw.groupby(["scenario", "method"])[
        ["latent_effect_mse", "brier", "class_accuracy", "training_coverage", "false_net_absence", "false_causal_absence"]
    ].mean().reset_index()
    lines = [
        "# Phase P3 Known-Truth Simulation",
        "",
        f"Replications: {len(SEEDS)} per scenario; train={N_TRAIN:,}; test={N_TEST:,}.",
        "",
        "The simulator generates latent effects independently of every labeling rule.",
        "",
        "| Scenario | Method | Effect MSE | Brier | Accuracy | Coverage | False net absence | False causal absence |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in mean_table.itertuples(index=False):
        def show(value):
            return "" if pd.isna(value) else f"{value:.4f}"
        lines.append(
            f"| {row.scenario} | {row.method} | {show(row.latent_effect_mse)} | {show(row.brier)} | "
            f"{show(row.class_accuracy)} | {show(row.training_coverage)} | "
            f"{show(row.false_net_absence)} | {show(row.false_causal_absence)} |"
        )
    lines.extend(
        [
            "",
            "A method is not considered successful merely because it beats hard labels. It must also avoid false effects in the null scenario, "
            "remain competitive with direct and ordinary-soft supervision, and expose the causal limitation under cancellation.",
            "",
        ]
    )
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"outputs: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
