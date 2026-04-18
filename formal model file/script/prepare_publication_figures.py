from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/Users/hlbao/Projects/dissertation/formal model file")
NOTEBOOK = ROOT / "script" / "03_surrogate_v7.ipynb"


CELL0 = """# ── Cell 0: Imports & Load Results ───────────────────────────────────────────
import warnings, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.titlesize': 12,
})

# ══════════════════════════════════════════════════════════════════════════════
# HOUSE TYPE — change this one variable to switch between detached and semi
# ══════════════════════════════════════════════════════════════════════════════
import os

HOUSE_TYPE = os.environ.get("HOUSE_TYPE", "detached")   # "detached" or "semi"
ARCHETYPE_LABEL = 'Semi-detached' if HOUSE_TYPE == 'semi' else 'Detached'

_here = Path.cwd().resolve()
_root = _here if (_here / "formal model file" / "output").exists() else _here.parents[2]
OUT_BASE = _root / "formal model file" / "output"
FIG_BASE = OUT_BASE / "figures"
FIG_IN_TEXT_DIR = FIG_BASE / "in_text"
FIG_APPENDIX_DIR = FIG_BASE / "appendix"

if HOUSE_TYPE == "semi":
    RESULTS_CSV = OUT_BASE / "results" / "results_v7_semi.csv"
    MODEL_DIR   = OUT_BASE / "models" / "semi"
    PERF_CSV    = OUT_BASE / "results" / "model_performance_semi.csv"
else:
    RESULTS_CSV = OUT_BASE / "results" / "results_v7.csv"
    MODEL_DIR   = OUT_BASE / "models" / "detached"
    PERF_CSV    = OUT_BASE / "results" / "model_performance.csv"

for d in [FIG_IN_TEXT_DIR, FIG_APPENDIX_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

FIG_PARITY_DIR = FIG_IN_TEXT_DIR if HOUSE_TYPE == 'detached' else FIG_APPENDIX_DIR
FIG_SHAP_HE_DIR = FIG_IN_TEXT_DIR if HOUSE_TYPE == 'detached' else FIG_APPENDIX_DIR
TEST_PREDICTIONS_CSV = OUT_BASE / "results" / f"test_predictions_{HOUSE_TYPE}.csv"
SHAP_IMPORTANCE_CSV = OUT_BASE / "results" / f"shap_importance_{HOUSE_TYPE}.csv"
SHAP_BEESWARM_HE_CSV = OUT_BASE / "results" / f"shap_beeswarm_he_{HOUSE_TYPE}.csv"
RF_IMPORTANCE_CSV = OUT_BASE / "results" / f"rf_importance_{HOUSE_TYPE}.csv"

MODEL_COLORS = {
    'RF': '#4C6A92',
    'XGBoost': '#C76D3A',
    'MLP': '#2F8F6B',
}

TARGET_META = {
    'He_worst': {
        'short': 'He_worst',
        'label': 'He_worst (% summer hours)',
        'color': '#D95F02',
        'threshold': 3.0,
        'threshold_label': 'TM52 C1 = 3%',
    },
    'We_max_worst': {
        'short': 'We_max_worst',
        'label': 'We_max_worst (daily weighted exceedance)',
        'color': '#E6AB02',
        'threshold': 6.0,
        'threshold_label': 'TM52 C2 = 6',
    },
    'T_op_peak': {
        'short': 'T_op_peak',
        'label': 'T_op_peak (°C)',
        'color': '#7570B3',
        'threshold': None,
        'threshold_label': None,
    },
    'hours_gt26_night': {
        'short': 'hours_gt26_night',
        'label': 'Bedroom night hours > 26°C',
        'color': '#1F78B4',
        'threshold': 32.0,
        'threshold_label': 'TM59 = 32 h',
    },
    'heat_kWh_m2': {
        'short': 'heat_kWh_m2',
        'label': 'Heating (kWh/m²·yr)',
        'color': '#1B9E77',
        'threshold': None,
        'threshold_label': None,
    },
}

def savefig(fig, path):
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)

print(f"House type   : {HOUSE_TYPE}")
print(f"Results CSV  : {RESULTS_CSV.name}")
print(f"Models dir   : {MODEL_DIR}")
print(f"In-text figs : {FIG_IN_TEXT_DIR}")
print(f"Appendix figs: {FIG_APPENDIX_DIR}")

PARAM_COLS = [
    'width', 'length', 'height', 'orientation', 'wwr',
    'wallInsulationThickness', 'roofInsulationThickness', 'slabInsulationThickness',
    'u_windows', 'g_value', 'roofAbsorptance', 'flowCoefficient', 'wof', 'fixedShadingDepth',
]
SURROGATE_TARGETS = [
    'He_worst',
    'We_max_worst',
    'T_op_peak',
    'hours_gt26_night',
    'heat_kWh_m2',
]
DIAGNOSTIC_COLS = ['hours_C3_worst']
TARGET_COLS = SURROGATE_TARGETS

df_all = pd.read_csv(RESULTS_CSV)
df = df_all[df_all['status'] == 'ok'].copy().reset_index(drop=True)

print(f"\\nTotal runs   : {len(df_all)}")
print(f"Successful   : {len(df)}  ({100*len(df)/len(df_all):.1f}%)")
print(f"Failed/NaN   : {len(df_all) - len(df)}")
print(f"\\nTarget distributions:")
print(df[TARGET_COLS].describe().round(3).to_string())
if 'hours_C3_worst' in df.columns:
    c3_active = int((df['hours_C3_worst'] > 0).sum())
    print(f"\\nTM52 Criterion 3 diagnostic:")
    print(f"  Active cases (>0 h) : {c3_active}/{len(df)}")
    print(f"  Maximum hours       : {int(df['hours_C3_worst'].max())}")
"""


