"""
train_model.py — E-Waste Asset Lifecycle Optimizer
===================================================
Trains and evaluates ML models for risk_label classification
(low / medium / high) using the quality-verified training dataset.

Pipeline
--------
1. Load  training_data_phase5_1235records_fixed.csv
2. Pre-process  — encode categoricals, scale numerals
3. Train/Val/Test split  (70 / 15 / 15, stratified)
4. Logistic Regression baseline
5. Gradient Boosting classifier (target AUC-ROC ≥ 0.70)
6. Evaluate  — accuracy, AUC-ROC (OvR), F1, confusion matrix,
               per-class report, 5-fold cross-validation
7. Feature importance plot
8. Save best model  →  models/risk_label_model.joblib
               meta  →  models/model_metadata.json
"""

import json
import os
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

warnings.filterwarnings("ignore")

# ─── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
DATA_PATH   = SCRIPT_DIR / "training_data_phase5_1235records_fixed.csv"
MODELS_DIR  = SCRIPT_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

MODEL_PATH  = MODELS_DIR / "risk_label_model.joblib"
META_PATH   = MODELS_DIR / "model_metadata.json"
PLOTS_DIR   = MODELS_DIR / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

TARGET      = "risk_label"
RANDOM_SEED = 42

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("E-Waste Asset Lifecycle Optimizer — Model Training")
print("=" * 70)

df = pd.read_csv(DATA_PATH, parse_dates=["purchase_date", "created_at"])
print(f"\n✓ Loaded {len(df):,} records × {len(df.columns)} columns from {DATA_PATH.name}")
print(f"  Label distribution:\n{df[TARGET].value_counts().to_string()}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. FEATURE SELECTION
# ─────────────────────────────────────────────────────────────────────────────
# Exclude:
#   - Identifiers / raw dates  (asset_id, purchase_date, created_at)
#   - risk_score               (directly encodes the target → leakage)
#   - Verification artifacts   (purchase_year, age_in_months_recalc)
#   - Target                   (risk_label)

EXCLUDE = {
    TARGET,
    "risk_score",          # derived from same raw features; leakage vs target
    "asset_id",
    "purchase_date",
    "created_at",
    "purchase_year",
    "age_in_months_recalc",
}

CATEGORICAL_FEATURES = [
    "device_type", "brand", "department", "region",
    "usage_type", "os", "overheating_issues",
]

NUMERIC_FEATURES = [
    col for col in df.columns
    if col not in EXCLUDE
    and col not in CATEGORICAL_FEATURES
]

# Validate columns exist
CATEGORICAL_FEATURES = [c for c in CATEGORICAL_FEATURES if c in df.columns]
NUMERIC_FEATURES     = [c for c in NUMERIC_FEATURES     if c in df.columns]

print(f"\n  Numeric  features ({len(NUMERIC_FEATURES)}): {NUMERIC_FEATURES}")
print(f"  Categorical features ({len(CATEGORICAL_FEATURES)}): {CATEGORICAL_FEATURES}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. PRE-PROCESS TARGET
# ─────────────────────────────────────────────────────────────────────────────
le = LabelEncoder()
y  = le.fit_transform(df[TARGET])          # low=0 / medium=1 / high=2 (sorted)
X  = df[CATEGORICAL_FEATURES + NUMERIC_FEATURES].copy()

# Ensure categoricals are strings (handle bool-like columns like overheating_issues)
for col in CATEGORICAL_FEATURES:
    X[col] = X[col].astype(str)

print(f"\n  Class encoding: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. TRAIN / VALIDATION / TEST SPLIT  (70 / 15 / 15, stratified)
# ─────────────────────────────────────────────────────────────────────────────
X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=0.15, random_state=RANDOM_SEED, stratify=y
)
X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val,
    test_size=0.15 / 0.85,      # ≈ 17.6% of train_val ≈ 15% of total
    random_state=RANDOM_SEED, stratify=y_train_val
)

print(f"\n  Split  — train: {len(X_train):,}  |  val: {len(X_val):,}  |  test: {len(X_test):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. PREPROCESSING PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         CATEGORICAL_FEATURES),
    ],
    remainder="drop",
)

