"""Phase P1 pilot: point-in-time bags and fuzzy outcome-derived weak labels.

This is deliberately marked PILOT because Phase P0 found unresolved timezone,
trading-calendar, and price-adjustment gates. The conservative news mapping uses
the first observed stock trading date strictly after the article's calendar date.
It must not be presented as the confirmatory result.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "fpa_phafin" / "p1_pilot_labels"
NEWS_PATH = RAW / "All_news_sentiment.csv"
FIN_DIR = RAW / "financial"
SYMBOLS = ["BBL", "KBANK", "KTB", "SCB", "BAY", "TTB", "KKP", "TISCO"]

FEATURES = [
    "log_ret", "vol_5d", "vol_22d", "mom_5d", "mom_22d",
    "hl_range", "turnover_rel", "beta_60d", "set_ret", "set_vol_22d",
]
ALPHAS = [0.1, 1.0, 10.0]
MIN_TRAIN = 60
VALIDATION_SIZE = 20
REFIT_EVERY = 20
SCALE_HISTORY = 60
THRESHOLD_HISTORY = 60
CONFIDENCE_MIN = 0.70
EPSILON = 1e-8


def stable_article_id(row: pd.Series) -> str:
    payload = "\x1f".join(
        str(row.get(column, "")) if pd.notna(row.get(column)) else ""
        for column in ["Date", "Symbol", "Headline", "URL"]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def load_financial() -> pd.DataFrame:
    frames = []
    for symbol in SYMBOLS:
        path = FIN_DIR / f"panel_{symbol}.csv"
        frame = pd.read_csv(path, low_memory=False)
        frame["Date"] = pd.to_datetime(frame["Date"], errors="raise").dt.normalize()
        frame = frame.sort_values("Date").drop_duplicates("Date", keep="first").copy()
        frame["Symbol"] = symbol
        open_price = pd.to_numeric(frame["Open"], errors="coerce")
        high_price = pd.to_numeric(frame["High"], errors="coerce")
        low_price = pd.to_numeric(frame["Low"], errors="coerce")
        close_price = pd.to_numeric(frame["Close"], errors="coerce")
        volume = pd.to_numeric(frame["Volume"], errors="coerce")
        positive_ohlc = (pd.concat([open_price, high_price, low_price, close_price], axis=1) > 0).all(axis=1)
        coherent_ohlc = (
            high_price >= pd.concat([open_price, close_price, low_price], axis=1).max(axis=1)
        ) & (
            low_price <= pd.concat([open_price, close_price, high_price], axis=1).min(axis=1)
        )
        frame["target_open_close"] = np.where(
            (open_price > 0) & (close_price > 0), np.log(close_price / open_price), np.nan
        )
        frame["outcome_data_valid"] = positive_ohlc & coherent_ohlc & (volume > 0)
        for feature in FEATURES:
            frame[f"x_{feature}"] = pd.to_numeric(frame[feature], errors="coerce").shift(1)
        frame["outcome_volume"] = volume
        frames.append(frame)
    return pd.concat(frames, ignore_index=True).sort_values(["Symbol", "Date"]).reset_index(drop=True)


def build_article_map(financial: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    news = pd.read_csv(NEWS_PATH, low_memory=False)
    news.insert(0, "source_row", np.arange(2, len(news) + 2))
    key = ["Date", "Symbol", "Headline", "URL"]
    original_rows = len(news)
    news = news.drop_duplicates(key, keep="first").copy()
    news["published_raw"] = news["Date"].astype(str)
    news["published_date"] = pd.to_datetime(news["Date"], errors="coerce").dt.normalize()
    news["article_id"] = news.apply(stable_article_id, axis=1)
    description = news["Description"].fillna("").astype(str).replace({"nan": ""})
    news["model_text"] = (
        news["Headline"].fillna("").astype(str).str.strip()
        + " "
        + description.str.strip()
    ).str.strip()
    news["decision_date"] = pd.NaT

    for symbol in SYMBOLS:
        calendar = np.array(
            sorted(financial.loc[financial["Symbol"] == symbol, "Date"].dropna().unique()),
            dtype="datetime64[ns]",
        )
        mask = (news["Symbol"].astype(str) == symbol) & news["published_date"].notna()
        dates = news.loc[mask, "published_date"].to_numpy(dtype="datetime64[ns]")
        positions = np.searchsorted(calendar, dates, side="right")
        mapped = np.full(len(positions), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
        valid = positions < len(calendar)
        mapped[valid] = calendar[positions[valid]]
        news.loc[mask, "decision_date"] = pd.to_datetime(mapped)

    news["timing_rule"] = "PROVISIONAL_DATE_END_TO_NEXT_OBSERVED_TRADING_DATE"
    news["timestamp_verified"] = False
    keep = [
        "article_id", "source_row", "published_raw", "published_date", "decision_date",
        "Symbol", "Source", "Language", "Headline", "Description", "model_text", "URL",
        "timing_rule", "timestamp_verified",
    ]
    mapped = news[keep].sort_values(["decision_date", "Symbol", "source_row"], na_position="last")
    stats = {
        "input_rows": original_rows,
        "deduplicated_rows": len(mapped),
        "duplicates_removed": original_rows - len(mapped),
        "mapped_rows": int(mapped["decision_date"].notna().sum()),
        "unmapped_rows": int(mapped["decision_date"].isna().sum()),
    }
    return mapped, stats


def add_bag_metadata(financial: pd.DataFrame, article_map: pd.DataFrame) -> pd.DataFrame:
    assigned = article_map.dropna(subset=["decision_date"]).copy()
    bag = (
        assigned.groupby(["Symbol", "decision_date"], as_index=False)
        .agg(
            news_count=("article_id", "size"),
            unique_articles=("article_id", "nunique"),
            source_count=("Source", "nunique"),
            article_ids=("article_id", lambda values: "|".join(values.astype(str))),
        )
        .rename(columns={"decision_date": "Date"})
    )
    panel = financial.merge(bag, how="left", on=["Symbol", "Date"], validate="one_to_one")
    for column in ["news_count", "unique_articles", "source_count"]:
        panel[column] = panel[column].fillna(0).astype(int)
    panel["article_ids"] = panel["article_ids"].fillna("")
    panel["has_news"] = panel["news_count"] > 0
    panel["decision_time"] = panel["Date"].dt.strftime("%Y-%m-%dT09:00:00+07:00")
    return panel


def fit_forward_ridge(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("Date").copy()
    x_columns = [f"x_{feature}" for feature in FEATURES]
    x = group[x_columns].to_numpy(dtype=float)
    y = group["target_open_close"].to_numpy(dtype=float)
    complete = np.isfinite(x).all(axis=1) & np.isfinite(y)
    predictions = np.full(len(group), np.nan)
    selected_alpha = np.full(len(group), np.nan)
    model = None
    current_alpha = np.nan
    since_refit = REFIT_EVERY

    for i in range(len(group)):
        if not complete[i]:
            continue
        history = np.flatnonzero(complete[:i])
        if len(history) < MIN_TRAIN:
            continue
        if model is None or since_refit >= REFIT_EVERY:
            if len(history) >= MIN_TRAIN + VALIDATION_SIZE:
                fit_idx = history[:-VALIDATION_SIZE]
                val_idx = history[-VALIDATION_SIZE:]
                losses = []
                for alpha in ALPHAS:
                    candidate = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
                    candidate.fit(x[fit_idx], y[fit_idx])
                    losses.append(mean_squared_error(y[val_idx], candidate.predict(x[val_idx])))
                current_alpha = ALPHAS[int(np.argmin(losses))]
            else:
                current_alpha = 1.0
            model = make_pipeline(StandardScaler(), Ridge(alpha=current_alpha))
            model.fit(x[history], y[history])
            since_refit = 0
        predictions[i] = float(model.predict(x[i : i + 1])[0])
        selected_alpha[i] = current_alpha
        since_refit += 1

    group["price_only_prediction"] = predictions
    group["ridge_alpha"] = selected_alpha
    group["residual"] = group["target_open_close"] - group["price_only_prediction"]
    return group


def past_robust_standardized(values: pd.Series, history: int) -> tuple[np.ndarray, np.ndarray]:
    array = values.to_numpy(dtype=float)
    standardized = np.full(len(array), np.nan)
    scale_used = np.full(len(array), np.nan)
    for i, value in enumerate(array):
        if not np.isfinite(value):
            continue
        past = array[:i]
        past = past[np.isfinite(past)]
        if len(past) < history:
            continue
        past = past[-history:]
        center = np.median(past)
        scale = 1.4826 * np.median(np.abs(past - center))
        if not np.isfinite(scale) or scale <= EPSILON:
            continue
        standardized[i] = (value - center) / scale
        scale_used[i] = scale
    return standardized, scale_used


def add_fuzzy_labels(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("Date").copy()
    z, residual_scale = past_robust_standardized(group["residual"], SCALE_HISTORY)
    log_volume = np.where(group["outcome_volume"].to_numpy(dtype=float) > 0,
                          np.log1p(group["outcome_volume"].to_numpy(dtype=float)), np.nan)
    volume_z, volume_scale = past_robust_standardized(pd.Series(log_volume), SCALE_HISTORY)
    volume_deviation = np.abs(volume_z)

    n = len(group)
    q_low = np.full(n, np.nan)
    q_high = np.full(n, np.nan)
    v_low = np.full(n, np.nan)
    v_high = np.full(n, np.nan)
    p_neg = np.full(n, np.nan)
    p_zero = np.full(n, np.nan)
    p_pos = np.full(n, np.nan)
    confidence = np.full(n, np.nan)
    label = np.full(n, "ABSTAIN", dtype=object)

    for i in range(n):
        if not (np.isfinite(z[i]) and np.isfinite(volume_deviation[i])):
            continue
        past_abs_z = np.abs(z[:i])
        past_abs_z = past_abs_z[np.isfinite(past_abs_z)]
        past_v = volume_deviation[:i]
        past_v = past_v[np.isfinite(past_v)]
        if len(past_abs_z) < THRESHOLD_HISTORY or len(past_v) < THRESHOLD_HISTORY:
            continue
        ql, qh = np.quantile(past_abs_z, [0.30, 0.70])
        vl, vh = np.quantile(past_v, [0.50, 0.90])
        if qh - ql <= EPSILON or vh - vl <= EPSILON:
            continue
        q_low[i], q_high[i], v_low[i], v_high[i] = ql, qh, vl, vh
        magnitude = abs(z[i])
        low_response = float(np.clip((qh - magnitude) / (qh - ql), 0.0, 1.0))
        high_response = 1.0 - low_response
        normal_volume = float(np.clip((vh - volume_deviation[i]) / (vh - vl), 0.0, 1.0))
        memberships = np.array(
            [high_response if z[i] < 0 else 0.0,
             min(low_response, normal_volume),
             high_response if z[i] > 0 else 0.0],
            dtype=float,
        )
        total = memberships.sum()
        if total <= EPSILON:
            continue
        probabilities = memberships / total
        p_neg[i], p_zero[i], p_pos[i] = probabilities
        confidence[i] = float(memberships.max())
        if (
            confidence[i] >= CONFIDENCE_MIN
            and bool(group.iloc[i]["has_news"])
            and bool(group.iloc[i]["outcome_data_valid"])
        ):
            label[i] = ["NEGATIVE", "LOW_RESPONSE", "POSITIVE"][int(np.argmax(probabilities))]

    group["residual_scale"] = residual_scale
    group["residual_z"] = z
    group["volume_log_scale"] = volume_scale
    group["volume_deviation"] = volume_deviation
    group["q_low"] = q_low
    group["q_high"] = q_high
    group["v_low"] = v_low
    group["v_high"] = v_high
    group["p_negative"] = p_neg
    group["p_low_response"] = p_zero
    group["p_positive"] = p_pos
    group["label_confidence"] = confidence
    group["weak_label"] = label
    group["retain_for_text_training"] = label != "ABSTAIN"
    group["label_status"] = "PILOT_UNCONFIRMED_TIMING_AND_PRICE_ADJUSTMENT"
    return group


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    financial = load_financial()
    article_map, mapping_stats = build_article_map(financial)
    panel = add_bag_metadata(financial, article_map)
    ridge_parts = []
    for symbol, group in panel.groupby("Symbol", sort=False):
        part = fit_forward_ridge(group)
        part["Symbol"] = symbol
        ridge_parts.append(part)
    panel = pd.concat(ridge_parts, ignore_index=True)
    label_parts = []
    for symbol, group in panel.groupby("Symbol", sort=False):
        part = add_fuzzy_labels(group)
        part["Symbol"] = symbol
        label_parts.append(part)
    panel = pd.concat(label_parts, ignore_index=True)

    article_map.to_csv(OUT / "article_to_stock_day_pilot.csv", index=False, encoding="utf-8-sig")
    output_columns = [
        "Date", "decision_time", "Symbol", "target_open_close", "outcome_volume", "outcome_data_valid",
        *[f"x_{feature}" for feature in FEATURES],
        "news_count", "unique_articles", "source_count", "article_ids", "has_news",
        "price_only_prediction", "ridge_alpha", "residual", "residual_scale", "residual_z",
        "volume_deviation", "q_low", "q_high", "v_low", "v_high",
        "p_negative", "p_low_response", "p_positive", "label_confidence",
        "weak_label", "retain_for_text_training", "label_status",
    ]
    panel[output_columns].to_csv(OUT / "stock_day_labels_pilot.csv", index=False, encoding="utf-8-sig")
    retained = panel.loc[panel["retain_for_text_training"], output_columns]
    retained.to_csv(OUT / "retained_weak_labels_pilot.csv", index=False, encoding="utf-8-sig")

    class_counts = retained["weak_label"].value_counts().sort_index().to_dict()
    summary = {
        "schema_version": "1.0-pilot",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PILOT_ONLY_NOT_CONFIRMATORY",
        "mapping_rule": "first observed stock trading date strictly after article calendar date",
        "known_blockers": [
            "publication timezone and ingestion availability are unverified",
            "official exchange trading calendar is absent",
            "price adjustment and corporate actions are unverified",
            "zero-volume semantics are unresolved",
        ],
        "parameters": {
            "features": FEATURES,
            "alphas": ALPHAS,
            "min_train": MIN_TRAIN,
            "validation_size": VALIDATION_SIZE,
            "refit_every": REFIT_EVERY,
            "scale_history": SCALE_HISTORY,
            "threshold_history": THRESHOLD_HISTORY,
            "confidence_min": CONFIDENCE_MIN,
        },
        "article_mapping": mapping_stats,
        "stock_days": len(panel),
        "stock_days_with_news": int(panel["has_news"].sum()),
        "stock_days_with_forward_price_prediction": int(panel["price_only_prediction"].notna().sum()),
        "retained_weak_labels": len(retained),
        "retained_fraction_of_news_days": float(len(retained) / max(1, panel["has_news"].sum())),
        "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "retained_date_min": retained["Date"].min().isoformat() if len(retained) else None,
        "retained_date_max": retained["Date"].max().isoformat() if len(retained) else None,
    }
    (OUT / "pilot_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = [
        "# FPA-PhaFin Phase P1 Pilot Labels",
        "",
        "Status: **PILOT ONLY — NOT CONFIRMATORY**",
        "",
        f"- Deduplicated articles: {mapping_stats['deduplicated_rows']:,}",
        f"- Articles mapped conservatively: {mapping_stats['mapped_rows']:,}",
        f"- Stock-days: {len(panel):,}",
        f"- Stock-days with news: {int(panel['has_news'].sum()):,}",
        f"- Retained weak labels: {len(retained):,}",
        f"- Retained/news-day ratio: {summary['retained_fraction_of_news_days']:.3f}",
        f"- Class counts: {summary['class_counts']}",
        "",
        "The mapping intentionally delays every article until the next observed trading date. "
        "This is conservative for a pilot, but it does not replace source-level timezone and availability verification.",
        "",
    ]
    (OUT / "PILOT_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
