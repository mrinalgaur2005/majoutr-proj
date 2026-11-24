# Source documentation review — Zenodo 10.5281/zenodo.7856848

## Sources inspected (public)

| Source | URL / DOI | Use |
|--------|-----------|-----|
| Zenodo record | https://zenodo.org/records/7856848 | Dataset listing, CC-BY-4.0 |
| Data in Brief article | https://doi.org/10.1016/j.dib.2023.109687 | Table structure, collection, DST handling |
| PMC full text | https://pmc.ncbi.nlm.nih.gov/articles/PMC10618698/ | Same article (open access) |

## Findings

### Date column
- **Evidence:** Table 5 — "Date | yyyy-mm-dd | Date of observation" (10.1016/j.dib.2023.109687, §3.2.4).
- **Confidence:** High for format; **medium** that Date is **local civil calendar date** after publisher DST normalization (not stated as IANA timezone; implied by Norway metering context and explicit DST preprocessing in §4.2).
- **Direct / suggestive:** Suggestive for local civil date; not an IANA timezone declaration.

### Hour column (1–24)
- **Evidence:** Table 5 — "Hour | 1, …, 24 | Hour of the day"; `Demand_kWh` described as "kWh/h".
- **Confidence:** High that Hour is an integer slot index 1–24 on each Date.
- **Hour 1 = 00:00–01:00 vs 01:00–02:00:** **UNRESOLVED** — no explicit clock mapping in Table 5 or §4.2.
- **Interval start vs end:** **UNRESOLVED** — documentation does not state whether energy accrues over the preceding or following clock hour.

### DST and timezone
- **Evidence (direct):** §4.2 Hourly data — "To mitigate complications arising from daylight-savings time switches, each day in the dataset has 24 hours. The springtime missing hour was calculated as the average of values from the preceding and succeeding hours. The extra hour in autumn was dealt with by omitting the second hour of the doubled hours."
- **Confidence:** High that publisher **normalized** civil days to 24 hourly slots; DST gaps/duplicates are **not represented as ambiguous rows** in the published CSV.
- **IANA timezone string:** **Not documented** in sources reviewed.
- **t_available / publication latency:** **Not documented.**

### Data provenance
- Smart-meter data via local grid companies and Elhub (10.1016/j.dib.2023.109687, metadata table).
- Individual demand October 2020–March 2022, Oslo and Bergen subsets (1,136 households).

### Related prior dataset (not primary for 7856848 schema)
- Hofmann & Siebenbrunner, Data in Brief 50, doi:10.1016/j.dib.2023.109571 (iFlex experiment) — separate Zenodo; not cited as normative for Hour clock mapping in 7856848.

## zenodo extras
- No separate README on Zenodo clarifying Hour 1 clock beyond Data in Brief (record description points readers to the paper).
