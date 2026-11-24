# Timestamp comparison

- Max |Δ| validation MAE F0: **0.0869652** kWh/h
- Max |Δ| validation MAE F1: **0.0845882** kWh/h
- Max |Δ| validation MAE F2: **0.078561** kWh/h
- F1−F0 paired MAE identical across tracks: **False**

Interpretation: lag/target features indexed on publisher `(Date, Hour)` grid; timestamp label shift is an order isomorphism on the complete lattice → **forecast paths replicate** unless calendar features tied to absolute clocks differ (native Hour features identical).
