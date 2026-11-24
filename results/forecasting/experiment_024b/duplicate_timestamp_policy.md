# Duplicate timestamp policy

| Case | Detection | Action | Executable now |
|------|-----------|--------|----------------|
| Exact duplicate | Same `timestamp`, same `cons`, same compared aux | Drop to one row, log | Yes |
| Conflicting `cons` | Same `timestamp`, different `cons` | Exclude timestamp entirely | Yes |
| Conflicting aux only | Same `cons`, different undocumented `flag` | Exclude until semantics | Partial (GoiEner) |
| DST fall-back repeat | Repeated civil time | BLOCKED — needs IANA tz | No |
| Export error dup | Same as exact/conflict per above | Per rules | Yes |

**Rejected:** keep-first on conflicts (024A superseded).
