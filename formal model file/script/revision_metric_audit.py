"""Recompute screening diagnostics from all saved hourly runs; preserve canonical data."""
import argparse
import re
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from revision_common import ROOT, OUT, TARGETS, dataset, data_path, sha, write_json

def objects(text):
    clean = re.sub(r'!.*', '', text)
    return [[v.strip() for v in block.split(',')] for block in clean.split(';') if block.strip()]

def occupancy_proof(text):
    obs = objects(text)
    by_type = {}
    for o in obs:
        by_type.setdefault(o[0].lower(), []).append(o)
    people = by_type['people']
    assert len(people) == 2 and all(float(p[5]) > 0 for p in people)
    schedules = {p[3] for p in people}
    years = [o for o in by_type['schedule:year'] if o[1] in schedules]
    assert len(years) == len(schedules)
    weeks = {y[i] for y in years for i in range(3, len(y), 5)}
    week_objects = [o for o in by_type['schedule:week:daily'] if o[1] in weeks]
    assert len(week_objects) == len(weeks)
    day_names = {name for o in week_objects for name in o[2:]}
    days = [o for o in by_type['schedule:day:interval'] if o[1] in day_names]
    assert len(days) == len(day_names)
    minimum = min(float(o[i]) for o in days for i in range(5, len(o), 2))
    assert minimum > 0, 'Zero occupancy requires evaluating the actual hourly schedule.'
    timestamp = by_type['outputcontrol:timestamp'][0]
    assert timestamp[1:] == ['Yes', 'Yes'], 'Expected ISO beginning-of-interval timestamps.'
    return minimum

def calculate(raw, width, length):
    ts = pd.DatetimeIndex(pd.to_datetime(raw['Date/Time'].str.strip()))
    expected = pd.date_range('2025-01-01', periods=8760, freq='h')
    assert ts.equals(expected), 'Missing/duplicate/shifted annual hourly timestamps'
    def col(*parts):
        found = [c for c in raw if all(p.lower() in c.lower() for p in parts)]
        assert len(found) == 1, (parts, found)
        arr = raw[found[0]].to_numpy(float)
        assert np.isfinite(arr).all()
        return arr
    outdoor = col('outdoor', 'drybulb')
    daily = outdoor.reshape(365, 24).mean(axis=1)
    trm = np.empty(365)
    trm[0] = daily[0]
    for i in range(1, 365):
        trm[i] = 0.2 * daily[i-1] + 0.8 * trm[i-1]
    tmax = np.repeat(0.33 * trm + 21.8, 24)
    summer = (ts.month >= 5) & (ts.month <= 9)
    night = (ts.hour >= 22) | (ts.hour < 7)
    r = {'summer_hours': int(summer.sum()), 'annual_night_hours': int(night.sum()),
         'summer_night_hours': int((summer & night).sum())}
    flags = []
    peak = []
    for z in ['101', '102']:
        op = col(z, 'operative temperature')
        delta = op - tmax
        d = delta[summer]
        he = 100 * np.mean(d >= 1)
        weights = np.rint(np.maximum(d, 0))
        we = float(weights.reshape(-1, 24).sum(axis=1).max())
        halfup = np.floor(np.maximum(d, 0) + .5).reshape(-1, 24).sum(axis=1).max()
        c3 = int(np.sum(d > 4))
        fail = int(he > 3) + int(we > 6) + int(c3 > 0)
        flags.append(fail >= 2)
        peak.append(op[summer].max())
        r.update({f'He_all_{z}': he, f'He_occupied_{z}': he,
                  f'He_offset_{z}': 0.0, f'We_{z}': we, f'We_halfup_{z}': float(halfup),
                  f'C3_hours_{z}': c3, f'two_of_three_proxy_{z}': fail >= 2})
        if z == '102':
            r['hours_gt26_night'] = int(np.sum((op > 26) & summer & night))
            r['hours_gt26_night_annual'] = int(np.sum((op > 26) & night))
            r['night_outside_summer'] = r['hours_gt26_night_annual'] - r['hours_gt26_night']
    r.update(He_worst=round(max(r['He_all_101'], r['He_all_102']), 4),
             We_max_worst=max(r['We_101'], r['We_102']), T_op_peak=round(max(peak), 3),
             hours_C3_worst=max(r['C3_hours_101'], r['C3_hours_102']),
             two_of_three_proxy_dwelling=any(flags))
    heat = sum(col(z, 'ideal loads supply air total heating energy').sum() for z in ['101', '102'])
    r['heat_kWh_m2'] = round(heat / 3600000 / (2 * width * length), 4)
    r['cooling_kWh'] = sum(col(z, 'ideal loads supply air total cooling energy').sum() for z in ['101', '102']) / 3600000
    return r

