# CEEW Mathura–Bareilly dataset audit

Source: Agrawal, S., Mani, S., Ganesan, K., and Jain, A., *High frequency smart meter data from two districts in India (Mathura and Bareilly)*, Harvard Dataverse, DOI `10.7910/DVN/GOCHJH`, version 2. The untouched original files are in `data/raw/ceew_mathura_bareilly/`; the machine-readable audit is `results/ceew/dataset_audit.json`.

The audit reads 21,845,497 observations from six high-frequency source files: 13,946,703 Bareilly rows and 7,898,794 Mathura rows. It finds 84 meter IDs (not 93 active IDs in these files). Bareilly spans 2019-05-09 through 2021-10-31; Mathura spans 2019-05-01 through 2021-02-20. The source README documents three-minute measurements.

Raw columns are `x_Timestamp`, `t_kWh`, `z_Avg Voltage (Volt)`, `z_Avg Current (Amp)`, `y_Freq (Hz)`, and `meter`. There are no explicit consumer-category, feeder/substation, or weather fields. The documentation describes urban household smart meters, so the current study must not infer agriculture from clusters.

## Energy treatment

The README calls `t_kWh` electricity consumption recorded at each three-minute interval. It is therefore treated as **interval energy**, not renamed to power. The canonical loader retains `interval_energy_kwh` and derives a separate `load_kw = interval_energy_kwh / 0.05`. Empirically, median derived load is 0.220 kW and median voltage × current is 0.246 kW, a consistent magnitude check (allowing for power factor and measurement definitions).

For a complete 15-minute bin, interval energy is the sum of the five three-minute records; average power is that sum divided by 0.25 h. Arithmetic mean of `t_kWh` is not the 15-minute energy and must not be used as the target without the corresponding conversion.

The detailed per-meter coverage, duplicates, gaps, and maximum gaps are in `results/ceew/per_meter_coverage.csv`. Zero readings are common and must not automatically be treated as missing; the JSON audit reports them separately from nulls and negatives.