CELL1 = """# ── Cell 1: EDA — Target Distributions ───────────────────────────────────────
from IPython.display import Image, display

fig, axes = plt.subplots(2, 3, figsize=(14, 8))
axes = axes.flatten()

for i, col in enumerate(TARGET_COLS):
    meta = TARGET_META[col]
    vals = df[col].dropna()
    ax = axes[i]
    ax.hist(vals, bins=40, color=meta['color'], alpha=0.88, edgecolor='white', lw=0.4)
    ax.axvline(vals.median(), color='0.2', ls='--', lw=1.2)

    stats_lines = [f"Median = {vals.median():.2f}"]
    if meta['threshold'] is not None:
        ax.axvline(meta['threshold'], color='#B22222', ls=':', lw=1.4)
        fail_rate = 100 * (vals >= meta['threshold']).mean()
        stats_lines.append(f"Fail proxy = {fail_rate:.1f}%")

    ax.text(0.98, 0.96, '\\n'.join(stats_lines), transform=ax.transAxes,
            ha='right', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.85, edgecolor='0.8'))
    ax.set_title(meta['short'])
    ax.set_xlabel(meta['label'])
    ax.set_ylabel('Count')
    ax.grid(alpha=0.25)

p = FIG_IN_TEXT_DIR / f'{HOUSE_TYPE}_target_distributions.png'
savefig(fig, p)
display(Image(str(p)))

print("\\nTarget correlation matrix:")
print(df[TARGET_COLS].corr().round(3).to_string())
"""


