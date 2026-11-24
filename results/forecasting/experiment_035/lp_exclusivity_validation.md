| Formulation | Exclusivity | No-export | Cyclic SOC | Label |
|-------------|-------------|-------------|------------|-------|
| Exp033 `linprog` | Not guaranteed (`p_ch+p_dis≤P`) | Violated then clipped | Yes | **relaxed LP benchmark** |
| Big-M continuous (034) | Not guaranteed | Same as relaxed LP | Yes | **relaxed** |
| SciPy `milp` + binary z (035) | **Guaranteed** | **Enforced** | Yes | **MILP exclusive benchmark** |

Medoid MILP peaks match Exp033 relaxed LP peaks when curtail was zero; differ where Exp033 relied on clipping (e.g. cluster1_higher).
