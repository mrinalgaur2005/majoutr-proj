# Feature engineering

**F0:** lag 1/24/168, sin/cos native Hour, weekend flag (Date weekday).

**F1:** F0 + category-level SLP at **target slot** (`Hour`/`Date` at row i+1), template pool = all households with row index `< i` (strict causal, native slot).

**F2:** F0 + profile-level SLP, same causality within household.

**SLP calendar disclosure:** Publisher DST normalization (spring imputed hour, autumn duplicate omitted). Not IANA civil time.

`t_available = t_timestamp` — idealized, not verified.
