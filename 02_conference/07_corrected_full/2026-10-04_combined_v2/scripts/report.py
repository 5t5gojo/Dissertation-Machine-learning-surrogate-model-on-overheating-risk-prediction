"""Corrected full-data report, figures and explicitly versioned legacy comparisons."""
import json
from collections import Counter
from pathlib import Path
import platform
import re
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(ROOT / 'frozen_code'))
from revision_common import FEATURES, TARGETS, LABELS, TITLES, UNITS, sha, write_json

FAMILIES = ['RF', 'XGBoost', 'MLP']
COLORS = ['#546b85', '#be623c', '#23795e']
OLD = {'TMYx': PROJECT / '02_conference/03_data/evaluation',
       'DSY1': PROJECT / '02_conference/03_data/weather_scenarios/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/full/evaluation'}
FEATURE_LABEL = dict(zip(FEATURES, LABELS))
UNIT = dict(zip(TARGETS, UNITS))
SHORT_TITLE = dict(zip(TARGETS, ['Seasonal exceedance proxy', 'Daily stepped exceedance',
                               'Peak operative temperature', 'Summer bedroom night hours',
                               'Ideal heating demand intensity']))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'pdf.fonttype': 42,
                     'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix('.png'), dpi=200, bbox_inches='tight')
    fig.savefig(path.with_suffix('.pdf'), bbox_inches='tight')
    plt.close(fig)


def verify_error_logs():
    rows, unexpected = [], []
    old_runs = {'TMYx': PROJECT / 'formal model file/output/runs',
                'DSY1': OLD['DSY1'].parent / 'runs'}
    for weather in ['TMYx', 'DSY1']:
        d = pd.read_csv(ROOT / 'datasets' / weather / 'results.csv')
        assert len(d) == 4000 and d.status.eq('ok').all()
        for record in d.to_dict('records'):
            case = Path(record['archetype']) / record['run_id']
            current = (ROOT / 'datasets' / weather / 'runs' / case / 'eplusout.err').read_text()
            previous = (old_runs[weather] / case / 'eplusout.err').read_text()
            assert 'EnergyPlus Completed Successfully' in current
            assert not re.search(r'\*\*\s*(Severe|Fatal)\s*\*\*', current)
            counts = [Counter(re.findall(r'\*\*\s*Warning\s*\*\*\s*(.*)', text)) for text in [previous, current]]
            added = counts[1] - counts[0]
            rows.append(dict(weather=weather, archetype=record['archetype'], run_id=record['run_id'],
                             previous_warning_lines=sum(counts[0].values()), corrected_warning_lines=sum(counts[1].values()),
                             added_warning_lines=sum(added.values())))
            if added:
                unexpected.append(dict(weather=weather, case=str(case), added=dict(added)))
    pd.DataFrame(rows).to_csv(ROOT / 'reports/error_log_audit.csv', index=False)
    write_json(ROOT / 'reports/error_log_verification.json', dict(cases=len(rows),
        severe_or_fatal=0, added_warnings=unexpected,
        note='Counts include ReadVarsESO warning lines, which are outside the EnergyPlus final warning total.'))
    assert not unexpected, 'New warnings need inspection before claiming final verification'


def change_stats(old, new, keys):
    metrics = TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']
    pairs = old[keys + metrics].merge(new[keys + metrics], on=keys, validate='one_to_one', suffixes=('_old', '_new'))
    assert len(pairs) == len(old) == len(new)
    rows = []
    for group, g in pairs.groupby('archetype'):
        for t in metrics:
            delta = g[f'{t}_new'] - g[f'{t}_old']
            rows.append(dict(archetype=group, target=t, n=len(g), mean_old=g[f'{t}_old'].mean(), mean_new=g[f'{t}_new'].mean(),
                mean_change=delta.mean(), median_change=delta.median(), mean_absolute_change=delta.abs().mean(),
                p95_absolute_change=delta.abs().quantile(.95), maximum_absolute_change=delta.abs().max(),
                increased=int((delta>1e-9).sum()), decreased=int((delta<-1e-9).sum())))
            pairs.loc[g.index, f'delta_{t}'] = delta
    return pairs, pd.DataFrame(rows)


