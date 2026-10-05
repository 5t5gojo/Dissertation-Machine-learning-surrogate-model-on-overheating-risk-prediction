# Metric audit for the non-DSY revision

The source is `/Users/hlbao/Projects/dissertation/formal model file`, not the OneDrive workspace. All 4,000 saved `sim.idf` and `eplusout.csv` pairs were checked. The canonical simulation tables and five training targets were preserved. Detailed records are in `output/reviewer_revision/audit/`.

## Scope and definitions

This is an audit of implemented screening proxies informed by TM52 (2013) and TM59 (2017). It is not a TM52/TM59 compliance calculation. TM59 (2026) introduces different criteria; the revision does not silently switch editions.

| Quantity | Implemented definition | Audit and action |
|---|---|---|
| Adaptive limit | Tmax = 0.33 Trm + 21.8 C; alpha = 0.8 running mean, initialized from first daily outdoor mean | Recomputed from hourly output; preserve this explicit definition |
| C1 proxy | 100 times number of summer hours with raw delta T >= 1 K divided by summer hours | Explicitly establish occupied mask from actual IDF schedules |
| C2 proxy | Daily sum of rint(max(delta T,0)) times hourly duration; worst day and zone | Correct reference comparison to >6, not >=6; remain a stepped proxy |
| Peak temperature | Maximum May-September operative temperature over zones 101/102 | Full summer hours, not daytime-only; no compliance pass/fail |
| Bedroom night target | May-September 22:00-07:00, zone 102 operative temperature >26 C | Keep summer scope explicit and add annual diagnostic |
| Heating target | Annual Ideal Loads Supply Air Total Heating Energy / (3.6e6 * 2WL) | Demand intensity, not metered energy; reproduced exactly |
| C3 diagnostic | Summer hours with raw delta T >4 K | Audit within each zone; do not combine different-zone maxima into overall flags |

## Occupied hours

Both People objects use NECB-G-Occupancy. The audit follows the referenced Schedule:Year -> Schedule:Week:Daily -> Schedule:Day:Interval objects in every generated IDF. All referenced daily schedule fractions are positive, with minimum 0.3, and both design headcounts are positive. Occupied means scheduled people >0, not full occupancy and not an arbitrary 0.5 schedule cut-off.

Under this definition every summer hourly interval is occupied: 3,672 hours per zone. The occupied-hours and all-hours C1 values coincide for all 4,000 cases; the maximum offset is 0.0000 percentage points. The reviewer's proposed denominator dilution is therefore not present under the implemented schedules. This does not establish realistic occupancy or conformity with TM59 room-specific occupancy profiles. Replacing the schedules would also change internal gains and require re-simulation, not just selecting a new denominator.

## Time indexing

Every run has 8,760 consecutive ISO timestamps from 2025-01-01 00:00 to 2025-12-31 23:00. OutputControl:Timestamp explicitly specifies beginning-of-interval timestamps. The correct night mask is hour >=22 OR hour <7: nine intervals per night, 1,377 summer night hours and 3,285 annual night hours. The original row-based mask matches these timestamps in this dataset. No daylight saving adjustment is applied in the IDF.

## Reference comparisons

| Archetype | C2 >6 | C2 >=6 (old displayed rate) | C3 nonzero | Same-zone two-of-three proxy |
|---|---:|---:|---:|---:|
| Detached | 1,343 / 2,000 = 67.15% | 1,456 / 2,000 = 72.80% | 2 | 2 |
| Semi-detached | 942 / 2,000 = 47.10% | 1,058 / 2,000 = 52.90% | 0 | 0 |

Zero cases exceed the C1 reference of 3%. Nevertheless, `detached/run_0768` and `detached/run_1281` both have zone-102 C2 =31 and C3 =2 h / 1 h respectively. It is incorrect to say that no dwelling triggers two of the three proxy criteria. Report these as proxy flags, not formal TM52 failures. No comparison should combine C2 from one zone with C3 from another.

The original `np.rint` uses ties-to-even. Recomputing C2 using positive half-up rounding changes no zone-level daily maximum in this dataset. This numerical check is not proof of full equivalence to the formal occupied-hour method.

## Summer versus annual bedroom hours

| Archetype | Summer mean | Annual mean | Summer maximum | Annual maximum | Summer >32 h | Annual >32 h | Cases changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| Detached | 0.9335 | 1.5820 | 45 | 164 | 3 | 15 | 99 |
| Semi-detached | 1.1750 | 1.8660 | 29 | 194 | 0 | 16 | 93 |

Both summer medians are zero and both summer zero fractions are 56.6%. The annual comparison is a new diagnostic, not a retrained annual-night surrogate and not compliance assessment. Do not claim semi-detached night-time exceedance did not increase: its mean is higher for both periods. Summer counts cannot be used as a substitute for annual TM59:2017 reference comparisons.

## Other verified assumptions and boundaries

- The EPW dry-bulb maximum is 31.0 C, not 30.8 C.
- All audited Ideal Loads cooling energy values are zero.
- Fixed overhang depth means non-operating shading, but its projection is sampled from 0 to 1 m.
- Natural ventilation has no occupancy/security schedule, a 24 C minimum indoor temperature, 10 C minimum outdoor temperature and 10 m/s maximum wind speed. Its delta-temperature setting is -100 K: it does not explicitly require outside air to be cooler than inside. Describe a temperature-controlled opening assumption, not guaranteed night-purge cooling.
- The occupancy schedule comes from the NECB-named template; SAP supplies headcounts only. Do not describe these as validated UK/TM59 room-specific operation profiles.
- Heating remains available during summer; the absence of active cooling does not establish that heating is disabled for the entire summer. Use 'without active cooling' rather than an unqualified free-running claim.
- No occupied-dwelling measurements or independent building-model benchmark validation has been added.

## Sources for interpretation

- CIBSE TM52 publication: https://www.cibse.org/knowledge-research/knowledge-portal/tm52-the-limits-of-thermal-comfort-avoiding-overheating-in-european-buildings/
- CIBSE TM59 (2017) publication: https://cibse.org/knowledge-research/knowledge-portal/technical-memorandum-59-design-methodology-for-the-assessment-of-overheating-risk-in-homes/
- DesignBuilder official implementation guide, edition comparison including annual 2017 night assessment: https://designbuilder.co.uk/helpv2025.1/Content/CIBSETM59.htm

Full formal-standard conformance is not claimed from publicly accessible summaries. Data definitions and audit evidence above come directly from this repository.