# ─────────────────────────────────────────────────────────────────────────────
# 6. MODEL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
models = {
    "Logistic Regression (baseline)": LogisticRegression(
        max_iter=1000, random_state=RANDOM_SEED, class_weight="balanced", C=1.0
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.1, max_depth=4,
        subsample=0.8, min_samples_leaf=10, random_state=RANDOM_SEED
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. TRAIN, CROSS-VALIDATE AND EVALUATE
# ─────────────────────────────────────────────────────────────────────────────
cv          = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
results     = {}
best_name   = None
best_auc    = -1.0
best_pipeline = None

print("\n" + "=" * 70)
print("TRAINING & EVALUATION")
print("=" * 70)

for model_name, estimator in models.items():
    print(f"\n── {model_name} ──────────────────────────────")

    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier",   estimator),
    ])

    # ── Cross-validation (on train+val) ──────────────────────────────────────
    cv_scores = cross_validate(
        pipe, X_train_val, y_train_val,
        scoring=["accuracy", "roc_auc_ovr"],
        cv=cv, n_jobs=-1,
    )
    cv_acc = cv_scores["test_accuracy"].mean()
    cv_auc = cv_scores["test_roc_auc_ovr"].mean()
    print(f"  5-Fold CV  accuracy : {cv_acc:.4f} ± {cv_scores['test_accuracy'].std():.4f}")
    print(f"  5-Fold CV  AUC-ROC  : {cv_auc:.4f} ± {cv_scores['test_roc_auc_ovr'].std():.4f}")

    # ── Fit on full train split, evaluate on val ──────────────────────────────
    pipe.fit(X_train, y_train)

    y_val_pred  = pipe.predict(X_val)
    y_val_proba = pipe.predict_proba(X_val)
    val_acc     = accuracy_score(y_val, y_val_pred)
    val_auc     = roc_auc_score(y_val, y_val_proba, multi_class="ovr", average="macro")

    print(f"\n  Validation accuracy : {val_acc:.4f}")
    print(f"  Validation AUC-ROC  : {val_auc:.4f}  {'✓ target met' if val_auc >= 0.70 else '✗ below 0.70 target'}")
    print(f"\n  Classification report (validation):")
    print(classification_report(y_val, y_val_pred, target_names=le.classes_))

    results[model_name] = {
        "cv_accuracy": float(cv_acc),
        "cv_auc_roc":  float(cv_auc),
        "val_accuracy": float(val_acc),
        "val_auc_roc":  float(val_auc),
        "pipeline":     pipe,
    }

    if val_auc > best_auc:
        best_auc    = val_auc
        best_name   = model_name
        best_pipeline = pipe

# ─────────────────────────────────────────────────────────────────────────────
# 8. FINAL TEST EVALUATION (best model only)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"BEST MODEL: {best_name}  (val AUC-ROC = {best_auc:.4f})")
print("=" * 70)

# Refit on train+val before final test
best_pipeline.fit(X_train_val, y_train_val)

y_test_pred  = best_pipeline.predict(X_test)
y_test_proba = best_pipeline.predict_proba(X_test)
test_acc     = accuracy_score(y_test, y_test_pred)
test_auc     = roc_auc_score(y_test, y_test_proba, multi_class="ovr", average="macro")

print(f"\n  Test accuracy : {test_acc:.4f}")
print(f"  Test AUC-ROC  : {test_auc:.4f}  {'✓ target met' if test_auc >= 0.70 else '✗ below 0.70 target'}")
print(f"\n  Classification report (test set):")
report_dict = classification_report(
    y_test, y_test_pred, target_names=le.classes_, output_dict=True
)
print(classification_report(y_test, y_test_pred, target_names=le.classes_))

# ─────────────────────────────────────────────────────────────────────────────
# 9. PLOTS
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(19, 5))
fig.suptitle(f"Model Evaluation — {best_name}", fontsize=13, fontweight="bold")

# ── Confusion matrix ──────────────────────────────────────────────────────────
ConfusionMatrixDisplay.from_predictions(
    y_test, y_test_pred,
    display_labels=le.classes_,
    cmap="Blues",
    ax=axes[0],
)
axes[0].set_title("Confusion Matrix (Test Set)")

# ── Per-class F1 bar chart ────────────────────────────────────────────────────
class_names = le.classes_
f1_scores   = [report_dict[c]["f1-score"] for c in class_names]
colors_f1   = ["#e74c3c", "#f39c12", "#2ecc71"]
bars = axes[1].bar(class_names, f1_scores, color=colors_f1, edgecolor="white")
axes[1].set_ylim(0, 1.05)
axes[1].set_title("Per-Class F1-Score (Test Set)")
axes[1].set_ylabel("F1-Score")
axes[1].axhline(0.70, color="grey", linestyle="--", linewidth=1, label="0.70 target")
axes[1].legend(fontsize=9)
for bar, val in zip(bars, f1_scores):
    axes[1].text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.01,
        f"{val:.2f}", ha="center", fontsize=10,
    )

# ── Feature importance (GB) or Coefficients (LR) ────────────────────────────
clf = best_pipeline.named_steps["classifier"]
pre = best_pipeline.named_steps["preprocessor"]

num_feat_names = NUMERIC_FEATURES
cat_feat_names = list(
    pre.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
)
all_feat_names = num_feat_names + cat_feat_names

if hasattr(clf, "feature_importances_"):
    importances = clf.feature_importances_
    title_imp   = "Feature Importances (Gradient Boosting)"
else:
    # Multiclass LR: mean absolute coefficient across classes
    importances = np.abs(clf.coef_).mean(axis=0)
    title_imp   = "Mean |Coefficient| (Logistic Regression)"

