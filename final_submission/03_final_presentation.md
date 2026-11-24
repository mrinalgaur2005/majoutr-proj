# Final evaluation presentation (~12–15 minutes)

**Format:** ~22 slides. **Audience:** Electrical engineering faculty.

---

## Slide 1 — Title

**Title:** Standard Load Profile-Based Characterization and SVR-Based Short-Term Electricity Load Forecasting

**Bullets:** [Student], [Guide] • Contributions: characterization → forecasting → energy management (illustrative) • Exp 001–037

---

## Slide 2 — Why consumption patterns matter

**Bullets:** Shape, magnitude, load factor, peak timing, morning/afternoon/evening splits • Heterogeneity hidden if all curves treated alike

**Figure:** `figures/exp032_ceew_mean_daily.png`

---

## Slide 3 — Research questions (three tracks)

**Bullets:** **A** Can SLPs characterize recurring patterns? **B** Can SLPs inform SVR forecasting? **C** Do patterns imply different ToD exposure / storage economics?

**Figure:** `07_slp_research_framework.md` (mermaid flow — show on backup slide)

---

## Slide 4 — Datasets

**Bullets:** CEEW 84 m, 43,555 days (characterization + Exp 037) • Norway 1,136 HH (forecasting audit) • No ag/res labels

---

## Slide 5 — SLP construction (K=2)

**Bullets:** 96-slot profiles • Peak-normalized centroids • Two pattern regimes • **Not** residential vs agricultural

**Figure:** `figures/exp032_cluster_profiles.png`

---

## Slide 6 — Experiment 036 (out-of-sample)

**Bullets:** 58/26 meter splits • Frozen centroids • Held-out groups differ (δ_LF ≈ 0.98) • Centroid corr ≈ 0.983

**Figure:** `figures/exp036_heldout_bands.png`

---

## Slide 7 — Forecasting (distinct question)

**Bullets:** SLP-informed SVR • Macro MAE: persistence **0.436** vs SVR **~0.446** • Comparable — limited SLP increment

**Figure:** `figures/exp031_test_macro_mae.png`

**Notes:** Characterization ≠ forecasting improvement.

---

## Slide 8 — Why energy management follows SLP work

**Bullets:** SLPs encode **when** energy is used • ToD tariffs price intervals differently • Same tariff, different profiles → different bills

---

## Slide 9 — Introducing Time-of-Day tariffs (illustrative)

**Bullets:** Off-peak / shoulder / peak prices • **Illustrative INR/kWh** — not real utility tariffs • 96 × 15-min assignment

**Figure:** `figures/exp037_tariff_schedule.png`

---

## Slide 10 — Consumption across tariff periods by SLP group

**Bullets:** Groups place different energy shares in peak vs off-peak • From characterized profiles (Exp 032 + 037)

**Figure:** `figures/exp037_period_energy_by_group.png`

---

## Slide 11 — Differential tariff exposure (moderate spread)

**Bullets:** Group 0 BR29: flat **₹108.24** → ToD **₹108.91** (+0.6%) • Group 1 MH31: **₹20.06** → **₹23.80** (+18.6%) • Illustrative medoids only

**Figure:** `figures/exp037_flat_vs_tod_bills.png`

**Notes:** Higher absolute bill vs higher **relative** ToD penalty.

---

## Slide 12 — Why BESS might shift purchases

**Bullets:** Charge cheap intervals • Discharge when prices high • Constrained by η, SOC, power, cyclic balance • **No demand charge** in model

---

## Slide 13 — BESS methodology (Exp 037)

**Bullets:** Exp 035 physics + cost-minimizing MILP • 5 kWh / 2 kW example • 240 scenarios on medoids • Compare rule vs optimized vs no BESS

---

## Slide 14 — BESS economics result

**Bullets:** Moderate spread, 5 kWh / 2 kW: **₹0** incremental savings both groups • Optimizer selects **no operation** • Losses + spread insufficient

**Figure:** `figures/exp037_spread_sensitivity.png` (optional)

---

## Slide 15 — Peak vs bill (important distinction)

**Bullets:** Exp 035: peak **reduction** possible (e.g. −27% MILP group 0) • Exp 037: **energy bill** unchanged without demand charges • Do not equate the two

**Figure:** `figures/exp035_dispatch_comparison.png` (small inset — supporting only)

---

## Slide 16 — Integrated framework

**Bullets:** Consumption → profiles → SLPs → {forecasting | ToD exposure | BESS evaluation}

**Figure:** Framework mermaid (`07_slp_research_framework.md`)

---

## Slide 17 — Limitations

**Bullets:** Illustrative tariffs • Two medoids for BESS economics • Synopsis Ireland–Spain not complete • BESS not central project identity

---

## Slide 18 — Conclusion

**Bullets:** SLPs **describe** patterns (validated out-of-sample) • SVR **evaluated** honestly • ToD/BESS show **how** to use profiles for management studies — not guaranteed savings

**Notes:** Questions welcome.