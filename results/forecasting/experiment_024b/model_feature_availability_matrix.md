# Model feature availability matrix

| Component | Persistence | SNaive | ARIMA | SVR F0 | SVR F1 | SVR F2 | Source rule | Shared | Future info |
|-----------|-------------|--------|-------|--------|--------|--------|-------------|--------|-------------|
| Current `y(t_origin)` | Y | — | series | lag1 | lag1 | lag1 | exact row | Y | No |
| Lag 1 | — | — | series | Y | Y | Y | `t_o−1Δ` | Y | No |
| Daily lag | — | — | series | Y | Y | Y | `t_o−24Δ` or `48Δ` | Y | No |
| Weekly lag | — | — | series | Y | Y | Y | `t_o−168Δ` or `336Δ` | Y | No |
| Calendar (origin) | — | — | — | Y | Y | Y | `t_origin` | Y | No |
| Category SLP | — | — | — | — | Y | — | `slot_target`, pool `<t_o` | Y | No if Policy A |
| Profile SLP | — | — | — | — | — | Y | `slot_target`, profile `<t_o` | Y | No |
| SNaive ref | — | Y | — | — | — | — | `t_target−24h` | Y | No |
| ARIMA fit | — | — | train slice | — | — | — | train rows only | — | No |

F0/F1/F2 differ **only** by SLP columns as specified.