def simulation_summary(frame):
    rows = []
    for arch, g in frame.groupby('archetype'):
        rows.append(dict(archetype=arch, n=len(g), C1_gt3=int(g.He_worst.gt(3).sum()), C2_gt6=int(g.We_max_worst.gt(6).sum()),
            C3_nonzero=int(g.hours_C3_worst.gt(0).sum()), same_zone_two_of_three_proxy=int(g.two_of_three_proxy_dwelling.sum()),
            night_zero_pct=100*g.hours_gt26_night.eq(0).mean(), night_summer_gt32=int(g.hours_gt26_night.gt(32).sum()),
            night_annual_gt32=int(g.hours_gt26_night_annual.gt(32).sum()), median_peak_C=g.T_op_peak.median(), max_peak_C=g.T_op_peak.max(),
            median_heating_kWh_m2=g.heat_kWh_m2.median(), max_cooling_kWh=g.cooling_kWh.max()))
    return pd.DataFrame(rows)


def correction_figure(weather, pairs):
    fig, axs = plt.subplots(2, 5, figsize=(18, 7), layout='constrained')
    for row, arch in enumerate(['detached', 'semi']):
        g = pairs[pairs.archetype.eq(arch)]
        for col, target in enumerate(TARGETS):
            ax = axs[row, col]
            old, new = g[f'{target}_old'], g[f'{target}_new']
            lo, hi = min(old.min(), new.min()), max(old.max(), new.max())
            ax.plot([lo, hi], [lo, hi], '--', color='0.5', linewidth=1)
            ax.scatter(old, new, s=5, alpha=.25, color=['#467a8e', '#bb744d'][row], rasterized=True)
            ax.set_title(SHORT_TITLE[target], fontsize=10)
            ax.set_xlabel(f'Legacy simulation ({UNIT[target]})', fontsize=9)
            ax.set_ylabel(f'Corrected {arch} ({UNIT[target]})', fontsize=9)
    fig.suptitle(f'{weather}: paired effect of IDF corrections / 2,000 cases per archetype\n'
                 'Same LHS and weather; dashed line = unchanged simulation target', fontsize=13)
    save(fig, ROOT / 'figures' / weather / 'appendix/legacy_vs_corrected_targets')


def attributions(dest):
    s = pd.read_csv(dest / 'shap_importance_all.csv')
    s['rank'] = s.groupby(['archetype', 'seed', 'target']).mean_abs_shap.rank(ascending=False, method='min')
    ss = s.groupby(['archetype', 'target', 'feature']).agg(mean_abs_shap=('mean_abs_shap', 'mean'), sd_abs_shap=('mean_abs_shap', 'std'),
        min_rank=('rank', 'min'), max_rank=('rank', 'max'), first_rank_splits=('rank', lambda x: int(x.eq(1).sum()))).reset_index()
    ss['rank_of_mean'] = ss.groupby(['archetype', 'target']).mean_abs_shap.rank(ascending=False, method='min')
    ss.to_csv(dest / 'shap_mean_values_and_ranks.csv', index=False)
    pi = pd.read_csv(dest / 'permutation_importance_all.csv')
    ps = pi.groupby(['archetype', 'seed', 'model', 'target', 'feature']).normalized_mse_increase.mean().reset_index()
    ps['rank'] = ps.groupby(['archetype', 'seed', 'model', 'target']).normalized_mse_increase.rank(ascending=False, method='min')
    ps.to_csv(dest / 'permutation_ranks_by_split.csv', index=False)
    agreement = []
    for (arch, target), group in ps.groupby(['archetype', 'target']):
        wide = group.groupby(['feature', 'model']).normalized_mse_increase.mean().unstack()
        agreement.append(dict(archetype=arch, target=target, rank_spearman=spearmanr(wide.XGBoost, wide.MLP).statistic,
            xgb_top_feature=wide.XGBoost.idxmax(), mlp_top_feature=wide.MLP.idxmax()))
    pd.DataFrame(agreement).to_csv(dest / 'cross_model_importance_comparison.csv', index=False)
    return ss