CELL4 = """# ── Cell 4: Test Set Comparison — XGBoost vs MLP vs RF ───────────────────────
from IPython.display import Image, display

def predict_nn(model, X_scaled):
    model.eval()
    with torch.no_grad():
        y_s = model(to_tensor(X_scaled)).cpu().numpy()
    return scaler_y.inverse_transform(y_s)

def predict_xgb(models, X):
    return np.column_stack([m.predict(X) for m in models])

def predict_rf(models, X):
    return np.column_stack([m.predict(X) for m in models])

y_pred_xgb = predict_xgb(xgb_models, X_test) if HAS_XGB else None
y_pred_nn  = predict_nn(mlp, X_te_s)
y_pred_rf  = predict_rf(rf_models, X_test)

rows = []
for i, target in enumerate(TARGET_COLS):
    y_true = y_test[:, i]
    for label, y_pred in [('XGBoost', y_pred_xgb), ('MLP', y_pred_nn), ('RF', y_pred_rf)]:
        if y_pred is None:
            continue
        r2   = r2_score(y_true, y_pred[:, i])
        mae  = mean_absolute_error(y_true, y_pred[:, i])
        rmse = mean_squared_error(y_true, y_pred[:, i]) ** 0.5
        rows.append(dict(target=target, model=label, R2=r2, MAE=mae, RMSE=rmse))

test_df = pd.DataFrame(rows)
print("── Test Set R² (higher is better) ──────────────────────────────────────")
print(test_df.pivot(index='target', columns='model', values='R2').round(4).to_string())
print("\\n── Test Set MAE (lower is better) ──────────────────────────────────────")
print(test_df.pivot(index='target', columns='model', values='MAE').round(4).to_string())

# Parity plots
fig, axes = plt.subplots(2, len(TARGET_COLS), figsize=(3.2*len(TARGET_COLS), 7))
for i, target in enumerate(TARGET_COLS):
    y_true = y_test[:, i]
    for row_idx, (label, y_pred) in enumerate([
        ('XGBoost', y_pred_xgb),
        ('MLP',     y_pred_nn),
    ]):
        if y_pred is None:
            continue
        r2  = r2_score(y_true, y_pred[:, i])
        mae = mean_absolute_error(y_true, y_pred[:, i])
        ax  = axes[row_idx, i]
        ax.scatter(y_true, y_pred[:, i], alpha=0.35, s=8, color=MODEL_COLORS[label])
        lims = [min(y_true.min(), y_pred[:, i].min()), max(y_true.max(), y_pred[:, i].max())]
        ax.plot(lims, lims, 'k--', lw=1)
        ax.set_title(f"{TARGET_META[target]['short']} | {label}")
        ax.set_xlabel('EnergyPlus')
        ax.set_ylabel('Surrogate')
        ax.tick_params(labelsize=9)
        ax.grid(alpha=0.25)
        ax.text(0.05, 0.95, f"R²={r2:.3f}\\nMAE={mae:.3f}", transform=ax.transAxes,
                ha='left', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.85, edgecolor='0.8'))
p = FIG_PARITY_DIR / f'{HOUSE_TYPE}_parity_xgb_vs_mlp.png'
savefig(fig, p)
display(Image(str(p)))

# R² bar chart
fig2, ax2 = plt.subplots(figsize=(11, 5.5))
r2_pivot = test_df.pivot(index='target', columns='model', values='R2')
r2_pivot = r2_pivot[['RF', 'XGBoost', 'MLP']]
r2_pivot.plot(kind='bar', ax=ax2, width=0.68,
              color=[MODEL_COLORS['RF'], MODEL_COLORS['XGBoost'], MODEL_COLORS['MLP']],
              alpha=0.9, edgecolor='white')
ax2.axhline(0.9, color='black', ls='--', lw=1, alpha=0.5)
ax2.set_xlabel('')
ax2.set_ylabel('R² (test set)')
ax2.set_xticklabels([TARGET_META[t]['short'] for t in r2_pivot.index], rotation=15, ha='right')
ax2.legend(loc='lower right', frameon=True)
ax2.grid(alpha=0.3, axis='y')
ax2.set_ylim(0, 1.05)
p2 = FIG_IN_TEXT_DIR / f'{HOUSE_TYPE}_model_comparison_r2.png'
savefig(fig2, p2)
display(Image(str(p2)))

# Export canonical test-prediction table for publication figures
pred_rows = []
for i, target in enumerate(TARGET_COLS):
    y_true = y_test[:, i]
    for label, y_pred in [('XGBoost', y_pred_xgb), ('MLP', y_pred_nn), ('RF', y_pred_rf)]:
        if y_pred is None:
            continue
        pred_rows.append(pd.DataFrame({
            'archetype': HOUSE_TYPE,
            'target': target,
            'model': label,
            'y_true': y_true,
            'y_pred': y_pred[:, i],
        }))
pd.concat(pred_rows, ignore_index=True).to_csv(TEST_PREDICTIONS_CSV, index=False)
print(f"Saved → {TEST_PREDICTIONS_CSV}")
"""


