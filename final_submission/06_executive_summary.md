# Executive summary

## Title

**Standard Load Profile-informed Support Vector Regression for short-term electricity load forecasting**

## What the study does

Daily electricity use is heterogeneous in shape, magnitude, load factor, and the hours in which energy is taken. The project builds standard load profiles from 15-minute meter data, checks that those profiles describe held-out meters, and tests whether profile information changes short-term support-vector forecasts. Time-of-day prices and battery operation are then used as supplementary questions: do the same pattern groups face different illustrative energy costs, and does storage reduce procurement cost under the stated constraints?

## Characterization

On the Mathura–Bareilly smart-meter records, **84 meters** and **43,555** complete daily profiles support a two-group, peak-normalized representation (silhouette about **0.242**). The groups differ in mean daily energy (**about 10.93 kWh** and **6.20 kWh**) and load factor (**about 0.47** and **0.20**). They are pattern regimes, not verified consumer classes.

Out-of-sample assignment used five meter-level splits (**58** training meters and **26** held-out meters each time). Held-out groups remain distinguishable: median Cliff's delta about **+0.98** for load factor and **−0.98** for the peak-to-average ratio. Matched centroid shapes agree across splits (mean correlation about **0.983**).

## Forecasting

On the corrected Norwegian residential cohort, test macro mean absolute error is **0.4361** for persistence, **0.4457** for tuned support-vector regression, and **0.4537** when the tested profile features are included. The methods sit in a similar error band. Profile features did not improve on persistence in that evaluation. That predictive result is separate from the descriptive result above.

## Supplementary prices and storage

Under an illustrative moderate price table (₹5, ₹8, and ₹12 per kWh in off-peak, shoulder, and peak windows), one representative day in the higher-energy group moves from a flat bill of about **₹108.24** to about **₹108.91**. The representative day in the peakier group moves from about **₹20.06** to about **₹23.80** (about **+18.6%**). These are not utility bills.

With 90% round-trip efficiency, a cyclic state of charge, and no demand charge, cost-minimizing storage does not reduce procurement cost on those two days (no incremental saving at 5 kWh and 2 kW). Peak reduction from a separate peak-shaving study is not the same as a lower energy bill when only energy prices apply.

## Takeaway

Standard load profiles give a structured description of daily demand that supports forecasting tests and a disciplined look at time-varying prices and storage. The forecasting comparison and the storage-cost comparison are reported as measured, including where they do not show a gain.
