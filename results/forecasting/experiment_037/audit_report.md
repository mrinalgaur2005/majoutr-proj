{
  "validation": {
    "tests": [
      {
        "test": "tariff_partition_flat",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_positive_flat",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_partition_low_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_positive_low_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_partition_moderate_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_positive_moderate_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_partition_high_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tariff_positive_high_spread",
        "pass": true,
        "detail": ""
      },
      {
        "test": "period_energy_sum",
        "pass": true,
        "detail": ""
      },
      {
        "test": "milp_not_worse_than_no_bess",
        "pass": true,
        "detail": "no_bess_optimal"
      },
      {
        "test": "milp_curtail_zero",
        "pass": true,
        "detail": ""
      },
      {
        "test": "milp_grid_balance",
        "pass": true,
        "detail": ""
      },
      {
        "test": "milp_exclusivity",
        "pass": true,
        "detail": ""
      },
      {
        "test": "cost_match",
        "pass": true,
        "detail": ""
      },
      {
        "test": "rule_no_simul",
        "pass": true,
        "detail": ""
      },
      {
        "test": "tod_exposure_inequality",
        "pass": true,
        "detail": "peak reduction does not imply extra savings without demand charge"
      },
      {
        "test": "exp035_physics_suite",
        "pass": true,
        "detail": "{'milp_no_curtail_balance': True, 'milp_exclusivity': True}"
      }
    ],
    "all_pass": true,
    "exp035_physics": {
      "n_tests": 11,
      "n_pass": 11,
      "tests": [
        {
          "test": "zero_capacity",
          "pass": true,
          "detail": ""
        },
        {
          "test": "zero_power",
          "pass": true,
          "detail": ""
        },
        {
          "test": "unclipped_energy_identity",
          "pass": true,
          "detail": "0.0"
        },
        {
          "test": "clipped_grid_residual_exp033_lp",
          "pass": true,
          "detail": "curtail=1.8974kWh residual=1.8974"
        },
        {
          "test": "exp034_failure_reproduced",
          "pass": true,
          "detail": ""
        },
        {
          "test": "milp_no_curtail_balance",
          "pass": true,
          "detail": "1.5543122344752192e-15"
        },
        {
          "test": "milp_cyclic_soc",
          "pass": true,
          "detail": ""
        },
        {
          "test": "milp_exclusivity",
          "pass": true,
          "detail": ""
        },
        {
          "test": "rule_no_curtail_balance",
          "pass": true,
          "detail": ""
        },
        {
          "test": "offline_cyclic_isolated_peak_infeasible",
          "pass": true,
          "detail": "soc_final=0.3946"
        },
        {
          "test": "offline_cyclic_cluster0_medoid",
          "pass": true,
          "detail": ""
        }
      ]
    }
  },
  "n_bess_scenarios": 240
}
