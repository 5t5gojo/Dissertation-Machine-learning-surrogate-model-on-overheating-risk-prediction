"""Verify preserved sources and summarize paired pilot differences in original units."""
from collections import Counter
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_sensitivity import (EXPERIMENT, TARGETS, VARIANTS, atomic_json, digest,
                             require, verify_frozen)

UNITS = dict(zip(TARGETS + ['hours_C3_worst'],
                 ['percentage points', 'stepped proxy units', 'deg C', 'hours', 'kWh/m2/year', 'hours']))
LABELS = dict(zip(TARGETS, ['Seasonal exceedance (pp)', 'Stepped daily proxy',
                           'Peak temperature (deg C)', 'Bedroom night exceedance (h)',
                           'Ideal heating demand (kWh/m2/year)']))


def summarize(data, keys):
    records = []
    for group, g in data.groupby(keys):
        group = group if isinstance(group, tuple) else (group,)
        for target in TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']:
            delta = g[f'new_{target}'] - g[f'old_{target}']
            unit = UNITS.get(target, 'hours')
            index = delta.abs().idxmax()
            corr = g[[f'old_{target}', f'new_{target}']].corr(method='spearman').iloc[0, 1]
            records.append(dict(zip(keys, group), target=target, unit=unit, n=len(g),
                baseline_mean=g[f'old_{target}'].mean(), modified_mean=g[f'new_{target}'].mean(),
                mean_change=delta.mean(), median_change=delta.median(),
                mean_absolute_change=delta.abs().mean(), paired_rmse=np.sqrt(np.mean(delta**2)),
                p95_absolute_change=delta.abs().quantile(.95), max_absolute_change=delta.abs().max(),
                max_change_run_id=g.loc[index, 'run_id'],
                increased=int((delta > 1e-9).sum()), decreased=int((delta < -1e-9).sum()),
                unchanged=int((delta.abs() <= 1e-9).sum()), spearman_old_new=corr))
    return pd.DataFrame(records)


def flag_tables(paired):
    definitions = {'C1_gt3': ('He_worst', 3), 'C2_gt6': ('We_max_worst', 6),
                   'C3_nonzero': ('hours_C3_worst', 0),
                   'night_summer_gt32': ('hours_gt26_night', 32),
                   'night_annual_gt32': ('hours_gt26_night_annual', 32)}
    records = []
    keys = ['weather', 'archetype', 'variant', 'cohort']
    for key, g in paired.groupby(keys):
        for name, (target, threshold) in definitions.items():
            old, new = g[f'old_{target}'] > threshold, g[f'new_{target}'] > threshold
            records.append(dict(zip(keys, key), flag=name, n=len(g), old_count=int(old.sum()), new_count=int(new.sum()),
                                newly_exceeding=int((~old & new).sum()), no_longer_exceeding=int((old & ~new).sum())))
        old, new = g.old_two_of_three_proxy_dwelling.astype(bool), g.new_two_of_three_proxy_dwelling.astype(bool)
        records.append(dict(zip(keys, key), flag='same_zone_two_of_three_proxy', n=len(g), old_count=int(old.sum()), new_count=int(new.sum()),
                            newly_exceeding=int((~old & new).sum()), no_longer_exceeding=int((old & ~new).sum())))
    return pd.DataFrame(records)


