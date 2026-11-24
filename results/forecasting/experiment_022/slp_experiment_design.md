# Controlled SLP experiment design (future — 022)

| ID | Feature strategy | Definition | Leakage risk |
|----|------------------|------------|--------------|
| F0 | No SLP | Lags + calendar only | Low |
| F1 | Shared category SLP | Hour-of-week mean from train pool (current 020) | Low if train-only |
| F2 | Per-profile SLP | Hour-of-week mean from single meter train | Low |
| F3 | Cluster centroid | K cluster templates on **train** segments only; no future labels | Medium if mis-specified K |
| F4 | Previous-day profile | Lags of hourly profile from day $d-1$ | Low if day complete before origin |
| F5 | Partial-day profile | Only hours $<$ origin hour on day $d$ | Low |

## Ablation ladder
Persistence, seasonal-naive (24h lag), ARIMA(1,0,1), SVR(F0)…SVR(F5).

## Success criteria (register before run)
- Primary: ΔMAE vs persistence on validation (not test).
- Secondary: peak-regime MAE, event recall for spikes (profile 00489 class).

## 021 finding
- Shared template (F1) overlaps calendar; expect limited gain until F2–F5 tested.