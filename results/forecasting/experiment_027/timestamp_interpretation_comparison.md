# Timestamp interpretation comparison

        ## Candidate conventions

        | Code | Hour 1 | Hour 24 | Formula |
        |------|--------|---------|---------|
        | `H1_START_00` | 00:00–01:00 (proposed) | 23:00–24:00 | `Date + (Hour−1)h` |
        | `H1_START_01` | 01:00–02:00 | 24:00–01:00 (+1 day) | `Date + Hour h` |

        ## Data-only observations (cannot pick convention alone)

        - Complete 24-slot grid on every Date for every household.
        - Uniform series length 13,128 rows.
        - No duplicate (ID, Date, Hour) keys in file (Experiment 026).

        ## Eligibility impact

        ```
        {
  "H1_START_00": {
    "n_p2_total": 14719152,
    "households_with_p2": 1136,
    "identical_to_other": true
  },
  "H1_START_01": {
    "n_p2_total": 14719152,
    "households_with_p2": 1136,
    "identical_to_other": true
  }
}
        ```

        On this dataset, P2 eligible origin counts are **identical** under both conventions because eligibility uses **uniform +1h** and **−k·1h** lookups on a complete rectilinear (Date, Hour) lattice; the mapping is an order-isomorphism shifting all timestamps by +1h.

        **Consequence:** P2 population counts do **not** discriminate between `H1_START_00` and `H1_START_01`. External alignment (e.g. Nordpool `prices.csv`) would be needed to break the tie — not resolved in documentation.

        ## prices.csv

        ```
        {
  "prices_local": false
}
        ```

        Shared Hour column supports joinability, not interval-end proof.