# Top-20 features
top_n   = min(20, len(importances))
idx_top = np.argsort(importances)[-top_n:][::-1]
top_names = [all_feat_names[i] if i < len(all_feat_names) else f"feat_{i}" for i in idx_top]
top_vals  = importances[idx_top]

axes[2].barh(range(top_n), top_vals[::-1], color="steelblue", edgecolor="white")
axes[2].set_yticks(range(top_n))
axes[2].set_yticklabels(top_names[::-1], fontsize=8)
axes[2].set_title(title_imp)
axes[2].set_xlabel("Importance")

plt.tight_layout()
plot_path = PLOTS_DIR / "evaluation.png"
plt.savefig(plot_path, dpi=120, bbox_inches="tight")
plt.show()
print(f"\n✓ Evaluation plots saved → {plot_path}")

# ── Model comparison bar chart ────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(9, 4))
model_names_short = [n.replace(" (baseline)", "\n(baseline)") for n in results]
val_aucs  = [results[n]["val_auc_roc"]  for n in results]
cv_aucs   = [results[n]["cv_auc_roc"]   for n in results]
x_pos     = np.arange(len(results))
width     = 0.35
ax2.bar(x_pos - width / 2, cv_aucs,  width, label="5-Fold CV AUC-ROC",  color="#3498db", edgecolor="white")
ax2.bar(x_pos + width / 2, val_aucs, width, label="Validation AUC-ROC", color="#2ecc71", edgecolor="white")
ax2.axhline(0.70, color="red", linestyle="--", linewidth=1.5, label="Target ≥ 0.70")
ax2.set_xticks(x_pos)
ax2.set_xticklabels(model_names_short, fontsize=10)
ax2.set_ylabel("AUC-ROC (macro OvR)")
ax2.set_title("Model Comparison — AUC-ROC")
ax2.set_ylim(0, 1.05)
ax2.legend(fontsize=9)
for i, (cv_v, val_v) in enumerate(zip(cv_aucs, val_aucs)):
    ax2.text(i - width / 2, cv_v  + 0.01, f"{cv_v:.3f}",  ha="center", fontsize=9)
    ax2.text(i + width / 2, val_v + 0.01, f"{val_v:.3f}", ha="center", fontsize=9)
plt.tight_layout()
fig2.savefig(PLOTS_DIR / "model_comparison.png", dpi=120, bbox_inches="tight")
plt.show()
print(f"✓ Comparison plot saved → {PLOTS_DIR / 'model_comparison.png'}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. SAVE MODEL + METADATA
# ─────────────────────────────────────────────────────────────────────────────
joblib.dump({"pipeline": best_pipeline, "label_encoder": le}, MODEL_PATH)
print(f"\n✓ Model saved → {MODEL_PATH}")

metadata = {
    "trained_at":       datetime.now().isoformat(),
    "data_source":      DATA_PATH.name,
    "n_train":          int(len(X_train_val)),
    "n_test":           int(len(X_test)),
    "best_model":       best_name,
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "label_classes":    list(le.classes_),
    "label_encoding":   {cls: int(le.transform([cls])[0]) for cls in le.classes_},
    "thresholds": {
        "high":   "risk_score >= 0.55",
        "medium": "risk_score in [0.35, 0.55)",
        "low":    "risk_score < 0.35",
    },
    "metrics": {
        "test": {
            "accuracy": round(test_acc, 4),
            "auc_roc_macro_ovr": round(test_auc, 4),
            "per_class": {
                cls: {
                    "precision": round(report_dict[cls]["precision"], 4),
                    "recall":    round(report_dict[cls]["recall"],    4),
                    "f1_score":  round(report_dict[cls]["f1-score"],  4),
                    "support":   int(report_dict[cls]["support"]),
                }
                for cls in le.classes_
            },
        },
        "validation": {
            "accuracy": round(results[best_name]["val_accuracy"], 4),
            "auc_roc_macro_ovr": round(results[best_name]["val_auc_roc"], 4),
        },
        "cross_validation_5fold": {
            "mean_accuracy": round(results[best_name]["cv_accuracy"], 4),
            "mean_auc_roc":  round(results[best_name]["cv_auc_roc"],  4),
        },
    },
    "target_met": test_auc >= 0.70,
}

with open(META_PATH, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"✓ Metadata saved → {META_PATH}")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("TRAINING COMPLETE — SUMMARY")
print("=" * 70)
print(f"  Best model         : {best_name}")
print(f"  Test accuracy      : {test_acc:.4f}")
print(f"  Test AUC-ROC       : {test_auc:.4f}  {'✓' if test_auc >= 0.70 else '✗'}")
print(f"  AUC-ROC target met : {'YES ✓' if test_auc >= 0.70 else 'NO ✗  — review hyperparameters'}")
print(f"  Artifacts:")
print(f"    Model    → {MODEL_PATH}")
print(f"    Metadata → {META_PATH}")
print(f"    Plots    → {PLOTS_DIR}")
