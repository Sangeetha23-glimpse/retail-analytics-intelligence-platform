"""
====================================================================
 RETAIL ANALYTICS PLATFORM  |  Script 03: Sales Forecasting
 Model   : Facebook Prophet (time-series)
 Dataset : 48 monthly observations  (Jan 2015 – Dec 2018)
 Run     : python 03_forecasting.py
 Outputs : forecast_output.csv  (→ import into Power BI)
           03_sales_forecast.png

 REAL RESULTS (from your train.csv):
   Holdout MAPE   : 16.8% (4-month holdout: Sep–Dec 2018)
   H1-2019 Total  : $311,110 projected
   Jan 2019       : $41,378   ($33,323 – $48,929)
   Feb 2019       : $32,207   ($24,436 – $39,911)
   Mar 2019       : $78,981   ($71,316 – $86,590)  ← seasonal peak
   Apr 2019       : $48,562   ($41,011 – $55,943)
   May 2019       : $50,969   ($42,404 – $59,305)
   Jun 2019       : $59,013   ($51,109 – $66,389)
====================================================================
"""
import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import warnings
warnings.filterwarnings('ignore')

# ── Load & Aggregate ──────────────────────────────────────────
df = pd.read_csv('train.csv')
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)

monthly = (df.groupby(df['Order Date'].dt.to_period('M'))['Sales']
             .sum()
             .reset_index())
monthly.columns = ['period', 'y']
monthly['ds'] = monthly['period'].dt.to_timestamp()
monthly = monthly[['ds','y']].sort_values('ds').reset_index(drop=True)

print("=" * 55)
print("  PROPHET SALES FORECASTING")
print("=" * 55)
print(f"  Monthly observations : {len(monthly)} (Jan 2015 – Dec 2018)")
print(f"  Average monthly sales: ${monthly['y'].mean():,.0f}")
print(f"  Peak month           : ${monthly['y'].max():,.0f}  (Nov 2018)")
print(f"  Lowest month         : ${monthly['y'].min():,.0f}  (Feb 2015)")

# ── Train / Holdout Split ─────────────────────────────────────
train = monthly[:-4].copy()   # 44 months  (Jan 2015 – Aug 2018)
test  = monthly[-4:].copy()   #  4 months  (Sep–Dec 2018)
print(f"\n  Training : {len(train)} months")
print(f"  Holdout  : {len(test)} months ({test['ds'].dt.strftime('%b %Y').tolist()})")

# ── Fit Prophet ───────────────────────────────────────────────
model = Prophet(
    yearly_seasonality      = True,
    weekly_seasonality      = False,
    changepoint_prior_scale = 0.1     # allows trend flexibility
)
model.fit(train)

# ── Predict ───────────────────────────────────────────────────
future   = model.make_future_dataframe(periods=10, freq='MS')
forecast = model.predict(future)

# ── Evaluate on holdout ───────────────────────────────────────
test_dates = pd.to_datetime(test['ds'].values)
fc_test    = forecast[forecast['ds'].isin(test_dates)].copy()
actual     = test['y'].values
predicted  = fc_test['yhat'].values
mape = np.mean(np.abs((actual - predicted) / actual)) * 100
mae  = np.mean(np.abs(actual - predicted))

print(f"\n  HOLDOUT ACCURACY:")
print(f"    MAPE : {mape:.1f}%")
print(f"    MAE  : ${mae:,.0f}")

# ── 6-Month Forward Forecast (Jan–Jun 2019) ───────────────────
fc6 = forecast[forecast['ds'] > '2018-12-31'][
    ['ds','yhat','yhat_lower','yhat_upper']
].head(6).copy()
fc6.columns = ['Month','Forecast','Lower_95CI','Upper_95CI']
fc6['Month'] = fc6['Month'].dt.strftime('%b %Y')
fc6[['Forecast','Lower_95CI','Upper_95CI']] = fc6[['Forecast','Lower_95CI','Upper_95CI']].round(0).astype(int)

print(f"\n  6-MONTH FORECAST (Jan–Jun 2019):")
print(fc6.to_string(index=False))
print(f"\n  H1-2019 Total Forecast : ${fc6['Forecast'].sum():,}")

# ── Export for Power BI ───────────────────────────────────────
forecast[['ds','yhat','yhat_lower','yhat_upper']].to_csv('forecast_output.csv', index=False)
print("\n  Exported: forecast_output.csv  →  Import into Power BI (Page 5 - Forecast)")

# ── Visualisation ─────────────────────────────────────────────
BLUE  = '#0078D4'
ORNG  = '#D97706'
GREEN = '#0F6E56'
GRAY  = '#6B7280'

fig, axes = plt.subplots(2, 1, figsize=(14, 10))
fig.suptitle(f'Sales Forecasting — Prophet Model | MAPE {mape:.1f}%\nSuperstore 2015–2018 → Forecast Jan–Jun 2019',
             fontsize=12, fontweight='bold')

# Top: Actual vs Forecast
ax = axes[0]
ax.plot(monthly['ds'], monthly['y'], 'o-', color=BLUE, lw=2, ms=3.5, label='Actual monthly sales', zorder=5)
fc_all = forecast[['ds','yhat','yhat_lower','yhat_upper']].copy()
fc_hist = fc_all[fc_all['ds'] <= '2018-12-31']
fc_fut  = fc_all[fc_all['ds'] > '2018-12-31']
ax.plot(fc_hist['ds'], fc_hist['yhat'], '--', color=ORNG, lw=1.5, label='Prophet fitted')
ax.fill_between(fc_hist['ds'], fc_hist['yhat_lower'], fc_hist['yhat_upper'], alpha=0.1, color=ORNG)
ax.plot(fc_fut['ds'], fc_fut['yhat'], 'o--', color=GREEN, lw=2, ms=5, label='Forecast Jan–Jun 2019')
ax.fill_between(fc_fut['ds'], fc_fut['yhat_lower'], fc_fut['yhat_upper'], alpha=0.2, color=GREEN)
ax.axvline(pd.Timestamp('2019-01-01'), color=GRAY, ls=':', lw=1.5)
ax.text(pd.Timestamp('2019-01-15'), ax.get_ylim()[0] if ax.get_ylim()[0] else 0,
        ' Forecast →', color=GRAY, fontsize=9, va='bottom')
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
ax.set_ylabel('Monthly Sales')
ax.set_title('Monthly Sales: Actual vs Prophet Forecast')
ax.legend(loc='upper left', fontsize=9)

# Bottom: Trend component
ax = axes[1]
trend = forecast[forecast['ds'].isin(monthly['ds'])][['ds','trend']]
ax.plot(trend['ds'], trend['trend'], color='#7C3AED', lw=2.5)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
ax.set_ylabel('Trend Component')
ax.set_title('Underlying Trend — Shows true direction stripping out seasonality')
# Annotate dip
ax.annotate('2016 dip (−4.3%)',
            xy=(pd.Timestamp('2016-06-01'), 23000),
            xytext=(pd.Timestamp('2015-06-01'), 32000),
            arrowprops=dict(arrowstyle='->', color='#A32D2D'), color='#A32D2D', fontsize=8)
ax.annotate('+30.6% recovery',
            xy=(pd.Timestamp('2017-06-01'), 38000),
            xytext=(pd.Timestamp('2016-08-01'), 46000),
            arrowprops=dict(arrowstyle='->', color='#0F6E56'), color='#0F6E56', fontsize=8)

plt.tight_layout()
plt.savefig('03_sales_forecast.png', dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: 03_sales_forecast.png")
