"""Read-only hourly audit of raw versus rounded C1/C3 screening proxies."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / '07_corrected_full/2026-10-04_combined_v2'
sys.path.insert(0, str(SOURCE / 'frozen_code'))
import revision_metric_audit as original_audit

WEATHERS = ['TMYx', 'DSY1']
ARCHETYPES = ['detached', 'semi']
MODES = ['raw', 'rounded', 'halfup']
SOURCE_URL = ('https://assets.publishing.service.gov.uk/media/5d91ca2ded915d556d8e7b64/'
              'Research_into_overheating_in_new_homes_-_phase_1.pdf')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def round_halfup(delta):
    # Half away from zero; only positive thresholds affect this audit.
    return np.copysign(np.floor(np.abs(delta) + 0.5), delta)


def evaluate_zone(delta):
    """One occupied summer, complete 24-hour days. Keep C2 fixed in every mode."""
    delta = np.asarray(delta, dtype=float)
    require(delta.ndim == 1 and len(delta) > 0 and len(delta) % 24 == 0,
            'Expected complete summer days')
    require(np.isfinite(delta).all(), 'Non-finite temperature difference')
    rounded = np.rint(delta)
    halfup = round_halfup(delta)
    weights = np.rint(np.maximum(delta, 0))
    we = float(weights.reshape(-1, 24).sum(axis=1).max())
    result = {'occupied_summer_hours': len(delta), 'We_fixed': we, 'C2_flag': we > 6}
    for mode, values in [('raw', delta), ('rounded', rounded), ('halfup', halfup)]:
        hours = int(np.count_nonzero(values >= 1))
        he = 100 * hours / len(delta)
        c3 = int(np.count_nonzero(values > 4))
        c1_flag = hours * 100 > 3 * len(delta)
        joint = int(c1_flag) + int(we > 6) + int(c3 > 0) >= 2
        result.update({f'C1_hours_{mode}': hours, f'He_{mode}_pct': he,
                       f'C1_flag_{mode}': c1_flag, f'C3_hours_{mode}': c3,
                       f'C3_flag_{mode}': c3 > 0, f'joint_{mode}': joint})
    # Independent interval-count checks, without using the rounding operations.
    require(result['C1_hours_rounded'] == int(np.count_nonzero(delta > 0.5)), 'C1 rint boundary')
    require(result['C3_hours_rounded'] == int(np.count_nonzero(delta > 4.5)), 'C3 rint boundary')
    require(result['C1_hours_halfup'] == int(np.count_nonzero(delta >= 0.5)), 'C1 half-up boundary')
    require(result['C3_hours_halfup'] == int(np.count_nonzero(delta >= 4.5)), 'C3 half-up boundary')
    require(result['C1_hours_rounded'] >= result['C1_hours_raw'], 'C1 monotonicity')
    require(result['C3_hours_rounded'] <= result['C3_hours_raw'], 'C3 monotonicity')
    result['He_change_pp'] = result['He_rounded_pct'] - result['He_raw_pct']
    result['C3_change_hours'] = result['C3_hours_rounded'] - result['C3_hours_raw']
    result['ties_at_0_5'] = int(np.count_nonzero(delta == 0.5))
    result['ties_at_4_5'] = int(np.count_nonzero(delta == 4.5))
    result['positive_half_integer_hours'] = int(np.count_nonzero((delta > 0) & ((delta % 1) == 0.5)))
    result['C2_halfup_minus_fixed'] = float(round_halfup(np.maximum(delta, 0)).reshape(-1, 24).sum(axis=1).max() - we)
    return result


def combine_zones(zones):
    require(len(zones) == 2, 'Expected two habitable zones')
    result = {'We_fixed': max(z['We_fixed'] for z in zones),
              'C2_flag': any(z['C2_flag'] for z in zones)}
    for mode in MODES:
        result.update({
            f'He_{mode}_pct': max(z[f'He_{mode}_pct'] for z in zones),
            f'C1_hours_worst_{mode}': max(z[f'C1_hours_{mode}'] for z in zones),
            f'C1_flag_{mode}': any(z[f'C1_flag_{mode}'] for z in zones),
            f'C3_hours_{mode}': max(z[f'C3_hours_{mode}'] for z in zones),
            f'C3_flag_{mode}': any(z[f'C3_flag_{mode}'] for z in zones),
            # Never combine the worst C1, C2 and C3 from different zones.
            f'joint_{mode}': any(z[f'joint_{mode}'] for z in zones),
        })
    result['He_change_pp'] = result['He_rounded_pct'] - result['He_raw_pct']
    result['C3_change_hours'] = result['C3_hours_rounded'] - result['C3_hours_raw']
    result['any_flag_changed'] = any(result[f'{x}_raw'] != result[f'{x}_rounded']
                                     for x in ['C1_flag', 'C3_flag', 'joint'])
    result['rounding_tie_sensitive'] = any(result[f'{x}_rounded'] != result[f'{x}_halfup']
                                          for x in ['He', 'C3_hours', 'joint'] if x != 'He') or result['He_rounded_pct'] != result['He_halfup_pct']
    return result


def read_case(row):
    key = {k: row[k] for k in ['weather', 'archetype', 'run_id']}
    folder = SOURCE / 'datasets' / row['weather'] / 'runs' / row['archetype'] / row['run_id']
    payload = (folder / 'eplusout.csv').read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    require(digest == row['csv_sha256'], f'Hourly hash mismatch: {key}')
    idf = (folder / 'sim.idf').read_bytes()
    require(hashlib.sha256(idf).hexdigest() == row['idf_sha256'], f'IDF hash mismatch: {key}')
    minimum = original_audit.occupancy_proof(idf.decode())
    raw = pd.read_csv(io.BytesIO(payload), usecols=lambda c: c == 'Date/Time' or
                     'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or
                     'Ideal Loads Supply Air Total' in c)
    baseline = original_audit.calculate(raw, row['width'], row['length'])
    for name, value in baseline.items():
        require(abs(float(row[name]) - float(value)) < 1e-9, f'Canonical mismatch: {key} {name}')
    timestamp = pd.DatetimeIndex(pd.to_datetime(raw['Date/Time'].str.strip()))
    summer = (timestamp.month >= 5) & (timestamp.month <= 9)
    require(len(raw) == 8760 and summer.sum() == 3672, f'Incomplete year: {key}')
    outdoor_col = next(c for c in raw if 'Outdoor Air Drybulb' in c)
    daily = raw[outdoor_col].to_numpy().reshape(365, 24).mean(axis=1)
    running_mean = np.empty(365)
    running_mean[0] = daily[0]
    for day in range(1, 365):
        running_mean[day] = 0.8 * running_mean[day-1] + 0.2 * daily[day-1]
    threshold = np.repeat(0.33 * running_mean + 21.8, 24)
    zone_rows = []
    for zone in ['101', '102']:
        col = next(c for c in raw if f'SPACE {zone}:' in c and 'Operative Temperature' in c)
        zone_result = evaluate_zone((raw[col].to_numpy() - threshold)[summer])
        for name, actual in [('He_all', zone_result['He_raw_pct']), ('We', zone_result['We_fixed']),
                             ('C3_hours', zone_result['C3_hours_raw']),
                             ('two_of_three_proxy', zone_result['joint_raw'])]:
            require(abs(actual - float(row[f'{name}_{zone}'])) < 1e-9, f'Independent raw mismatch: {key} {zone} {name}')
        zone_rows.append(dict(key, zone=zone, **zone_result))
    case = dict(key, **combine_zones(zone_rows), occupancy_minimum=minimum,
                source_csv_sha256=digest, source_idf_sha256=row['idf_sha256'],
                source_hourly=str((folder / 'eplusout.csv').relative_to(SOURCE)))
    for name in ['T_op_peak', 'hours_gt26_night', 'hours_gt26_night_annual', 'heat_kWh_m2']:
        case[f'{name}_unchanged'] = baseline[name]
    require(abs(round(case['He_raw_pct'], 4) - row['He_worst']) < 1e-9, f'Worst C1 mismatch: {key}')
    require(case['C3_hours_raw'] == row['hours_C3_worst'], f'Worst C3 mismatch: {key}')
    require(case['joint_raw'] == row['two_of_three_proxy_dwelling'], f'Joint mismatch: {key}')
    return case, zone_rows


def verify_frozen(expected):
    for name, digest in expected.items():
        require(sha(SOURCE / name) == digest, f'Protected file changed: {name}')


def summarize(cases, zones):
    summaries, transitions = [], []
    for (weather, arch), g in cases.groupby(['weather', 'archetype'], sort=False):
        z = zones[(zones.weather == weather) & (zones.archetype == arch)]
        item = dict(weather=weather, archetype=arch, n=len(g))
        for mode in MODES:
            item.update({f'He_{mode}_mean_pct': g[f'He_{mode}_pct'].mean(),
                         f'He_{mode}_median_pct': g[f'He_{mode}_pct'].median(),
                         f'He_{mode}_max_pct': g[f'He_{mode}_pct'].max(),
                         f'C1_{mode}_count': int(g[f'C1_flag_{mode}'].sum()),
                         f'C3_{mode}_count': int(g[f'C3_flag_{mode}'].sum()),
                         f'joint_{mode}_count': int(g[f'joint_{mode}'].sum()),
                         f'C3_{mode}_mean_hours': g[f'C3_hours_{mode}'].mean()})
        item.update(He_changed_cases=int((g.He_change_pp > 0).sum()),
                    He_change_mean_pp=g.He_change_pp.mean(), He_change_median_pp=g.He_change_pp.median(),
                    He_change_p95_pp=g.He_change_pp.quantile(.95), He_change_max_pp=g.He_change_pp.max(),
                    C2_fixed_count=int(g.C2_flag.sum()), any_flag_changed=int(g.any_flag_changed.sum()),
                    tie_sensitive_cases=int(g.rounding_tie_sensitive.sum()),
                    exact_half_integer_zone_hours=int(z.positive_half_integer_hours.sum()),
                    C2_halfup_changed_zones=int((z.C2_halfup_minus_fixed != 0).sum()))
        summaries.append(item)
        for metric, label in [('C1_flag', 'C1_gt3'), ('C3_flag', 'C3_nonzero'), ('joint', 'same_zone_two_of_three')]:
            a, b = g[f'{metric}_raw'], g[f'{metric}_rounded']
            transitions.append(dict(weather=weather, archetype=arch, metric=label, n=len(g),
                false_to_false=int((~a & ~b).sum()), false_to_true=int((~a & b).sum()),
                true_to_false=int((a & ~b).sum()), true_to_true=int((a & b).sum()), changed=int((a != b).sum())))
    paired = []
    for arch in ARCHETYPES:
        a = cases[(cases.weather == 'TMYx') & (cases.archetype == arch)].set_index('run_id').sort_index()
        b = cases[(cases.weather == 'DSY1') & (cases.archetype == arch)].set_index('run_id').sort_index()
        require(a.index.equals(b.index), 'Unpaired weather samples')
        for metric in ['He_raw_pct', 'He_rounded_pct', 'C3_hours_raw', 'C3_hours_rounded',
                       'T_op_peak_unchanged', 'hours_gt26_night_unchanged']:
            delta = b[metric] - a[metric]
            paired.append(dict(archetype=arch, metric=metric, n=len(a),
                               TMYx_mean=a[metric].mean(), DSY1_mean=b[metric].mean(),
                               mean_DSY1_minus_TMYx=delta.mean(), median_DSY1_minus_TMYx=delta.median(),
                               increased=int((delta > 1e-12).sum()), unchanged=int((delta.abs() <= 1e-12).sum()),
                               decreased=int((delta < -1e-12).sum())))
    return pd.DataFrame(summaries), pd.DataFrame(transitions), pd.DataFrame(paired)


def write_report(output, cases, zones, summary, transitions, paired, verification):
    cols = ['weather', 'archetype', 'n', 'He_raw_mean_pct', 'He_rounded_mean_pct',
            'He_change_mean_pp', 'He_change_median_pp', 'He_change_p95_pp', 'He_change_max_pp', 'He_changed_cases']
    flag_cols = ['weather', 'archetype', 'C1_raw_count', 'C1_rounded_count', 'C2_fixed_count',
                 'C3_raw_count', 'C3_rounded_count', 'joint_raw_count', 'joint_rounded_count']
    lines = [
        '# Raw versus rounded temperature-difference audit', '',
        'Source: corrected combined V2, 2026-10-04. This is post-processing only. No EnergyPlus runs, model training, manuscript edits or canonical-result replacements were performed.', '',
        '## Scope and definitions', '',
        f'- Cases: {len(cases):,}; occupied-zone series: {len(zones):,}; 8,760 hourly records per case.',
        '- Summer is May-September, with 3,672 hourly bins. Every checked occupied-zone schedule remains positive (minimum 0.3), so its occupied mask equals the summer mask. This is not a validation of realistic occupancy.',
        '- Delta T = operative temperature minus adaptive limit. The adaptive limit and outdoor running mean are identical to the frozen corrected V2 implementation.',
        '- Raw: C1 counts Delta T >= 1 K; C3 counts Delta T > 4 K.',
        '- Rounded: round Delta T to the nearest integer (NumPy rint, ties to even), then use >=1 and >4. This is equivalent to raw Delta T >0.5 K for C1 and >4.5 K for C3, including the specified tie behaviour.',
        '- A secondary half-away-from-zero calculation checks the unspecified half-integer convention. No tolerance snapping was applied to hourly differences.',
        '- C1 is a percentage of occupied summer hours; changes are percentage points (pp), not relative percent. Flag: C1 >3%, evaluated before display rounding.',
        '- C2 is deliberately held fixed: sum rint(max(Delta T,0)) over each summer day, take the maximum; flag is strictly >6. The half-up C2 calculation is a diagnostic only.',
        '- C3 flag means at least one qualifying summer hour. The joint flag requires two criteria in the SAME zone, then any qualifying habitable zone at dwelling level.',
        f'- Motivation: [UK government overheating research, printed pp. 7-8]({SOURCE_URL}) describes nearest-integer temperature differences. This audit isolates rounding; it does not establish full TM52/TM59 compliance.', '',
        '## C1 continuous-value sensitivity', '', summary[cols].to_markdown(index=False, floatfmt='.4f'), '',
        '## Threshold counts (each group has 2,000 cases)', '', summary[flag_cols].to_markdown(index=False), '',
        '## All flag transitions', '', transitions.to_markdown(index=False), '',
        '## Paired weather comparison', '', paired.to_markdown(index=False, floatfmt='.4f'), '',
        '## Half-integer check', '',
        summary[['weather', 'archetype', 'exact_half_integer_zone_hours', 'tie_sensitive_cases', 'C2_halfup_changed_zones']].to_markdown(index=False), '',
        '## Interpretation boundaries', '',
        '- Threshold claims about C1, C3 and same-zone joint flags must name the rounding convention. The raw counts remain the preserved original proxy results; the rounded counts are a separate sensitivity analysis.',
        '- Peak operative temperature, summer/annual night hours and heating demand do not involve this Delta T rounding. Their saved values were reproduced, not changed. C2 is unchanged by design.',
        '- Existing He surrogate accuracy and SHAP results apply only to the original raw He target. A changed C1 target would require separate retraining/evaluation; no rounded-target model performance is inferred here.',
        '- C3 remains diagnostic. Recomputing its counts and joint flags does not by itself require retraining the five existing target models.',
        '- Weather pairing holds building inputs fixed, but the two weather files differ in source/location/scenario. Differences are not isolated climate-change or heat-severity effects.', '',
        '## Verification', '',
        f'- {verification["raw_case_matches"]:,} cases reproduce all frozen audit metrics before the change.',
        f'- {verification["zone_boundary_checks"]:,} occupied-zone series pass independent interval-count checks and monotonicity checks.',
        f'- All {verification["frozen_files_verified"]:,} frozen input/result/model/figure files match their pre-existing hashes, before and after this audit.',
        f'- All {verification["hourly_files_verified"]:,} hourly CSVs and their run IDFs match recorded hashes on input and a separate final preservation pass.',
        '- No existing result, model, IDF, weather, manuscript or figure was written.', '',
        '## Outputs', '',
        '- `case_comparison.csv`: all 8,000 dwellings/weather cases, continuous metrics and flags for each convention.',
        '- `zone_comparison.csv`: all 16,000 occupied-zone series; reconstructs same-zone logic.',
        '- `group_summary.csv`: four weather/archetype groups and C1 distributions.',
        '- `flag_transitions.csv`: full false/true transitions, including both directions.',
        '- `paired_weather_comparison.csv`: paired DSY1 minus TMYx values under each convention.',
        '- `changed_flag_cases.csv`: IDs and values for cases with any C1/C3/joint flip.',
        '- `verification.json`: scope, preservation checks, software versions and completion status.', '',
    ]
    (output / 'REPORT.md').write_text('\n'.join(lines))


def verify_hourly(case):
    csv = SOURCE / case['source_hourly']
    require(sha(csv) == case['source_csv_sha256'], f'Hourly changed: {csv}')
    require(sha(csv.parent / 'sim.idf') == case['source_idf_sha256'], f'Run IDF changed: {csv.parent}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--output', type=Path, default=HERE / 'results')
    args = parser.parse_args()
    require(1 <= args.workers <= 12, 'Use 1..12 workers')
    output = args.output.resolve()
    require(not output.is_relative_to(SOURCE.resolve()), 'Cannot write inside corrected V2')
    require(not output.exists(), f'Refusing to overwrite existing audit: {output}')
    output.mkdir(parents=True)
    start = time.perf_counter()
    frozen = json.loads((SOURCE / 'artifact_hashes.json').read_text())
    protocol = json.loads((SOURCE / 'protocol.json').read_text())
    frozen.update(protocol['input_hashes'])
    for name in ['artifact_hashes.json', 'protocol.json', 'complete.json']:
        frozen[name] = sha(SOURCE / name)
    print(f'Verifying {len(frozen)} frozen files before audit', flush=True)
    verify_frozen(frozen)
    save_json(output / 'source_hashes.json', frozen)
    jobs = []
    for weather in WEATHERS:
        data = pd.read_csv(SOURCE / 'datasets' / weather / 'results.csv')
        require(len(data) == 4000 and data.status.eq('ok').all(), 'Incomplete source dataset')
        require(not data.duplicated(['archetype', 'run_id']).any(), 'Duplicate cases')
        require(set(data.weather) == {weather} and set(data.archetype) == set(ARCHETYPES), 'Wrong source groups')
        require(data.groupby('archetype').size().eq(2000).all(), 'Wrong group sizes')
        jobs.extend(data.to_dict('records'))
    save_json(output / 'protocol.json', dict(
        source_root=str(SOURCE), output_root=str(output), script_sha256=sha(__file__),
        created_utc=datetime.now(timezone.utc).isoformat(), total_cases=len(jobs),
        rounded_mode='nearest integer; ties to even', secondary_mode='nearest integer; half away from zero',
        C2='held fixed at original stepped definition', C1_flag='He >3 percent, no display rounding',
        C3_flag='one or more qualifying summer hours', joint='at least two criteria in the same occupied zone',
        external_definition_source=SOURCE_URL, new_simulations=0, retrained_models=0))
    cases, zones = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(read_case, row) for row in jobs]
        for future in as_completed(futures):
            case, zone_rows = future.result()
            cases.append(case)
            zones.extend(zone_rows)
            if len(cases) % 200 == 0:
                print(f'POSTPROCESS {len(cases)}/8000 ({time.perf_counter()-start:.1f}s)', flush=True)
    cases = pd.DataFrame(cases).sort_values(['weather', 'archetype', 'run_id']).reset_index(drop=True)
    zones = pd.DataFrame(zones).sort_values(['weather', 'archetype', 'run_id', 'zone']).reset_index(drop=True)
    require(len(cases) == 8000 and len(zones) == 16000, 'Incomplete audit')
    summary, transitions, paired = summarize(cases, zones)
    print(summary[['weather','archetype','C1_raw_count','C1_rounded_count','C3_raw_count','C3_rounded_count','joint_raw_count','joint_rounded_count']].to_string(index=False), flush=True)
    print('Independent final input-preservation hash pass', flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, _ in enumerate(pool.map(verify_hourly, cases.to_dict('records')), 1):
            if i % 1000 == 0:
                print(f'PRESERVATION {i}/8000', flush=True)
    verify_frozen(frozen)
    verification = dict(status='complete', cases=8000, zone_series=16000, raw_case_matches=8000,
                        zone_boundary_checks=16000, frozen_files_verified=len(frozen),
                        hourly_files_verified=8000, run_idfs_verified=8000,
                        source_results_preserved=True, new_simulations=0, retrained_models=0,
                        script_sha256=sha(__file__), python=sys.version, numpy=np.__version__, pandas=pd.__version__,
                        finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-start)
    for name, frame in [('case_comparison', cases), ('zone_comparison', zones),
                        ('group_summary', summary), ('flag_transitions', transitions),
                        ('paired_weather_comparison', paired),
                        ('changed_flag_cases', cases[cases.any_flag_changed])]:
        frame.to_csv(output / f'{name}.csv', index=False)
    write_report(output, cases, zones, summary, transitions, paired, verification)
    save_json(output / 'verification.json', verification)
    save_json(output / 'output_hashes.json', {p.name: sha(p) for p in output.iterdir() if p.is_file()})
    print(json.dumps(verification, indent=2), flush=True)


if __name__ == '__main__':
    main()