CELL5 = """# ── Cell 5: Feature Importance (RF built-in + SHAP) ──────────────────────────
from IPython.display import Image, display

# ── 5a: Random Forest built-in importance (MDI) ──────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
axes = axes.flatten()

for i, (target, rf_m) in enumerate(zip(TARGET_COLS, rf_models)):
    imp   = rf_m.feature_importances_
    order = np.argsort(imp)[::-1]
    ax = axes[i]
    ax.barh([PARAM_COLS[j] for j in order[::-1]], imp[order[::-1]],
            color=TARGET_META[target]['color'], alpha=0.85)
    ax.set_title(TARGET_META[target]['short'])
    ax.set_xlabel('MDI importance')
    ax.tick_params(axis='y', labelsize=8)
    ax.grid(alpha=0.25, axis='x')

p = FIG_APPENDIX_DIR / f'{HOUSE_TYPE}_rf_importance.png'
savefig(fig, p)
display(Image(str(p)))

rf_rows = []
for target, rf_m in zip(TARGET_COLS, rf_models):
    for feature, importance in zip(PARAM_COLS, rf_m.feature_importances_):
        rf_rows.append({
            'archetype': HOUSE_TYPE,
            'target': target,
            'feature': feature,
            'importance': float(importance),
        })
pd.DataFrame(rf_rows).to_csv(RF_IMPORTANCE_CSV, index=False)
print(f"Saved → {RF_IMPORTANCE_CSV}")

# ── 5b: SHAP values via XGBoost TreeExplainer ────────────────────────────────
best_models = xgb_models
model_label = 'XGBoost'

try:
    import shap

    # He_worst beeswarm summary
    target_idx  = TARGET_COLS.index('He_worst')
    explainer   = shap.TreeExplainer(best_models[target_idx])
    shap_vals   = explainer.shap_values(X_test)

    fig_shap, ax_shap = plt.subplots(figsize=(8, 6))
    shap.summary_plot(shap_vals, X_test, feature_names=PARAM_COLS,
                      show=False, plot_size=None)
    plt.tight_layout()
    p = FIG_SHAP_HE_DIR / f'{HOUSE_TYPE}_shap_He_worst.png'
    plt.savefig(p, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    display(Image(str(p)))

    beeswarm_rows = []
    for sample_idx in range(X_test.shape[0]):
        for feature_idx, feature in enumerate(PARAM_COLS):
            beeswarm_rows.append({
                'archetype': HOUSE_TYPE,
                'target': 'He_worst',
                'sample_idx': sample_idx,
                'feature': feature,
                'feature_value': float(X_test[sample_idx, feature_idx]),
                'shap_value': float(shap_vals[sample_idx, feature_idx]),
            })
    pd.DataFrame(beeswarm_rows).to_csv(SHAP_BEESWARM_HE_CSV, index=False)
    print(f"Saved → {SHAP_BEESWARM_HE_CSV}")

    # Mean |SHAP| bar chart for all targets
    fig2, axes2 = plt.subplots(2, 3, figsize=(14, 8))
    axes2 = axes2.flatten()
    shap_rows = []
    for i, (target, model) in enumerate(zip(TARGET_COLS, best_models)):
        sv       = shap.TreeExplainer(model).shap_values(X_test)
        mean_abs = np.abs(sv).mean(axis=0)
        order    = np.argsort(mean_abs)[::-1]
        for feature, value in zip(PARAM_COLS, mean_abs):
            shap_rows.append({
                'archetype': HOUSE_TYPE,
                'target': target,
                'feature': feature,
                'mean_abs_shap': float(value),
            })
        axes2[i].barh([PARAM_COLS[j] for j in order[::-1]], mean_abs[order[::-1]],
                      color=TARGET_META[target]['color'], alpha=0.85)
        axes2[i].set_title(TARGET_META[target]['short'])
        axes2[i].set_xlabel('Mean |SHAP|')
        axes2[i].tick_params(axis='y', labelsize=8)
        axes2[i].grid(alpha=0.25, axis='x')
    p2 = FIG_IN_TEXT_DIR / f'{HOUSE_TYPE}_shap_all_targets.png'
    savefig(fig2, p2)
    display(Image(str(p2)))
    pd.DataFrame(shap_rows).to_csv(SHAP_IMPORTANCE_CSV, index=False)
    print(f"Saved → {SHAP_IMPORTANCE_CSV}")

    print(f"Figures saved → in-text: {FIG_IN_TEXT_DIR}; appendix: {FIG_APPENDIX_DIR}")
    print("SHAP analysis complete.")

except ImportError:
    print("SHAP not installed — install with: pip install shap")
    print("Using RF MDI importance as proxy.")
"""