def figures(weather, source, ss, performance):
    dest = source / 'evaluation'
    figdir = ROOT / 'figures' / weather
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), sharey=True, layout='constrained')
    for ax, arch in zip(axs, ['detached', 'semi']):
        for k, (model, color) in enumerate(zip(FAMILIES, COLORS)):
            s = performance[performance.archetype.eq(arch) & performance.model.eq(model)].set_index('target').loc[TARGETS]
            ax.errorbar(np.arange(5)+(k-1)*.15, s.R2_mean, yerr=s.R2_std, fmt='o', capsize=4, label=model, color=color)
        ax.set_xticks(range(5), ['C1 proxy', 'C2 proxy', 'Peak temp.', 'Night hours', 'Heating'], rotation=25, ha='right')
        ax.set_title(f'{weather} / {arch} / corrected V2')
        ax.set_ylabel('Test R2: mean +/- SD (five overlapping splits)')
        ax.legend(frameon=False)
        ax.grid(alpha=.15)
    save(fig, figdir / 'in_text/model_accuracy')
    for target, title, unit in zip(TARGETS, TITLES, UNITS):
        fig, axs = plt.subplots(1, 2, figsize=(14, 7), layout='constrained')
        subset = ss[ss.target.eq(target)]
        limit = float((subset.mean_abs_shap+subset.sd_abs_shap).max()) * 1.08
        fig.suptitle(f'{weather} / corrected V2 / {title}\nXGBoost attribution magnitude: five-split mean +/- SD', fontsize=13)
        for ax, arch, color in zip(axs, ['detached', 'semi'], ['#467a8e', '#bb744d']):
            s = subset[subset.archetype.eq(arch)].sort_values('mean_abs_shap')
            ax.barh([FEATURE_LABEL[f] for f in s.feature], s.mean_abs_shap, xerr=s.sd_abs_shap, color=color, capsize=3)
            ax.set_title(arch)
            ax.set_xlabel(f'Mean absolute SHAP ({unit})')
            ax.set_xlim(0, limit)
            ax.grid(axis='x', alpha=.15)
        section = 'in_text' if target in ['T_op_peak', 'hours_gt26_night'] else 'appendix'
        save(fig, figdir / section / f'shap_{target}')
    # The prespecified seed-42 plot shows unique held-out cases, not pooled repeats.
    import shap
    for arch in ['detached', 'semi']:
        d = pd.read_csv(source / f'training_{arch}.csv').set_index('run_id')
        for target in TARGETS:
            v = pd.read_csv(dest / arch / 'seed_42' / f'shap_values_{target}.csv')
            order = ss[ss.archetype.eq(arch) & ss.target.eq(target)].sort_values('mean_abs_shap', ascending=False).feature.tolist()
            x = d.loc[v.run_id, order]
            shap.summary_plot(v[order].to_numpy(), x.to_numpy(), feature_names=[FEATURE_LABEL[f] for f in order],
                              max_display=14, sort=False, show=False, plot_size=(9, 7), color_bar_label='Feature value',
                              rng=np.random.default_rng(42))
            fig = plt.gcf()
            plt.title(f'{weather} / {arch} / corrected V2\nSeed 42 test cases; feature order from five-split mean importance', fontsize=11)
            plt.xlabel(f'SHAP contribution ({UNIT[target]})')
            section = 'in_text' if target in ['T_op_peak', 'hours_gt26_night'] else 'appendix'
            save(fig, figdir / section / f'{arch}_beeswarm_{target}')
        pred = pd.read_csv(dest / 'predictions_all.csv')
        fig, axs = plt.subplots(2, 5, figsize=(18, 7), layout='constrained')
        for row, family in enumerate(['XGBoost', 'MLP']):
            for col, target in enumerate(TARGETS):
                g = pred[pred.archetype.eq(arch) & pred.seed.eq(42) & pred.model.eq(family) & pred.target.eq(target)]
                ax = axs[row, col]
                lo, hi = min(g.y_true.min(), g.y_pred.min()), max(g.y_true.max(), g.y_pred.max())
                ax.plot([lo, hi], [lo, hi], '--', color='0.5')
                ax.scatter(g.y_true, g.y_pred, s=10, alpha=.55, color=COLORS[row+1])
                ax.set_title(SHORT_TITLE[target], fontsize=10)
                ax.set_xlabel(f'Simulation ({UNIT[target]})', fontsize=9)
                ax.set_ylabel(f'{family} prediction ({UNIT[target]})', fontsize=9)
        fig.suptitle(f'{weather} / {arch} / corrected V2 / prespecified seed-42 test set', fontsize=14)
        save(fig, figdir / 'appendix' / f'{arch}_parity_seed42')
        fig, axs = plt.subplots(1, 5, figsize=(18, 3.5), layout='constrained')
        for ax, seed in zip(axs, [42, 123, 202, 340, 567]):
            folder = dest / arch / f'seed_{seed}'
            selected = json.loads((folder / 'MLP_selected.json').read_text())
            curve = pd.read_csv(folder / f'MLP_candidate_{selected["candidate"]}_loss.csv')
            ax.plot(curve.epoch, curve.train_loss, label='Training')
            ax.plot(curve.epoch, curve.val_loss, label='Validation')
            ax.set_title(f'Seed {seed}; candidate {selected["candidate"]}')
            ax.set_xlabel('Epoch')
            ax.set_ylabel('Standardized MSE')
            ax.set_yscale('log')
            ax.legend(frameon=False)
        save(fig, figdir / 'appendix' / f'{arch}_selected_MLP_losses')