def audit_run(arg):
    arch, row = arg
    folder = ROOT / 'output/runs' / arch / row['run_id']
    try:
        minimum = occupancy_proof((folder / 'sim.idf').read_text())
        raw = pd.read_csv(folder / 'eplusout.csv', usecols=lambda c: c == 'Date/Time' or
                          'Operative Temperature' in c or 'Outdoor Air Drybulb' in c or
                          'Ideal Loads Supply Air Total' in c)
        r = calculate(raw, row['width'], row['length'])
        for t in TARGETS + ['hours_C3_worst']:
            r[f'canonical_difference_{t}'] = r[t] - row[t]
        return dict(archetype=arch, run_id=row['run_id'], status='ok', occupancy_minimum=minimum, **r)
    except Exception as exc:
        return dict(archetype=arch, run_id=row['run_id'], status='error', error=repr(exc))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    dest = OUT / 'audit'
    dest.mkdir(parents=True, exist_ok=True)
    jobs = [(a, r) for a in ['detached', 'semi'] for r in dataset(a).to_dict('records')]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, r in enumerate(pool.map(audit_run, jobs, chunksize=10), 1):
            rows.append(r)
            if i % 200 == 0:
                print(f'Audited {i}/{len(jobs)}', flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(dest / 'hourly_audit.csv', index=False)
    assert d.status.eq('ok').all(), 'Inspect audit errors before training.'
    diffs = [c for c in d if c.startswith('canonical_difference_')]
    assert d[diffs].abs().max().max() < 1e-6, 'Canonical target mismatch: do not train yet.'
    summaries = []
    for a, g in d.groupby('archetype'):
        summaries.append(dict(archetype=a, n=len(g), C1_gt3=int((g.He_worst > 3).sum()),
            C2_gt6=int((g.We_max_worst > 6).sum()), C2_ge6=int((g.We_max_worst >= 6).sum()),
            C2_gt6_pct=100*(g.We_max_worst > 6).mean(), C2_ge6_pct=100*(g.We_max_worst >= 6).mean(),
            C3_nonzero=int((g.hours_C3_worst > 0).sum()),
            two_of_three_proxy=int(g.two_of_three_proxy_dwelling.sum()),
            occupied_offset_max=g[['He_offset_101', 'He_offset_102']].abs().max().max(),
            night_zero_pct=100*g.hours_gt26_night.eq(0).mean(), night_mean=g.hours_gt26_night.mean(),
            night_median=g.hours_gt26_night.median(), night_max=g.hours_gt26_night.max(),
            night_gt32=int((g.hours_gt26_night > 32).sum()),
            night_annual_changed=int(g.night_outside_summer.ne(0).sum()),
            night_annual_gt32=int((g.hours_gt26_night_annual > 32).sum()),
            rounding_changed=int(((g.We_101 != g.We_halfup_101) | (g.We_102 != g.We_halfup_102)).sum()),
            cooling_kWh_max=g.cooling_kWh.max()))
    pd.DataFrame(summaries).to_csv(dest / 'metric_summary.csv', index=False)
    d[d.hours_C3_worst > 0].to_csv(dest / 'c3_active_cases.csv', index=False)
    epw = next((ROOT / 'weather file').glob('*2009-2023.epw'))
    weather = pd.read_csv(epw, skiprows=8, header=None)
    write_json(dest / 'manifest.json', {'source_root': str(ROOT), 'rows_audited': len(d),
        'data_sha256': {a: sha(data_path(a)) for a in ['detached', 'semi']},
        'weather_sha256': sha(epw), 'weather_max_C': float(weather[6].max()),
        'weather_summer_max_C': float(weather.loc[weather[1].between(5, 9), 6].max()),
        'audit_script_sha256': sha(__file__), 'occupancy_definition': 'schedule fraction > 0',
        'compliance_claim': False})
    print(pd.DataFrame(summaries).to_string(index=False), flush=True)

if __name__ == '__main__':
    main()