def plots(paired):
    random = paired[paired.cohort.eq('random64') & paired.variant.eq('combined')]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 5, figsize=(19, 8))
    for row, weather in enumerate(['TMYx', 'DSY1']):
        for col, target in enumerate(TARGETS):
            ax = axes[row, col]
            g = random[random.weather.eq(weather)]
            lo = min(g[f'old_{target}'].min(), g[f'new_{target}'].min())
            hi = max(g[f'old_{target}'].max(), g[f'new_{target}'].max())
            ax.plot([lo, hi], [lo, hi], '--', color='#71717a', linewidth=1)
            for arch, color in [('detached', '#b34b26'), ('semi', '#147879')]:
                a = g[g.archetype.eq(arch)]
                ax.scatter(a[f'old_{target}'], a[f'new_{target}'], c=color, label=arch, s=16, alpha=.7)
            ax.set_title(LABELS[target])
            ax.set_xlabel('Original')
            ax.set_ylabel(f'{weather}: combined correction')
            if col == 0:
                ax.legend(frameon=False)
    fig.suptitle('Matched sensitivity pilot: 64 random building vectors per archetype\nCombined = ventilation bearings + intermediate floor + semi attic party wall; interior shades retained', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .92))
    fig.savefig(EXPERIMENT / 'figures/combined_random_parity.png', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for row, weather in enumerate(['TMYx', 'DSY1']):
        for col, target in enumerate(['T_op_peak', 'hours_gt26_night']):
            ax = axes[row, col]
            variants = ['vent_rotation', 'interfloor', 'attic_party', 'combined', 'shade_off']
            for shift, arch, color in [(-.17, 'detached', '#b34b26'), (.17, 'semi', '#147879')]:
                means = []
                for variant in variants:
                    g = paired[paired.weather.eq(weather) & paired.archetype.eq(arch) & paired.variant.eq(variant) & paired.cohort.eq('random64')]
                    means.append((g[f'new_{target}'] - g[f'old_{target}']).abs().mean())
                ax.bar(np.arange(5) + shift, means, width=.32, color=color, label=arch)
            ax.set_xticks(np.arange(5), ['Vent\nbearings', 'Interfloor', 'Attic\nparty', 'Combined', 'Shade off\n(diagnostic)'])
            ax.set_ylabel('Mean absolute paired change')
            ax.set_title(f'{weather}: {LABELS[target]}')
            ax.legend(frameon=False)
    fig.suptitle('Isolated changes versus original model, random cohort only (n=64 per archetype)\nAttic-party-only is not applicable to detached; bar magnitudes are not additive', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .92))
    fig.savefig(EXPERIMENT / 'figures/variant_effects_random.png', dpi=180)
    plt.close(fig)


