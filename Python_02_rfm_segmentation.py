"""
====================================================================
 RETAIL ANALYTICS PLATFORM  |  Script 02: RFM Customer Segmentation
 Dataset : Superstore train.csv  |  793 unique customers
 Run     : python 02_rfm_segmentation.py
 Outputs : rfm_output.csv  (→ import into Power BI)
           02_rfm_segments.png

 REAL RESULTS:
   Champions           169 customers  $664,889  (29.4% of revenue)
   Loyal Customers     166 customers  $570,646  (25.2%)
   At Risk             141 customers  $489,373  (21.6%)  ← priority
   Potential Loyalists 157 customers  $294,247  (13.0%)
   Recent Customers     89 customers  $158,482  ( 7.0%)
   Lost                 71 customers   $83,900  ( 3.7%)
====================================================================
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# ── Load ─────────────────────────────────────────────────────
df = pd.read_csv('train.csv')
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
snapshot = df['Order Date'].max() + pd.Timedelta(days=1)  # 2018-12-31

# ── RFM Calculation ───────────────────────────────────────────
rfm = df.groupby(['Customer ID','Customer Name']).agg(
    Recency   = ('Order Date', lambda x: (snapshot - x.max()).days),
    Frequency = ('Order ID',   'nunique'),
    Monetary  = ('Sales',      'sum')
).reset_index()

# Quintile scoring 1–5
rfm['R_score'] = pd.qcut(rfm['Recency'],   q=5, labels=[5,4,3,2,1], duplicates='drop')
rfm['F_score'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5])
rfm['M_score'] = pd.qcut(rfm['Monetary'],  q=5, labels=[1,2,3,4,5], duplicates='drop')
rfm['RFM_score'] = rfm[['R_score','F_score','M_score']].astype(int).sum(axis=1)

# ── Segment Labels ────────────────────────────────────────────
def assign_segment(row):
    r, f = int(row.R_score), int(row.F_score)
    if   r >= 4 and f >= 4: return 'Champions'
    elif r >= 3 and f >= 3: return 'Loyal Customers'
    elif r >= 4 and f <= 2: return 'Recent Customers'
    elif r <= 2 and f >= 3: return 'At Risk'
    elif r == 1 and f == 1: return 'Lost'
    else:                   return 'Potential Loyalists'

rfm['Segment'] = rfm.apply(assign_segment, axis=1)

# ── Summary ───────────────────────────────────────────────────
summary = rfm.groupby('Segment').agg(
    Customers     = ('Customer ID', 'count'),
    Avg_Recency   = ('Recency',     'mean'),
    Avg_Frequency = ('Frequency',   'mean'),
    Avg_Monetary  = ('Monetary',    'mean'),
    Total_Revenue = ('Monetary',    'sum')
).round(1)
summary['Revenue_Share_Pct'] = (summary['Total_Revenue'] / summary['Total_Revenue'].sum() * 100).round(1)
summary = summary.sort_values('Total_Revenue', ascending=False)

print("=" * 65)
print("  RFM CUSTOMER SEGMENTATION — SUPERSTORE 2015–2018")
print("=" * 65)
print(summary.to_string())
print()

print("TOP 10 CHAMPIONS (highest-value loyal customers):")
champs = rfm[rfm['Segment']=='Champions'].sort_values('Monetary', ascending=False)
print(champs[['Customer Name','Recency','Frequency','Monetary','RFM_score']].head(10).to_string())
print()

print("TOP 10 AT-RISK CUSTOMERS (priority re-engagement list):")
at_risk = rfm[rfm['Segment']=='At Risk'].sort_values('Monetary', ascending=False)
print(at_risk[['Customer Name','Recency','Frequency','Monetary']].head(10).to_string())
print()

# ── Export for Power BI ───────────────────────────────────────
rfm.to_csv('rfm_output.csv', index=False)
print("Exported: rfm_output.csv  →  Import this into Power BI (Page 4 - Customer Insights)")

# ── Visualisation ─────────────────────────────────────────────
SEG_COLORS = {
    'Champions':           '#0F6E56',
    'Loyal Customers':     '#0078D4',
    'At Risk':             '#D97706',
    'Potential Loyalists': '#7C3AED',
    'Recent Customers':    '#6B7280',
    'Lost':                '#A32D2D',
}

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('RFM Customer Segmentation — Superstore 793 Customers',
             fontsize=13, fontweight='bold')

# 1 — Customer count bars
ax = axes[0]
counts = rfm['Segment'].value_counts()
clrs = [SEG_COLORS[s] for s in counts.index]
hb = ax.barh(counts.index, counts.values, color=clrs, height=0.6, edgecolor='white')
ax.set_title('Customers per Segment', fontweight='bold')
ax.set_xlabel('Number of Customers')
for bar, val in zip(hb, counts.values):
    ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
            str(val), va='center', fontsize=10, fontweight='bold')

# 2 — Revenue share pie
ax = axes[1]
rev_share = rfm.groupby('Segment')['Monetary'].sum().sort_values(ascending=False)
clrs2 = [SEG_COLORS[s] for s in rev_share.index]
wedges, texts, autotexts = ax.pie(
    rev_share.values, labels=rev_share.index,
    autopct='%1.1f%%', colors=clrs2, startangle=90,
    textprops={'fontsize': 8}
)
ax.set_title('Revenue Share by Segment', fontweight='bold')

# 3 — Recency vs Frequency scatter
ax = axes[2]
for seg, grp in rfm.groupby('Segment'):
    ax.scatter(grp['Recency'], grp['Frequency'],
               s=grp['Monetary']/80, alpha=0.6,
               color=SEG_COLORS[seg], label=seg, edgecolors='white', lw=0.3)
ax.set_xlabel('Recency (days since last order) →')
ax.set_ylabel('Frequency (unique orders)')
ax.set_title('Recency vs Frequency\n(bubble size = revenue)', fontweight='bold')
ax.invert_xaxis()
ax.legend(loc='upper right', fontsize=7, framealpha=0.8)

plt.tight_layout()
plt.savefig('02_rfm_segments.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 02_rfm_segments.png")
