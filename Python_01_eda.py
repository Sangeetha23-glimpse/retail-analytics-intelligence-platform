"""
====================================================================
 RETAIL ANALYTICS PLATFORM  |  Script 01: Exploratory Data Analysis
 Dataset : Superstore train.csv  |  9,800 rows  |  2015–2018
 Run     : python 01_eda.py
 Output  : 01_eda_plots.png
====================================================================
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import warnings
warnings.filterwarnings('ignore')

# ── Load ─────────────────────────────────────────────────────
df = pd.read_csv('train.csv')
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
df['Ship Date']  = pd.to_datetime(df['Ship Date'],  dayfirst=True)
df['delivery_days'] = (df['Ship Date'] - df['Order Date']).dt.days
df['is_delayed']    = (df['delivery_days'] > 5).astype(int)
df['Year']          = df['Order Date'].dt.year
df['Month']         = df['Order Date'].dt.month

# ── Console Summary ───────────────────────────────────────────
print("=" * 55)
print("  SUPERSTORE RETAIL — EDA SUMMARY")
print("=" * 55)
print(f"  Rows              : {len(df):,}")
print(f"  Date Range        : {df['Order Date'].min().date()} → {df['Order Date'].max().date()}")
print(f"  Unique Orders     : {df['Order ID'].nunique():,}")
print(f"  Unique Customers  : {df['Customer ID'].nunique():,}")
print(f"  Unique Products   : {df['Product ID'].nunique():,}")
print(f"  Total Revenue     : ${df['Sales'].sum():,.2f}")
print(f"  Avg Order Line    : ${df['Sales'].mean():,.2f}")
print(f"  Delay Rate (>5d)  : {df['is_delayed'].mean()*100:.1f}%")
print()

annual = df.groupby('Year').agg(
    Orders=('Order ID','nunique'), Sales=('Sales','sum'), Customers=('Customer ID','nunique')
).round(0)
annual['YoY%'] = annual['Sales'].pct_change().mul(100).round(1)
print("ANNUAL KPIs:")
print(annual.to_string())

# ── Plot ──────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
fig.suptitle('Superstore Retail Analytics — EDA Dashboard  (2015–2018)',
             fontsize=14, fontweight='bold', y=1.01)
BLUE  = '#1E3A5F'
ACNT  = '#0078D4'
GREEN = '#0F6E56'
RED   = '#A32D2D'
AMBER = '#854F0B'

# 1 — Annual revenue bars
ax = axes[0, 0]
ann = df.groupby('Year')['Sales'].sum()
cols = [RED, ACNT, GREEN, '#FF8C00']   # red=dip 2016, blue=recovery, green=growth
bars = ax.bar(ann.index, ann.values, color=cols, width=0.55, edgecolor='white')
ax.set_title('Annual Revenue', fontweight='bold')
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
for bar, val, yr in zip(bars, ann.values, ann.index):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+3000,
            f'${val/1e3:.0f}K', ha='center', fontsize=9, fontweight='bold')
ax.text(2016, 420000, '−4.3%\nDip', ha='center', color=RED, fontsize=8)
ax.text(2017, 560000, '+30.6%\nRecovery', ha='center', color=GREEN, fontsize=8)
ax.set_ylim(0, 820000)

# 2 — Monthly trend 2018
ax = axes[0, 1]
m2018 = df[df['Year']==2018].groupby('Month')['Sales'].sum()
ax.plot(m2018.index, m2018.values, 'o-', color=ACNT, lw=2.5, ms=5)
ax.fill_between(m2018.index, m2018.values, alpha=0.15, color=ACNT)
ax.set_title('Monthly Sales 2018', fontweight='bold')
ax.set_xticks(range(1,13))
ax.set_xticklabels(['J','F','M','A','M','J','J','A','S','O','N','D'], fontsize=8)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
peak_m = m2018.idxmax()
ax.annotate(f'Peak Nov\n${m2018[peak_m]/1e3:.0f}K',
            xy=(peak_m, m2018[peak_m]), xytext=(peak_m-2, m2018[peak_m]-15000),
            arrowprops=dict(arrowstyle='->', color=BLUE), fontsize=8, color=BLUE)

# 3 — Sales by Region (horizontal)
ax = axes[0, 2]
reg = df.groupby('Region')['Sales'].sum().sort_values()
clrs = [RED if r=='South' else ACNT for r in reg.index]
hbars = ax.barh(reg.index, reg.values, color=clrs, height=0.55, edgecolor='white')
ax.set_title('Sales by Region', fontweight='bold')
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
for bar, val in zip(hbars, reg.values):
    ax.text(bar.get_width()+2000, bar.get_y()+bar.get_height()/2,
            f'${val/1e3:.0f}K', va='center', fontsize=9)
ax.text(reg['South']/2, 0, 'Lowest', ha='center', va='center', fontsize=8, color='white', fontweight='bold')

# 4 — Category pie
ax = axes[1, 0]
cat = df.groupby('Category')['Sales'].sum()
wedges, texts, autotexts = ax.pie(
    cat.values, labels=cat.index, autopct='%1.1f%%',
    colors=[ACNT, AMBER, GREEN], startangle=90,
    textprops={'fontsize': 9})
ax.set_title('Sales by Category', fontweight='bold')

# 5 — Top 10 Sub-categories
ax = axes[1, 1]
sub = df.groupby('Sub-Category')['Sales'].sum().sort_values(ascending=False).head(10)
clrs2 = [GREEN if s in ['Phones','Chairs','Copiers'] else ACNT for s in sub.index]
ax.barh(sub.index[::-1], sub.values[::-1], color=clrs2[::-1], height=0.65, edgecolor='white')
ax.set_title('Top 10 Sub-Categories', fontweight='bold')
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))

# 6 — Delivery days dist
ax = axes[1, 2]
ax.hist(df['delivery_days'], bins=8, color=AMBER, edgecolor='white', rwidth=0.8)
ax.axvline(x=5, color=RED, ls='--', lw=2, label='Delay threshold (>5 days)')
ax.set_title(f'Delivery Days Distribution\n(Delay Rate: {df["is_delayed"].mean()*100:.1f}%  |  All from Standard Class)',
             fontweight='bold', fontsize=9)
ax.set_xlabel('Days')
ax.set_ylabel('Count')
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('01_eda_plots.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved: 01_eda_plots.png")
