Original rule does not enforce cyclic SOC; medoids finish at SOC 0.9 (cluster 0) or ≈0.59 (cluster 1) after aggressive charging.
`rule_dispatch_cyclic` adds restoration, but cyclic closure is infeasible on these days without worsening peaks (no export).
**Fair dispatch comparison:** use optimized LP with SOC_final=SOC₀ or report conversion loss and Δstored separately for rule.
See `corrected_medoid_metrics.csv`.