def weather_report(weather):
    source = ROOT / 'datasets' / weather
    dest = source / 'evaluation'
    assert json.loads((source / 'complete.json').read_text())['audited'] == 4000
    assert json.loads((dest / 'complete.json').read_text())['all_ok']
    data = pd.read_csv(source / 'results.csv')
    assert len(data) == 4000 and data.status.eq('ok').all()
    summary = simulation_summary(data)
    summary.to_csv(source / 'simulation_summary.csv', index=False)
    distributions = data.groupby('archetype')[TARGETS + ['hours_C3_worst', 'hours_gt26_night_annual']].agg(['mean', 'median', 'std', 'min', 'max'])
    distributions.to_csv(source / 'target_distribution_summary.csv')
    original = pd.concat([pd.read_csv(ROOT / 'inputs' / f'original_{weather}_{a}.csv') for a in ['detached', 'semi']], ignore_index=True)
    pairs, changes = change_stats(original, data, ['archetype', 'run_id'])
    pairs.to_csv(source / 'legacy_paired_changes.csv', index=False)
    changes.to_csv(source / 'legacy_change_summary.csv', index=False)
    correction_figure(weather, pairs)
    old_summary = simulation_summary(original)
    old_summary.merge(summary, on='archetype', suffixes=('_legacy', '_corrected')).to_csv(source / 'legacy_threshold_comparison.csv', index=False)
    p = pd.read_csv(dest / 'performance_summary.csv')
    selected = p[p.model.isin(FAMILIES)].copy()
    selected['R2 mean +/- SD'] = selected.apply(lambda r: f'{r.R2_mean:.3f} +/- {r.R2_std:.3f}', axis=1)
    table = selected.pivot(index=['archetype', 'target'], columns='model', values='R2 mean +/- SD').reset_index()
    previous = pd.read_csv(OLD[weather] / 'performance_summary.csv')
    selected.merge(previous, on=['archetype', 'model', 'target'], suffixes=('_corrected', '_legacy')).to_csv(dest / 'legacy_model_performance_comparison.csv', index=False)
    ss = attributions(dest)
    agreement = pd.read_csv(dest / 'cross_model_importance_comparison.csv')
    leaders = ss[ss.rank_of_mean.eq(1)][['archetype', 'target', 'feature']].rename(columns={'feature': 'xgb_shap_leader'})
    leaders = leaders.merge(agreement, on=['archetype', 'target'], validate='one_to_one').rename(columns={
        'xgb_top_feature': 'xgb_permutation_leader', 'mlp_top_feature': 'mlp_permutation_leader'})
    leaders.to_csv(dest / 'attribution_leaders_by_method.csv', index=False)
    old_shap = pd.read_csv(OLD[weather] / 'shap_mean_values_and_ranks.csv')
    ss.merge(old_shap, on=['archetype', 'target', 'feature'], suffixes=('_corrected', '_legacy')).to_csv(dest / 'legacy_shap_comparison.csv', index=False)
    events = pd.read_csv(dest / 'night_event_detection_all.csv')
    sub = pd.read_csv(dest / 'night_subgroups_all.csv')
    sub_summary = sub.groupby(['archetype', 'model', 'subgroup']).agg(RMSE_mean=('RMSE', 'mean'), RMSE_sd=('RMSE', 'std'),
        MAE_mean=('MAE', 'mean'), bias_mean=('bias', 'mean'), n_min=('n', 'min'), n_max=('n', 'max'), valid_splits=('RMSE', 'count')).reset_index()
    sub_summary.to_csv(dest / 'night_subgroup_summary.csv', index=False)
    pred = pd.read_csv(dest / 'predictions_all.csv')
    pred.assign(negative=pred.y_pred.lt(0)).groupby(['archetype', 'model', 'target']).agg(negative_predictions=('negative', 'sum'), minimum_prediction=('y_pred', 'min')).to_csv(dest / 'negative_prediction_summary.csv')
    figures(weather, source, ss, selected)
    night = ss[ss.target.eq('hours_gt26_night') & ss.rank_of_mean.le(3)].sort_values(['archetype', 'rank_of_mean'])
    sections = [f'# {weather}: Corrected Full Results (Combined V2)', '',
        'This report replaces neither the preserved legacy data nor the existing Word manuscripts. Use corrected tables and figures together, not mixed with legacy values.', '',
        '## Model and Simulation', '',
        'Full original LHS: 2,000 detached + 2,000 semi-detached cases. Three IDF corrections: wind-opening bearings follow rotation; intermediate-floor construction no longer contains sampled loft insulation; semi attic east gable is adiabatic. Automatic interior shades at 26.5 C remain enabled. The semi Kiva exposed fraction remains 0.75. All schedules, weather files and proxy definitions otherwise remain fixed.', '',
        summary.to_markdown(index=False, floatfmt='.4f'), '',
        'C1 uses the verified positive-occupancy schedule; C2 is the stepped proxy with strict >6; joint flags require two criteria in the SAME zone. None are formal compliance outcomes. Annual-night counts are diagnostic only.', '',
        '## Repeated Model Accuracy', '', table.to_markdown(index=False), '',
        'Five matched original 1400/300/300 splits; six candidate pipelines per model; validation-only selection. Equal configuration budget is not equal runtime. SD over overlapping splits is not an independent-sample confidence interval. Each weather dataset is retrained separately, not transferred.', '',
        '## Night-Time Diagnostics', '',
        sub_summary[sub_summary.model.isin(['XGBoost', 'MLP', 'AlwaysZero', 'TrainingMean'])].to_markdown(index=False, floatfmt='.4f'), '',
        'n_min/n_max are subgroup sizes per split; appearances across splits are not independent samples. Undefined empty/single-class metrics remain NA. Regression outputs are not clipped; negative-prediction diagnostics are retained separately.', '',
        events.groupby(['archetype', 'status']).size().rename('model_split_count').reset_index().to_markdown(index=False), '',
        '## Night-Time SHAP', '', night[['archetype', 'feature', 'mean_abs_shap', 'sd_abs_shap', 'rank_of_mean', 'first_rank_splits']].to_markdown(index=False, floatfmt='.4f'), '',
        'Rankings are five-split averages of exact selected-XGBoost attributions, not MLP explanations or causal effects. Cross-model permutation rankings are provided separately. Beeswarm figures use the prespecified seed-42 held-out cases, ordered by the five-split mean ranking; other splits may differ. Orientation is cyclic and high versus low numeric angles do not imply a monotonic physical effect.', '',
        '## Cross-Model Interpretation Check', '', agreement.to_markdown(index=False, floatfmt='.4f'), '',
        'This comparison uses permutation importance for BOTH models, not SHAP for one model versus a different importance method for the other. A high whole-ranking Spearman correlation does not establish an identical leading feature. Where the two leading-feature columns differ, do not claim model-independent dominance.', '',
        '### Method Dependence of the Leading Feature', '',
        leaders.to_markdown(index=False, floatfmt='.4f'), '',
        'SHAP here ranks mean absolute prediction contributions; permutation importance ranks the increase in held-out prediction loss. The same XGBoost model can therefore have different leading features under these two summaries. Report the named method, model and weather, rather than asserting a universal physical driver.', '',
        '## Changes from Legacy Model', '', changes.to_markdown(index=False, floatfmt='.4f'), '',
        'Model-performance and SHAP comparisons are in evaluation/legacy_model_performance_comparison.csv and evaluation/legacy_shap_comparison.csv. A changed R2 can reflect changed target variance, not only learner quality.', '',
        '## Remaining Boundaries', '',
        '- This is internal validation against EnergyPlus, not monitored-building or benchmark physical validation.',
        '- Intermediate-floor concrete-only and full-height adjoining attic are explicit assumptions; the overall reference model remains simplified.',
        '- No DSY2/DSY3 or TRY control is added. DSY1 and TMYx differ in source/location representation and scenario period, not just severity.',
        '- Occupancy/security/noise do not restrict openings; opening need not require outdoor temperature below indoor temperature.',
        '- C3 remains diagnostic to retain the same five-target comparison.',
        '- Legacy paper text, reviewer replies and supplementary package require coordinated updating before submission.', '',
        '## Verification', '',
        '4,000 outputs independently re-audited; 180 candidate trials; 45,000 held-out predictions; 150 trained-model metric rows and 50 SHAP arrays recomputed from saved models. Scalers fitted to training data only; split identities and validation selection verified.']
    report = ROOT / 'reports' / f'{weather}_corrected_results.md'
    report.write_text('\n'.join(sections) + '\n')
    return data, summary, selected, ss, report