def main():
    protocol = json.loads((EXPERIMENT / 'protocol.json').read_text())
    verify_frozen(protocol)
    completion = json.loads((EXPERIMENT / 'results/full_completion.json').read_text())
    require(completion['all_ok'] and completion['runs'] == 1440, 'Full pilot is incomplete')
    manifest = json.loads((EXPERIMENT / 'backup/source_hashes.json').read_text())
    for path, h in manifest.items():
        require(digest(path) == h, f'Original source modified: {path}')
    require(digest(EXPERIMENT / 'backup/original_inputs.zip') == protocol['backup_sha256'], 'Backup changed')
    reference = pd.read_csv(EXPERIMENT / 'inputs/reference_metrics.csv')
    for row in reference.to_dict('records'):
        require(digest(row['source_csv']) == row['source_csv_sha256'], 'Original hourly file changed')
    records, added_warnings = [], []
    reference_lookup = reference.set_index(['weather', 'archetype', 'run_id'])
    for p in sorted((EXPERIMENT / 'runs').glob('*/*/*/*/result.json')):
        record = json.loads(p.read_text())
        require(record['status'] == 'ok', f'Failed run: {p}')
        require(record['idf_sha256'] == digest(p.parent / 'sim.idf'), 'Run IDF changed')
        expected = protocol['input_hashes'][f'inputs/idfs/{record["variant"]}/{record["archetype"]}/{record["run_id"]}.idf']
        require(record['idf_sha256'] == expected, 'Run IDF differs from assigned variant')
        require(record['csv_sha256'] == digest(p.parent / 'eplusout.csv'), 'Run output changed')
        require(record['weather_sha256'] == protocol['input_hashes'][f'inputs/{record["weather"]}.epw'], 'Run weather mismatch')
        original = reference_lookup.loc[(record['weather'], record['archetype'], record['run_id'])]
        original_errors = Path(original.source_csv).with_name('eplusout.err').read_text()
        new_errors = (p.parent / 'eplusout.err').read_text()
        pattern = r'^\s*\*\*\s*Warning\s*\*\*\s*(.+)$'
        old_warnings = Counter(re.findall(pattern, original_errors, re.MULTILINE))
        new_warnings = Counter(re.findall(pattern, new_errors, re.MULTILINE))
        for message, count in (new_warnings - old_warnings).items():
            added_warnings.append({k: record[k] for k in ['weather', 'archetype', 'variant', 'run_id']} | {'message': message, 'count': count})
        records.append(record)
    results = pd.DataFrame(records)
    require(len(results) == 1452 and not results.duplicated(['weather', 'archetype', 'variant', 'run_id']).any(), 'Incorrect unique simulation count')
    require(results.severe_errors.eq(0).all() and results.cooling_kWh.lt(1e-6).all(), 'Severe errors or active cooling')
    pd.DataFrame(added_warnings, columns=['weather', 'archetype', 'variant', 'run_id', 'message', 'count']).to_csv(EXPERIMENT / 'results/additional_warning_instances.csv', index=False)
    results.to_csv(EXPERIMENT / 'results/all_results.csv', index=False)
    keys = ['weather', 'archetype', 'run_id', 'cohort']
    metrics = TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual', 'two_of_three_proxy_dwelling']
    left = results[keys + ['variant'] + metrics].rename(columns={t: f'new_{t}' for t in metrics})
    right = reference[keys + metrics].rename(columns={t: f'old_{t}' for t in metrics})
    paired = left.merge(right, on=keys, how='left', validate='many_to_one', indicator=True)
    require(paired['_merge'].eq('both').all(), 'Missing paired reference')
    paired = paired.drop(columns='_merge')
    for t in metrics[:-1]:
        paired[f'delta_{t}'] = paired[f'new_{t}'] - paired[f'old_{t}']
    controls = paired[paired.variant.eq('control')]
    require(len(controls) == 12 and controls[[f'delta_{t}' for t in metrics[:-1]]].abs().max().max() < 1e-6, 'Controls do not reproduce originals')
    variant = paired[~paired.variant.eq('control')].copy()
    variant.to_csv(EXPERIMENT / 'results/paired_changes.csv', index=False)
    stats = summarize(variant, ['weather', 'archetype', 'variant', 'cohort'])
    stats.to_csv(EXPERIMENT / 'results/change_summary.csv', index=False)
    flags = flag_tables(variant)
    flags.to_csv(EXPERIMENT / 'results/threshold_changes.csv', index=False)

    # Archetype contrasts use the same building vector on both sides, not independent medians.
    cross = variant[variant.variant.eq('combined')].pivot(index=['weather', 'run_id', 'cohort'], columns='archetype', values=[f'{prefix}_{t}' for prefix in ['old', 'new'] for t in TARGETS])
    contrasts = []
    for (weather, cohort), g in cross.groupby(level=['weather', 'cohort']):
        for t in TARGETS:
            old = g[f'old_{t}', 'semi'] - g[f'old_{t}', 'detached']
            new = g[f'new_{t}', 'semi'] - g[f'new_{t}', 'detached']
            contrasts.append(dict(weather=weather, cohort=cohort, target=t, n=len(g),
                original_mean_semi_minus_detached=old.mean(), corrected_mean_semi_minus_detached=new.mean(),
                old_semi_lower_count=int((old < 0).sum()), new_semi_lower_count=int((new < 0).sum()),
                paired_contrast_sign_changes=int((np.sign(old) != np.sign(new)).sum())))
    pd.DataFrame(contrasts).to_csv(EXPERIMENT / 'results/archetype_contrasts.csv', index=False)
    plots(variant)

    lines = ['# Paired IDF Sensitivity Results', '',
        'This is an isolated pilot, not a replacement dataset or revised surrogate evaluation.', '',
        '## Verification', '',
        f'- {len(manifest)} original source paths unchanged; 4,000 original IDFs archived and hash-checked.',
        '- 320 original hourly outputs re-audited before running; hourly source hashes unchanged.',
        '- 12 unmodified controls reproduce every saved target; 1,440 variant runs completed.',
        '- All 1,452 unique runs have zero severe errors and zero active cooling.',
        f'- Initial ReadVarsESO audit-file failures: {completion.get("initial_failures", 0)}; recovered with isolated working directories: {completion.get("recovered_with_isolated_workdirs", 0)}. Initial runner, protocol and failed attempt are preserved in backup/.',
        f'- Additional warning instances relative to paired original logs: {sum(r["count"] for r in added_warnings)} (see additional_warning_instances.csv).',
        '- Each new run was evaluated using both independent target implementations.',
        '- Actual run IDFs, weather provenance and output hashes were checked after completion.', '',
        '## Interpretation Boundaries', '',
        '- Random64 and Stress16 cohorts are reported separately. Stress16 was partly selected using extreme outcomes.',
        '- Means, counts and maximum differences describe this pilot only, not all 2,000 cases or housing-stock rates.',
        '- Combined retains automatic interior shading. Shade-off is a separate diagnostic, not part of the proposed correction.',
        '- No ML retraining or SHAP reranking is performed here; unchanged conclusions cannot be inferred from a small temperature difference alone.',
        '- Single-change effects are not additive; no complete factorial or causal decomposition is claimed.',
        '- Threshold counts are screening proxies, not regulatory compliance outcomes.',
        '- Existing semi Kiva fraction remains 0.75. This experiment does not resolve all model simplifications.', '',
        '## Variants', '']
    lines += [f'- `{v}`: {description}' for v, description in VARIANTS.items()]
    lines += ['', '## Combined Correction: Random Cohort', '',
        'Units: He in percentage points, We in stepped proxy units, peak in deg C, night in hours, heating in kWh/m2/year. Differences are modified minus original.', '']
    cols = ['weather', 'archetype', 'target', 'n', 'mean_change', 'mean_absolute_change', 'max_absolute_change']
    lines.append(stats[stats.variant.eq('combined') & stats.cohort.eq('random64') & stats.target.isin(TARGETS)][cols].to_markdown(index=False, floatfmt='.4f'))
    lines += ['', '## Individual Changes: Random Cohort', '']
    lines.append(stats[stats.cohort.eq('random64') & stats.target.isin(['T_op_peak', 'hours_gt26_night'])][['weather', 'archetype', 'variant', 'target', 'mean_change', 'mean_absolute_change', 'max_absolute_change']].to_markdown(index=False, floatfmt='.4f'))
    lines += ['', '## Combined Correction: Stress Cohort', '']
    lines.append(stats[stats.variant.eq('combined') & stats.cohort.eq('stress16') & stats.target.isin(TARGETS)][cols].to_markdown(index=False, floatfmt='.4f'))
    lines += ['', '## Combined Threshold Changes: Random Cohort', '']
    lines.append(flags[flags.variant.eq('combined') & flags.cohort.eq('random64')].drop(columns=['variant', 'cohort']).to_markdown(index=False))
    lines += ['', '## Files', '', '- `results/change_summary.csv`: all target differences by variant/cohort.',
        '- `results/paired_changes.csv`: per-building paired targets and changes.',
        '- `results/threshold_changes.csv`: old/new proxy counts and both crossing directions.',
        '- `results/archetype_contrasts.csv`: matched semi-minus-detached differences.',
        '- `inputs/idf_change_log.json`: every modified IDF field.',
        '- `figures/variant_effects_random.png` and `figures/combined_random_parity.png`.', '',
        'Original manuscripts, model checkpoints and result tables remain unchanged. Decisions about full reruns and paper updates require reviewing these pilot differences.']
    (EXPERIMENT / 'reports/paired_sensitivity_results.md').write_text('\n'.join(lines) + '\n')
    atomic_json(EXPERIMENT / 'results/verification.json', {'source_paths_unchanged': len(manifest), 'source_hourlies_unchanged': len(reference), 'unique_successful_runs': len(results), 'controls_exact': True, 'independent_postprocessors': True, 'backup_sha256': digest(EXPERIMENT / 'backup/original_inputs.zip'), 'report_script_sha256': digest(Path(__file__)), 'paired_changes_sha256': digest(EXPERIMENT / 'results/paired_changes.csv')})
    print(stats[stats.variant.eq('combined') & stats.cohort.eq('random64') & stats.target.isin(TARGETS)][cols].to_string(index=False))


if __name__ == '__main__':
    main()
