# DST audit — demand.csv

        ## Documented publisher handling

        Quoted policy: each civil **Date** has exactly **24** hourly records; spring transition hour imputed; autumn duplicated hour collapsed (Data in Brief §4.2).

        ## Empirical checks (full 1,136 households)

        | Metric | Result |
        |--------|--------|
        | Hour indices present | [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24] |
        | Records per household | 13,128 (uniform) |
        | Unique dates per household | 547 |
        | (ID, Date) groups with ≠24 hours | 0 |
        | DST transition calendar dates inspected | 2020-10-25, 2021-03-28, 2021-10-31, 2022-03-27 |

        ### Records on DST dates (per household)

        ```
        {
  "2020-10-25": {
    "min": 24,
    "max": 24,
    "unique": 1
  },
  "2021-03-28": {
    "min": 24,
    "max": 24,
    "unique": 1
  },
  "2021-10-31": {
    "min": 24,
    "max": 24,
    "unique": 1
  },
  "2022-03-27": {
    "min": 24,
    "max": 24,
    "unique": 1
  }
}
        ```

        **Interpretation:** Empirical pattern matches publisher claim of **24 rows per date** on transition days. This confirms **normalization**, not raw wall-clock continuity. **No DST indicator column** in `demand.csv`.

        ## Protocol implication

        - Seasonal-naive **elapsed 24h** and civil week-ago alternatives remain **metadata-blocked** per DEC-024A-06 / 024C.
        - P2 (no seasonal-naive requirement) is **not blocked** by SN/DST policy alone.