def patch_notebook() -> None:
    nb = json.loads(NOTEBOOK.read_text())
    for cell in nb["cells"]:
        src = cell.get("source", [])
        text = "".join(src) if isinstance(src, list) else src
        if text.startswith("# ── Cell 0: Imports & Load Results"):
            cell["source"] = CELL0.splitlines(True)
        elif text.startswith("# ── Cell 1: EDA — Target Distributions"):
            cell["source"] = CELL1.splitlines(True)
        elif text.startswith("# ── Cell 3b: Neural Network (PyTorch MLP, multi-output)"):
            lines = src if isinstance(src, list) else text.splitlines(True)
            patched = []
            for line in lines:
                line = line.replace(
                    "p = FIG_DIR / 'nn_loss_curve.png'\n",
                    "p = FIG_APPENDIX_DIR / f'{HOUSE_TYPE}_nn_loss_curve.png'\n",
                )
                line = line.replace(
                    "def __init__(self, n_in=14, n_out=6):\n",
                    "def __init__(self, n_in=14, n_out=5):\n",
                )
                patched.append(line)
            cell["source"] = patched
        elif text.startswith("# ── Cell 4: Test Set Comparison — XGBoost vs MLP vs RF"):
            cell["source"] = CELL4.splitlines(True)
        elif text.startswith("# ── Cell 5: Feature Importance (RF built-in + SHAP)"):
            cell["source"] = CELL5.splitlines(True)
        elif "y = df[TARGET_COLS].values" in text:
            lines = src if isinstance(src, list) else text.splitlines(True)
            cell["source"] = [
                line.replace("y = df[TARGET_COLS].values   # shape (N, 6)\n",
                             "y = df[TARGET_COLS].values   # shape (N, 5)\n")
                for line in lines
            ]
        elif "mlp_architecture='14→128(BN+ReLU+Drop)→64(BN+ReLU+Drop)→32(ReLU)→6'" in text:
            lines = src if isinstance(src, list) else text.splitlines(True)
            cell["source"] = [
                line.replace(
                    "mlp_architecture='14→128(BN+ReLU+Drop)→64(BN+ReLU+Drop)→32(ReLU)→6'",
                    "mlp_architecture='14→128(BN+ReLU+Drop)→64(BN+ReLU+Drop)→32(ReLU)→5'",
                )
                for line in lines
            ]

    NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    patch_notebook()
    print(f"Patched {NOTEBOOK}")
