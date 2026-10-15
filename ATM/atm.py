"""
ATM — Analysis of classification metrics.
Generates a synthetic binary-classification problem, trains a Logistic Regression
model, then produces a 6-panel figure covering every metric that matters:

  Panel 1 · Confusion Matrix          (TP / FP / FN / TN heat-map)
  Panel 2 · TP / FP / FN / TN counts (bar chart)
  Panel 3 · Core metrics summary      (Precision, Recall, F1, Accuracy, Specificity)
  Panel 4 · ROC curve + AUC
  Panel 5 · Precision-Recall curve + AP
  Panel 6 · F1 score vs decision threshold

Run:
    python atm.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")          # save-to-file; works with or without a display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix,
    precision_score, recall_score, f1_score, accuracy_score,
    roc_curve, auc,
    precision_recall_curve, average_precision_score,
)

# ── reproducibility ──────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)

# ── synthetic data & model ───────────────────────────────────────────────────
X, y = make_classification(
    n_samples=1_000, n_features=20, n_informative=10,
    n_redundant=5, weights=[0.6, 0.4], random_state=SEED
)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=SEED, stratify=y
)

model = LogisticRegression(max_iter=1_000, random_state=SEED)
model.fit(X_train, y_train)

y_pred  = model.predict(X_test)
y_prob  = model.predict_proba(X_test)[:, 1]   # probability of positive class

# ── core metrics ─────────────────────────────────────────────────────────────
cm = confusion_matrix(y_test, y_pred)
TN, FP, FN, TP = cm.ravel()

precision   = precision_score(y_test, y_pred)
recall      = recall_score(y_test, y_pred)          # same as TPR / sensitivity
f1          = f1_score(y_test, y_pred)
accuracy    = accuracy_score(y_test, y_pred)
specificity = TN / (TN + FP)                        # TNR

fpr_curve, tpr_curve, _       = roc_curve(y_test, y_prob)
roc_auc                        = auc(fpr_curve, tpr_curve)
prec_curve, rec_curve, thresh  = precision_recall_curve(y_test, y_prob)
avg_precision                  = average_precision_score(y_test, y_prob)

# F1 vs threshold
thresholds  = np.linspace(0.01, 0.99, 200)
f1_scores   = [
    f1_score(y_test, (y_prob >= t).astype(int), zero_division=0)
    for t in thresholds
]
best_thresh = thresholds[np.argmax(f1_scores)]
best_f1     = max(f1_scores)

# ── styling ───────────────────────────────────────────────────────────────────
PALETTE = {
    "TP": "#2ECC71",   # green
    "TN": "#3498DB",   # blue
    "FP": "#E74C3C",   # red
    "FN": "#F39C12",   # orange
    "bg": "#1A1A2E",
    "panel": "#16213E",
    "text": "#ECF0F1",
    "accent": "#E94560",
    "grid": "#2C3E50",
}

plt.rcParams.update({
    "figure.facecolor":  PALETTE["bg"],
    "axes.facecolor":    PALETTE["panel"],
    "axes.edgecolor":    PALETTE["grid"],
    "axes.labelcolor":   PALETTE["text"],
    "xtick.color":       PALETTE["text"],
    "ytick.color":       PALETTE["text"],
    "text.color":        PALETTE["text"],
    "grid.color":        PALETTE["grid"],
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "font.family":       "monospace",
})

fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle("Classification Metrics Analysis", fontsize=18, fontweight="bold",
             color=PALETTE["text"], y=1.01)

# ─── Panel 1 · Confusion Matrix ──────────────────────────────────────────────
ax = axes[0, 0]
cm_display = np.array([[TN, FP], [FN, TP]])
labels     = [["TN", "FP"], ["FN", "TP"]]
colors_map = [[PALETTE["TN"], PALETTE["FP"]], [PALETTE["FN"], PALETTE["TP"]]]

for i in range(2):
    for j in range(2):
        ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1,
                                   color=colors_map[i][j], alpha=0.85))
        ax.text(j + 0.5, 1.5 - i, f"{labels[i][j]}\n{cm_display[i][j]}",
                ha="center", va="center", fontsize=16, fontweight="bold",
                color="white")

ax.set_xlim(0, 2)
ax.set_ylim(0, 2)
ax.set_xticks([0.5, 1.5])
ax.set_xticklabels(["Predicted\nNegative", "Predicted\nPositive"], fontsize=10)
ax.set_yticks([0.5, 1.5])
ax.set_yticklabels(["Actual\nPositive", "Actual\nNegative"], fontsize=10)
ax.set_title("Confusion Matrix", fontweight="bold", pad=12)

# ─── Panel 2 · TP / FP / FN / TN bar chart ───────────────────────────────────
ax = axes[0, 1]
labels_bar = ["TP", "TN", "FP", "FN"]
values_bar = [TP, TN, FP, FN]
bar_colors = [PALETTE["TP"], PALETTE["TN"], PALETTE["FP"], PALETTE["FN"]]

bars = ax.bar(labels_bar, values_bar, color=bar_colors, width=0.55, edgecolor="white", linewidth=0.6)
for bar, val in zip(bars, values_bar):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2, str(val),
            ha="center", va="bottom", fontsize=13, fontweight="bold")

ax.set_ylim(0, max(values_bar) * 1.18)
ax.set_title("TP / TN / FP / FN Counts", fontweight="bold", pad=12)
ax.set_ylabel("Count")
ax.yaxis.grid(True)
ax.set_axisbelow(True)

# ─── Panel 3 · Metrics summary ───────────────────────────────────────────────
ax = axes[0, 2]
metric_names  = ["Precision", "Recall\n(Sensitivity)", "F1 Score",
                 "Accuracy", "Specificity\n(TNR)"]
metric_values = [precision, recall, f1, accuracy, specificity]
bar_c = ["#9B59B6", "#1ABC9C", PALETTE["accent"], "#3498DB", "#E67E22"]

bars2 = ax.barh(metric_names, metric_values, color=bar_c,
                height=0.5, edgecolor="white", linewidth=0.5)
for bar, val in zip(bars2, metric_values):
    ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", fontsize=11, fontweight="bold")

ax.set_xlim(0, 1.15)
ax.set_title("Core Metrics", fontweight="bold", pad=12)
ax.set_xlabel("Score")
ax.xaxis.grid(True)
ax.set_axisbelow(True)
# add thin formula annotations
formulas = [
    "TP / (TP+FP)",
    "TP / (TP+FN)",
    "2·P·R / (P+R)",
    "(TP+TN) / Total",
    "TN / (TN+FP)",
]
for i, (bar, fml) in enumerate(zip(bars2, formulas)):
    ax.text(0.01, bar.get_y() + bar.get_height() * 0.15,
            fml, fontsize=7, color="white", alpha=0.7)

# ─── Panel 4 · ROC curve ─────────────────────────────────────────────────────
ax = axes[1, 0]
ax.plot(fpr_curve, tpr_curve, color=PALETTE["accent"], lw=2.5,
        label=f"ROC  (AUC = {roc_auc:.3f})")
ax.fill_between(fpr_curve, tpr_curve, alpha=0.15, color=PALETTE["accent"])
ax.plot([0, 1], [0, 1], "w--", lw=1, alpha=0.5, label="Random classifier")
ax.scatter([FP / (FP + TN)], [TP / (TP + FN)],
           color="yellow", s=90, zorder=5, label="Current threshold")
ax.set_xlabel("False Positive Rate (FPR)  =  FP / (FP+TN)")
ax.set_ylabel("True Positive Rate (TPR)  =  TP / (TP+FN)")
ax.set_title("ROC Curve", fontweight="bold", pad=12)
ax.legend(fontsize=9)
ax.grid(True)

# ─── Panel 5 · Precision-Recall curve ────────────────────────────────────────
ax = axes[1, 1]
ax.plot(rec_curve, prec_curve, color="#1ABC9C", lw=2.5,
        label=f"PR  (AP = {avg_precision:.3f})")
ax.fill_between(rec_curve, prec_curve, alpha=0.15, color="#1ABC9C")
ax.axhline(y=sum(y_test) / len(y_test), color="w", lw=1,
           linestyle="--", alpha=0.5, label="Baseline (class ratio)")
ax.scatter([recall], [precision], color="yellow", s=90, zorder=5,
           label="Current threshold")
ax.set_xlabel("Recall  =  TP / (TP+FN)")
ax.set_ylabel("Precision  =  TP / (TP+FP)")
ax.set_title("Precision-Recall Curve", fontweight="bold", pad=12)
ax.legend(fontsize=9)
ax.grid(True)

# ─── Panel 6 · F1 vs threshold ───────────────────────────────────────────────
ax = axes[1, 2]
ax.plot(thresholds, f1_scores, color="#F39C12", lw=2.5, label="F1 score")
ax.axvline(x=best_thresh, color=PALETTE["accent"], lw=1.5,
           linestyle="--", label=f"Best threshold = {best_thresh:.2f}")
ax.axvline(x=0.5, color="white", lw=1, linestyle=":", alpha=0.6,
           label="Default threshold = 0.50")
ax.axhline(y=best_f1, color="#F39C12", lw=1, linestyle=":", alpha=0.6)
ax.text(best_thresh + 0.02, best_f1 - 0.04,
        f"F1 = {best_f1:.3f}", color=PALETTE["accent"], fontsize=10,
        fontweight="bold")
ax.set_xlabel("Decision Threshold")
ax.set_ylabel("F1 Score")
ax.set_title("F1 Score vs Threshold", fontweight="bold", pad=12)
ax.legend(fontsize=9)
ax.grid(True)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.05)

# ── footer with raw numbers ───────────────────────────────────────────────────
summary = (
    f"  TP={TP}  TN={TN}  FP={FP}  FN={FN}   |   "
    f"Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}  "
    f"Accuracy={accuracy:.3f}  Specificity={specificity:.3f}  "
    f"ROC-AUC={roc_auc:.3f}  AP={avg_precision:.3f}"
)
fig.text(0.5, -0.01, summary, ha="center", fontsize=9,
         color=PALETTE["text"], alpha=0.75,
         bbox=dict(boxstyle="round,pad=0.4", facecolor=PALETTE["panel"],
                   edgecolor=PALETTE["grid"], alpha=0.9))

plt.tight_layout(rect=[0, 0.03, 1, 1])

out = "ATM/metrics_analysis.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=PALETTE["bg"])
print(f"Saved → {out}")
