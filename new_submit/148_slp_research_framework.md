# Integrated research framework (SLP → applications)

Standard Load Profiles provide a **common descriptive foundation** for three connected uses of the same CEEW daily-profile pipeline.

```mermaid
flowchart TB
  subgraph inputs [Data and preparation]
    SM[CEEW smart meters<br/>84 m, 15-min, 43,555 days]
    DP[Daily 96-slot load profiles<br/>QA and energy balance]
  end

  subgraph core [Core: SLP characterization]
    PN[Peak normalization]
    CL[K=2 clustering / SLP centroids]
    OS[Experiment 036<br/>out-of-sample assignment]
  end

  subgraph apps [Connected applications]
    FC[Contribution B<br/>SLP-informed SVR forecasting<br/>Exp 010-018, 024-031]
    TD[Contribution C1<br/>ToD temporal analysis<br/>Exp 032 + 037 Stage A]
    BE[Contribution C2<br/>BESS under illustrative ToD<br/>Exp 033-035 physics + 037 Stage B]
  end

  SM --> DP --> PN --> CL --> OS
  CL --> FC
  CL --> TD
  TD --> BE
  OS -. validates .-> TD
  OS -. validates .-> BE
```

## Research progression (conceptual)

1. **Heterogeneous consumption** — shape, magnitude, peaking, and time-of-day structure differ across meter-days.
2. **SLP characterization** — recurring pattern regimes (not verified consumer categories); validated out-of-sample (Exp 036).
3. **SLP-informed forecasting** — distinct question: predictive value of profile features (Norwegian evaluation; comparable MAE vs persistence).
4. **ToD tariff exposure** — same profiles imply different **energy shares** in off-peak / shoulder / peak periods → different illustrative bill impacts (Exp 037 Stage A).
5. **BESS economics** — storage may shift purchases across periods, but profit depends on spread, losses, constraints, and **energy-only** tariffs (Exp 037 Stage B; **no** positive savings on medoids under tested assumptions).

## Distinctions (do not conflate)

| Layer | Question | Example evidence |
|-------|----------|------------------|
| Descriptive | Do SLPs separate patterns? | Exp 036, Cliff's δ LF ≈ 0.98 |
| Predictive | Do SLP features improve SVR? | Exp 031 MAE ~0.446 vs 0.436 persistence |
| Tariff exposure | Do groups pay differently under ToD? | Exp 037: group 1 medoid +18.6% vs flat (illustrative) |
| BESS procurement | Does storage cut energy cost? | Exp 037: **₹0** incremental on medoids (moderate, 5 kWh/2 kW) |

Peak reduction from storage studies (Exp 035) does **not** automatically equal bill savings when **demand charges are absent** (Exp 037).