def main():
    idfs = json.loads((ROOT / 'reports/idf_verification.json').read_text())
    assert idfs['idfs_checked'] == 4000 and idfs['opening_bearings_checked'] == 28000
    assert idfs['controls_and_materials_verified'] and idfs['subprocess_cwd_verified']
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    for path, digest in protocol['input_hashes'].items():
        assert sha(ROOT / path) == digest, f'Frozen input changed: {path}'
    for path, digest in json.loads((ROOT / 'backup/protected_sources.json').read_text()).items():
        assert sha(path) == digest, f'Legacy source changed: {path}'
    verify_error_logs()
    hardware = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string', 'hw.ncpu', 'hw.memsize'], text=True).splitlines()
    timings = []
    for weather in ['TMYx', 'DSY1']:
        cases = pd.read_csv(ROOT / 'datasets' / weather / 'results.csv')
        completed = json.loads((ROOT / 'datasets' / weather / 'complete.json').read_text())
        new_cases = cases[~cases.reused_pilot]
        timings.append(dict(weather=weather, new_cases=len(new_cases), reused_cases=int(cases.reused_pilot.sum()),
            batch_seconds_including_audit=completed['elapsed_seconds'],
            mean_new_case_processing_seconds=new_cases.processing_seconds.mean(),
            median_new_case_processing_seconds=new_cases.processing_seconds.median()))
    pd.DataFrame(timings).to_csv(ROOT / 'reports/runtime_summary.csv', index=False)
    write_json(ROOT / 'reports/environment_and_runtime.json', dict(cpu=hardware[0], logical_cpus=int(hardware[1]),
        memory_bytes=int(hardware[2]), platform=platform.platform(), python=sys.version,
        energyplus_version=protocol['energyplus_version'], simulation_workers=8, model_workers=3,
        note='Per-case processing time includes EnergyPlus invocation and target checks. Batch time includes final audit and pilot reuse. TMYx training overlaps DSY1 simulation; these are not dedicated-hardware runtime benchmarks.'))
    results = {w: weather_report(w) for w in ['TMYx', 'DSY1']}
    pairs, changes = change_stats(results['TMYx'][0], results['DSY1'][0], ['archetype', 'run_id'])
    pairs.rename(columns=lambda c: c.replace('_old', '_TMYx').replace('_new', '_DSY1')).to_csv(ROOT / 'reports/corrected_paired_weather_cases.csv', index=False)
    changes = changes.rename(columns={'mean_old': 'mean_TMYx', 'mean_new': 'mean_DSY1',
                                     'mean_change': 'mean_DSY1_minus_TMYx', 'median_change': 'median_DSY1_minus_TMYx'})
    changes.to_csv(ROOT / 'reports/corrected_paired_weather_summary.csv', index=False)
    corrections = pd.concat([pd.read_csv(ROOT / 'datasets' / w / 'legacy_change_summary.csv').assign(weather=w)
                             for w in ['TMYx', 'DSY1']], ignore_index=True)
    effect = corrections[corrections.target.isin(['T_op_peak', 'hours_gt26_night', 'heat_kWh_m2'])].pivot(
        index=['weather', 'archetype'], columns='target', values='mean_change').reset_index().rename(columns={
            'T_op_peak': 'mean_delta_peak_C', 'hours_gt26_night': 'mean_delta_night_hours',
            'heat_kWh_m2': 'mean_delta_heating_kWh_m2'})
    effect = effect[['weather', 'archetype', 'mean_delta_peak_C', 'mean_delta_night_hours', 'mean_delta_heating_kWh_m2']]
    effect.to_csv(ROOT / 'reports/idf_correction_mean_changes.csv', index=False)
    tables = []
    for weather, (_, summary, accuracy, importance, _) in results.items():
        tables.append(summary.assign(weather=weather))
    coverage = pd.concat(tables, ignore_index=True)
    coverage.to_csv(ROOT / 'reports/corrected_simulation_coverage.csv', index=False)
    all_accuracy = pd.concat([result[2].assign(weather=weather) for weather, result in results.items()], ignore_index=True)
    all_accuracy.to_csv(ROOT / 'reports/corrected_model_accuracy.csv', index=False)
    all_shap = pd.concat([result[3].assign(weather=weather) for weather, result in results.items()], ignore_index=True)
    all_shap.to_csv(ROOT / 'reports/corrected_shap_rankings.csv', index=False)
    leading = all_shap[all_shap.target.eq('hours_gt26_night') & all_shap.rank_of_mean.le(3)].sort_values(['weather', 'archetype', 'rank_of_mean'])
    method_leaders = pd.concat([pd.read_csv(ROOT / 'datasets' / w / 'evaluation/attribution_leaders_by_method.csv').assign(weather=w)
                               for w in ['TMYx', 'DSY1']], ignore_index=True)
    night_leaders = method_leaders[method_leaders.target.eq('hours_gt26_night')][
        ['weather', 'archetype', 'xgb_shap_leader', 'xgb_permutation_leader', 'mlp_permutation_leader']]
    report = ['# Combined V2: Full Corrected Experiment', '',
        '**Status: full corrected simulations, repeated model training, verification and new figures completed. Existing Word manuscripts and submission ZIP are still legacy versions and must not be submitted with these new numbers until updated.**', '',
        '## Scope', '',
        '8,000 successful paired weather/archetype simulations: 7,680 newly executed and 320 hash-matched pilot results reused. Original IDFs, data, models and manuscripts were preserved. The same 14-dimensional LHS and five original splits were retained.', '',
        'Changes: ventilation bearings, intermediate-floor insulation separation and full-height semi attic party wall. Automatic interior shades at 26.5 C remain; Kiva fraction stays 0.75. No physical validation or compliance claim is added.', '',
        '## How Much Did the IDF Corrections Change Results?', '', effect.to_markdown(index=False, floatfmt='.4f'), '',
        'Each delta is corrected minus legacy, for the same weather and same 2,000 LHS samples per archetype. These are NOT DSY1-minus-TMYx changes. A lower peak temperature does not necessarily mean fewer night-time exceedance hours.', '',
        '## Full Simulation Coverage', '', coverage.to_markdown(index=False, floatfmt='.4f'), '',
        '## Corrected Model Accuracy', '',
        all_accuracy.pivot(index=['weather', 'archetype', 'target'], columns='model', values='R2 mean +/- SD').reset_index().to_markdown(index=False), '',
        '## Corrected Night-Time SHAP', '',
        leading[['weather', 'archetype', 'feature', 'rank_of_mean', 'mean_abs_shap', 'first_rank_splits']].to_markdown(index=False, floatfmt='.4f'), '',
        'These are XGBoost predictive attributions. Consult permutation agreement before generalising to MLP. No causal mechanism or ranking stability is assumed from the legacy results.', '',
        '### Do the Leading Features Agree Across Methods?', '', night_leaders.to_markdown(index=False), '',
        'Differences in this table must be retained in the interpretation. SHAP contribution magnitude and permutation-induced prediction loss do not define the same quantity; neither demonstrates a unique physical cause.', '',
        '## Paired Weather Changes', '', changes.to_markdown(index=False, floatfmt='.4f'), '',
        'This compares two specified weather datasets using identical corrected buildings, not an isolated climate-severity effect.', '',
        '## Where to Read', '',
        '- `TMYx_corrected_results.md` and `DSY1_corrected_results.md`: full counts, error diagnostics, differences and limitations.',
        '- `datasets/<weather>/evaluation/`: models, splits, candidate trials, metrics, SHAP values and permutation results.',
        '- `figures/<weather>/in_text/`: corrected model accuracy, peak/night SHAP and seed-42 directional figures.',
        '- `figures/<weather>/appendix/`: other targets, parity plots and selected MLP loss curves.',
        '- `datasets/<weather>/legacy_change_summary.csv`: full-data effect of the IDF corrections.', '',
        '## Verification', '',
        '360 candidate trials; 20 matched partitions; 90,000 held-out predictions; 300 trained-model metric rows and 100 SHAP arrays independently recomputed. All protected source hashes still match. All 8,000 error logs were checked: no severe/fatal errors or additional warning lines compared with their corresponding legacy case. Existing unused-construction/cost and CSV-processing warnings are retained in the audit, not described as zero warnings. Full source/target checks and verification manifests are retained.']
    path = ROOT / 'reports/START_HERE_corrected_full_results.md'
    path.write_text('\n'.join(report) + '\n')
    checklist = [
        '# Manuscript and Submission Update Checklist', '',
        'The corrected V2 experiment is complete; this is NOT a declaration that the existing Word manuscript or submission ZIP has been updated.', '',
        '## Methods and Model Definition', '',
        '- Describe the corrected wind-opening bearings as local facade bearing plus building/zone rotation, modulo 360 degrees.',
        '- Separate the occupied-storey interface (100 mm reinforced concrete only) from the loft interface (sampled insulation plus concrete). Do not state that sampled loft insulation also belongs between occupied storeys.',
        '- State that the semi-detached attic east gable is adiabatic: the adjoining dwelling is assumed to extend to the full gable height.',
        '- Disclose retained automatic interior shades, activated above 26.5 C zone air temperature, in addition to sampled exterior overhang depth.',
        '- Retain the caveat that the semi Kiva exposed-perimeter fraction is fixed at 0.75, rather than derived separately for every sampled width/length.',
        '- Do not claim occupancy/security-controlled window operation, formal TM52/TM59 compliance, or monitored physical validation.', '',
        '## Results, Figures and Conclusions', '',
        '- Update BOTH TMYx and DSY1 distributions, threshold-proxy counts, heating statistics and paired weather differences from corrected_simulation_coverage.csv and the per-weather datasets.',
        '- Replace model comparison values with corrected_model_accuracy.csv: five overlapping splits, mean +/- SD, six configurations per family and validation-only selection. Do not reuse single-split legacy headlines.',
        '- Replace every SHAP figure and ranking from corrected_shap_rankings.csv. Do not carry forward a legacy orientation or night-time hierarchy without checking the new table.',
        '- In corrected V2, the semi-detached night-time XGBoost SHAP leader is window opening factor in BOTH weather datasets. The old statement that DSY1 makes g-value first in both archetypes no longer describes these corrected results. Separately, DSY1 permutation importance has g-value first for both XGBoost and MLP; do not suppress this method dependence.',
        '- Separate XGBoost SHAP from MLP predictive accuracy. Use cross_model_importance_comparison.csv to report the actual degree of permutation-ranking agreement.',
        '- Report sparse-night subgroup errors and single-class limitations; do not present undefined event discrimination as perfect performance.',
        '- Keep the DSY1 experiment framed as separate training under a specified weather scenario, not frozen-model transfer or a controlled isolation of climate severity.', '',
        '## Response Letter and Supplement', '',
        '- Explain that a subsequent IDF audit led to three transparent modelling corrections; include the new-versus-legacy paired comparison rather than silently replacing numbers.',
        '- Update all reviewer response references, table/figure numbers and supplementary data links in the same revision.',
        '- Retain the old package for provenance. Label a new submission package corrected V2 and exclude licensed weather files from public distribution.',
        '- Check final Word/PDF layout and conference requirements after coordinated text changes. No submission-format compliance is asserted by this simulation report.', '',
        '## Evidence Location', '',
        '- reports/START_HERE_corrected_full_results.md: numerical overview and remaining boundaries.',
        '- reports/idf_verification.json: independent 4,000-IDF geometry, construction and control checks.',
        '- datasets/<weather>/legacy_change_summary.csv: magnitude of all paired IDF-correction effects.',
        '- datasets/<weather>/evaluation/verification.json: saved-model, split, selection, metric and SHAP checks.',
        '- backup/original_backup_reference.json: verified original archive location and checksum.',
    ]
    (ROOT / 'reports/MANUSCRIPT_UPDATE_CHECKLIST.md').write_text('\n'.join(checklist) + '\n')
    artifacts = [p for folder in ['scripts', 'reports', 'figures'] for p in (ROOT / folder).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts]
    for weather in ['TMYx', 'DSY1']:
        source = ROOT / 'datasets' / weather
        artifacts += [p for p in source.iterdir() if p.is_file() and p.name != 'results_in_progress.csv']
        artifacts += [p for p in (source / 'evaluation').rglob('*') if p.is_file()]
    manifest = ROOT / 'artifact_hashes.json'
    write_json(manifest, {str(p.relative_to(ROOT)): sha(p) for p in sorted(artifacts)})
    write_json(ROOT / 'complete.json', dict(all_ok=True, cases=8000, newly_simulated=7680, pilot_reused=320,
        trials=360, held_out_prediction_rows=90000, trained_metric_rows_verified=300, shap_arrays_verified=100,
        original_sources_unchanged=True, manuscripts_updated=False, report_sha256=sha(path), report_script_sha256=sha(__file__),
        artifact_manifest_sha256=sha(manifest), indexed_artifacts=len(artifacts)))
    print(path, flush=True)
    print(coverage.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
