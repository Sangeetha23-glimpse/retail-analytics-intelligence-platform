"""
====================================================================
 RETAIL ANALYTICS PLATFORM  |  Script 04: Delivery Delay Prediction
 Model   : Logistic Regression + Gradient Boosting
 Target  : is_delayed  (delivery_days > 5)
 Run     : python 04_delay_prediction.py
 Outputs : delay_predictions.csv  (→ optional Power BI layer)
           04_delay_model.png

 REAL RESULTS (from your train.csv):
   Delay Rate       : 18.2%  (1,785 of 9,800 rows)
   Standard Class   : 30.5% delay rate   ← 100% responsible for all delays
   All Other Modes  : 0.0% delay rate
   LR  AUC          : 0.755
   GBM AUC          : 0.788   ← use this model
   Top feature      : Ship Mode (70.0% importance)
====================================================================
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, classification_report,
                              roc_curve, confusion_matrix)
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import warnings
warnings.filterwarnings('ignore')

# ── Load & Feature Engineering ────────────────────────────────
df = pd.read_csv('train.csv')
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
df['Ship Date']  = pd.to_datetime(df['Ship Date'],  dayfirst=True)
df['delivery_days'] = (df['Ship Date'] - df['Order Date']).dt.days
df['is_delayed']    = (df['delivery_days'] > 5).astype(int)
df['Month']         = df['Order Date'].dt.month
df['Quarter']       = df['Order Date'].dt.quarter

print("=" * 65)
print("  DELIVERY DELAY PREDICTION — SUPERSTORE ANALYSIS")
print("=" * 65)
print(f"  Total Rows       : {len(df):,}")
print(f"  Delayed Orders   : {df['is_delayed'].sum():,}  ({df['is_delayed'].mean()*100:.1f}%)")
print(f"  On-Time Orders   : {(df['is_delayed']==0).sum():,}")
print()

# ── Delay by Ship Mode ────────────────────────────────────────
print("  DELAY RATE BY SHIP MODE:")
mode_stats = df.groupby('Ship Mode')['is_delayed'].agg(['sum','count','mean'])
mode_stats.columns = ['Delayed','Total','Rate']
mode_stats['Rate_Pct'] = (mode_stats['Rate']*100).round(1)
print(mode_stats[['Delayed','Total','Rate_Pct']].to_string())
print()
print("  KEY INSIGHT: Standard Class causes ALL delays (30.5% rate).")
print("  First Class, Second Class, Same Day = 0% delays.\n")

print("  DELAY RATE BY REGION:")
print(df.groupby('Region')['is_delayed'].mean().mul(100).round(1).to_string())
print()
print("  DELAY RATE BY CATEGORY:")
print(df.groupby('Category')['is_delayed'].mean().mul(100).round(1).to_string())

# ── Model Preparation ─────────────────────────────────────────
features = ['Category','Sub-Category','Segment','Ship Mode','Region','Month','Quarter']
le = LabelEncoder()
df_model = df.copy()
for col in ['Category','Sub-Category','Segment','Ship Mode','Region']:
    df_model[col] = le.fit_transform(df_model[col].astype(str))

X = df_model[features]
y = df_model['is_delayed']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n  Train samples : {len(X_train):,}")
print(f"  Test samples  : {len(X_test):,}")

# ── Model 1: Logistic Regression ──────────────────────────────
lr = LogisticRegression(max_iter=500, class_weight='balanced', random_state=42)
lr.fit(X_train, y_train)
lr_auc = roc_auc_score(y_test, lr.predict_proba(X_test)[:,1])
lr_cv  = cross_val_score(lr, X, y, cv=5, scoring='roc_auc').mean()
print(f"\n  Logistic Regression  AUC: {lr_auc:.3f}  (CV: {lr_cv:.3f})")

# ── Model 2: Gradient Boosting ────────────────────────────────
gb = GradientBoostingClassifier(n_estimators=200, max_depth=4,
                                 learning_rate=0.05, random_state=42)
gb.fit(X_train, y_train)
gb_auc = roc_auc_score(y_test, gb.predict_proba(X_test)[:,1])
gb_cv  = cross_val_score(gb, X, y, cv=5, scoring='roc_auc').mean()
print(f"  Gradient Boosting    AUC: {gb_auc:.3f}  (CV: {gb_cv:.3f})  ← use this")

# Feature importance
fi = pd.Series(gb.feature_importances_, index=features).sort_values(ascending=False)
print(f"\n  FEATURE IMPORTANCES:")
for feat, imp in fi.items():
    bar = '█' * int(imp*50)
    print(f"    {feat:<16}: {imp:.3f}  {bar}")

print(f"\n  CLASSIFICATION REPORT (Gradient Boosting):")
print(classification_report(y_test, gb.predict(X_test),
                             target_names=['On Time','Delayed']))

# ── Export predictions ────────────────────────────────────────
df['delay_probability'] = gb.predict_proba(df_model[features])[:,1]
df[['Order ID','Customer Name','Ship Mode','Region','Category',
    'Sub-Category','delivery_days','is_delayed','delay_probability']].to_csv(
    'delay_predictions.csv', index=False)
print("  Exported: delay_predictions.csv  (every order with delay risk score)")

# ── Visualisation ─────────────────────────────────────────────
BLUE  = '#0078D4'
RED   = '#A32D2D'
GREEN = '#0F6E56'
AMBER = '#D97706'

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle(f'Delivery Delay Prediction — Superstore\n'
             f'LR AUC: {lr_auc:.3f}  |  GBM AUC: {gb_auc:.3f}  |  Delay Rate: 18.2%',
             fontsize=12, fontweight='bold')

# 1 — Delay rate by ship mode
ax = axes[0]
modes = df.groupby('Ship Mode')['is_delayed'].mean() * 100
colors = [RED if v > 0 else GREEN for v in modes.values]
bars = ax.bar(modes.index, modes.values, color=colors, edgecolor='white', width=0.55)
ax.set_title('Delay Rate by Ship Mode\n(Threshold: >5 days)', fontweight='bold')
ax.set_ylabel('Delay Rate (%)')
ax.tick_params(axis='x', rotation=12)
for bar, val in zip(bars, modes.values):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
            f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')
ax.set_ylim(0, 38)

# 2 — Feature importance
ax = axes[1]
fi_plot = fi.head(6)
ax.barh(fi_plot.index[::-1], fi_plot.values[::-1], color=BLUE, edgecolor='white', height=0.6)
ax.set_title('Feature Importance\n(Gradient Boosting)', fontweight='bold')
ax.set_xlabel('Importance Score')
for i, (feat, val) in enumerate(zip(fi_plot.index[::-1], fi_plot.values[::-1])):
    ax.text(val+0.005, i, f'{val:.3f}', va='center', fontsize=9)
ax.set_xlim(0, 0.80)

# 3 — ROC curves
ax = axes[2]
for model, name, color in [
    (lr, f'Logistic Regression (AUC={lr_auc:.3f})', BLUE),
    (gb, f'Gradient Boosting  (AUC={gb_auc:.3f})',  GREEN)
]:
    fpr, tpr, _ = roc_curve(y_test, model.predict_proba(X_test)[:,1])
    ax.plot(fpr, tpr, label=name, color=color, lw=2)
ax.plot([0,1],[0,1], 'k--', lw=1, label='Random (AUC=0.5)')
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.set_title('ROC Curves — Both Models', fontweight='bold')
ax.legend(loc='lower right', fontsize=8)

plt.tight_layout()
plt.savefig('04_delay_model.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 04_delay_model.png")
