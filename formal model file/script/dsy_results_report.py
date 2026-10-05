"""Verify DSY repeated evaluation and generate a separate evidence report and figures."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from dsy_model_eval import FOLDER, OLD, SCENARIO, dataset
from revision_common import ROOT, TARGETS, FEATURES, LABELS, TITLES, UNITS, sha, write_json


def main():
    dest = FOLDER / 'evaluation'
    assert json.loads((dest / 'complete.json').read_text())['trials'] == 180
    proto = json.loads((dest / 'protocol.json').read_text())
    pred = pd.read_csv(dest / 'predictions_all.csv')
    perf = pd.read_csv(dest / 'performance_all.csv').set_index(['archetype','seed','model','target'])
    trials = pd.read_csv(dest / 'search_trials_all.csv')
    assert len(pred) == 45000 and len(trials) == 180
    for arch in ('detached','semi'):
        assert sha(FOLDER / f'training_{arch}.csv') == proto['data_hash'][arch]
        for seed in proto['seeds']:
            split = pd.read_csv(dest / arch / f'seed_{seed}/split.csv').set_index('run_id')
            oldsplit = pd.read_csv(OLD / arch / f'seed_{seed}/split.csv').set_index('run_id')
            assert split.sort_index().equals(oldsplit.sort_index())
            assert split.split.value_counts().to_dict() == {'train':1400, 'validation':300, 'test':300}
    for (arch, seed, model, target), g in pred.groupby(['archetype','seed','model','target']):
        assert len(g) == 300 and g.run_id.is_unique
        source = dataset(arch).set_index('run_id').loc[g.run_id,target].to_numpy()
        np.testing.assert_allclose(source,g.y_true)
        split = pd.read_csv(dest / arch / f'seed_{seed}/split.csv').set_index('run_id')
        assert split.loc[g.run_id,'split'].eq('test').all()
        values = [r2_score(g.y_true,g.y_pred),mean_absolute_error(g.y_true,g.y_pred),mean_squared_error(g.y_true,g.y_pred)**.5]
        np.testing.assert_allclose(values,perf.loc[(arch,seed,model,target),['R2','MAE','RMSE']].to_numpy(float),rtol=1e-7,atol=1e-8,equal_nan=True)
    for (arch,seed,family),g in trials.groupby(['archetype','seed','family']):
        assert len(g) == 6
        selection=json.loads((dest/arch/f'seed_{seed}'/f'{family}_selected.json').read_text())
        assert selection['candidate'] == g.loc[g.normalized_val_mse.idxmin(),'candidate']
    shap = pd.read_csv(dest / 'shap_importance_all.csv')
    shap['rank'] = shap.groupby(['archetype','seed','target']).mean_abs_shap.rank(ascending=False, method='min')
    ss = shap.groupby(['archetype','target','feature']).agg(mean_abs_shap=('mean_abs_shap','mean'),
        sd_abs_shap=('mean_abs_shap','std'),min_rank=('rank','min'),max_rank=('rank','max')).reset_index()
    ss['rank_of_mean'] = ss.groupby(['archetype','target']).mean_abs_shap.rank(ascending=False,method='min')
    ss.to_csv(dest/'shap_mean_values_and_ranks.csv',index=False)
    night_top = ss[ss.target.eq('hours_gt26_night') & ss.rank_of_mean.le(3)].sort_values(['archetype','rank_of_mean'])
    pi = pd.read_csv(dest/'permutation_importance_all.csv')
    agreement=[]
    for (arch,target),g in pi.groupby(['archetype','target']):
        wide=g.groupby(['feature','model']).normalized_mse_increase.mean().unstack()
        agreement.append(dict(archetype=arch,target=target,rank_spearman=spearmanr(wide.XGBoost,wide.MLP).statistic))
    pd.DataFrame(agreement).to_csv(dest/'cross_model_importance_comparison.csv',index=False)
    summary = pd.read_csv(dest/'performance_summary.csv')
    selected = summary[summary.model.isin(['RF','XGBoost','MLP'])].copy()
    selected['R2 mean +/- SD'] = selected.apply(lambda r:f'{r.R2_mean:.3f} +/- {r.R2_std:.3f}',axis=1)
    overview=selected.pivot(index=['archetype','target'],columns='model',values='R2 mean +/- SD').reset_index()
    old=pd.read_csv(OLD/'performance_summary.csv')
    selected.merge(old,on=['archetype','model','target'],suffixes=('_DSY','_TMYx')).to_csv(dest/'weather_model_performance_comparison.csv',index=False)
    figdir=ROOT.parent/'02_conference/04_figures'/SCENARIO
    figdir.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':11,'font.family':'DejaVu Sans','pdf.fonttype':42})
    def save(fig,name):
        fig.savefig(figdir/f'{name}.png',dpi=200,bbox_inches='tight')
        fig.savefig(figdir/f'{name}.pdf',bbox_inches='tight')
        plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    colors=['#56718b','#be6539','#23795e']
    for ax,arch in zip(axs,['detached','semi']):
        for k,(model,color) in enumerate(zip(['RF','XGBoost','MLP'],colors)):
            s=selected[(selected.archetype==arch)&(selected.model==model)].set_index('target').loc[TARGETS]
            ax.errorbar(np.arange(5)+(k-1)*.15,s.R2_mean,yerr=s.R2_std,fmt='o',capsize=4,label=model,color=color)
        ax.set_xticks(range(5),['C1 proxy','C2 proxy','Peak temp.','Night hours','Heating'],rotation=25,ha='right')
        ax.set_title(arch+' / DSY1');ax.set_ylabel('Test R2: mean +/- SD (five splits)');ax.legend();ax.grid(alpha=.15)
    lower = min(.65, float((selected.R2_mean-selected.R2_std).min())-.02)
    for ax in axs:
        ax.set_ylim(lower,1.0)
    save(fig,'repeated_model_accuracy')
    for target,title,unit in zip(TARGETS,TITLES,UNITS):
        fig,axs=plt.subplots(1,2,figsize=(13,7),layout='constrained')
        subset=ss[ss.target==target]
        limit=float((subset.mean_abs_shap+subset.sd_abs_shap).max())*1.08
        fig.suptitle('DSY1 / '+title+'\nTreeSHAP magnitude: mean +/- SD across five splits',fontsize=13)
        for ax,arch,color in zip(axs,['detached','semi'],['#467a8e','#bb744d']):
            s=ss[(ss.archetype==arch)&(ss.target==target)].sort_values('mean_abs_shap')
            labels=[dict(zip(FEATURES,LABELS))[f] for f in s.feature]
            ax.barh(labels,s.mean_abs_shap,xerr=s.sd_abs_shap,color=color,capsize=3)
            ax.set_title(arch);ax.set_xlabel(f'Mean absolute SHAP ({unit})');ax.grid(axis='x',alpha=.15);ax.set_xlim(0,limit)
        save(fig,'shap_'+target)
    metrics=pd.read_csv(FOLDER/'summary.csv')
    allrows=pd.read_csv(FOLDER/'results.csv')
    distribution=allrows.groupby('archetype')[TARGETS+['hours_C3_worst','hours_gt26_night_annual']].agg(['median','min','max'])
    distribution.to_csv(FOLDER/'target_distribution_summary.csv')
    pairs=pd.read_csv(FOLDER/'paired_comparison.csv')
    changes=[]
    for arch,g in pairs.groupby('archetype'):
        for t in TARGETS+['hours_C3_worst']:
            delta=g['delta_'+t]
            changes.append(dict(archetype=arch,target=t,mean_paired_change=delta.mean(),median_paired_change=delta.median(),fraction_increased=(delta>0).mean()))
    changes=pd.DataFrame(changes);changes.to_csv(FOLDER/'paired_change_summary.csv',index=False)
    events=pd.read_csv(dest/'night_event_detection_all.csv')
    report=f'''# DSY1 full simulation and repeated-model results

Weather: {SCENARIO}. All 4000 simulations were independently audited before training. IDFs and original TMYx result files were not overwritten. This is a weather-scenario comparison, not a formal compliance assessment or a controlled isolation of severity alone.

## Simulation coverage

{metrics.to_markdown(index=False)}

These counts now use the full original 2000-sample design per archetype, not the input-extreme pilot. C1 uses the verified positive-occupancy schedule; C2 is the stepped proxy with strict >6; same-zone joint flags remain proxies. Annual-night values are diagnostics, not training targets.

## Repeated model comparison

{overview.to_markdown(index=False)}

Exactly the original five split assignments and six candidate configurations per model were reused. Each pipeline is selected by normalized validation loss, never test results. Equal configuration budget is not equal runtime. Standard deviations describe overlapping repeated splits and are not independent-sample confidence intervals. This evaluates DSY-trained models, not transfer of frozen TMYx models.

## Night-time evaluation

Nonzero/high-tail/above-32-hour errors and AlwaysZero/TrainingMean baselines are in evaluation/night_subgroups_all.csv. Event-status counts:

{events.groupby(['archetype','status']).size().rename('model_split_count').reset_index().to_markdown(index=False)}

Where a validation or test set contains only one class, discrimination is not identifiable; undefined metrics are NA rather than being advertised as perfect classification.

## Paired weather changes

{changes.to_markdown(index=False,floatfmt='.4f')}

## Interpretation and boundaries

Leading DSY night-time features:

{night_top[['archetype','feature','mean_abs_shap','sd_abs_shap','rank_of_mean']].to_markdown(index=False,floatfmt='.4f')}

In this DSY experiment g-value ranks first in both archetypes; semi-detached window opening factor ranks second. The previous TMYx semi-detached opening-factor-first result is therefore weather-dependent, not a universal built-form mechanism. These are predictive attributions, not a controlled causal experiment.

- SHAP values/ranks are recalculated from the selected DSY XGBoost models; tables are in evaluation/shap_mean_values_and_ranks.csv. Cross-model permutation agreement is in evaluation/cross_model_importance_comparison.csv.
- C3 is retained as a diagnostic to keep the same five-target comparison. Because DSY activates it, a supplementary C3 surrogate is a possible additional experiment, not claimed here.
- Source location, weather-generation method and scenario period differ from St James's Park TMYx. Do not attribute every paired change solely to a hotter summer.
- No DSY2/DSY3, TRY control, physical validation or causal ablation has been performed.
- This report does not modify the preserved no-DSY Word manuscript or original reviewer response. Their numerical claims must be updated before a new submission.

## Verification

4000 audited simulations; 180 candidate trials; ten matched 1400/300/300 partitions; 45000 held-out predictions; all 150 trained-model metric rows recomputed; hyperparameter selection checked against minimum validation loss. Figures are stored separately under 02_conference/04_figures/{SCENARIO}.
'''
    report_path=ROOT.parent/'02_conference/05_reviewer_feedback/DSY1_results_summary.md'
    report_path.write_text(report)
    write_json(dest/'verification.json',{'prediction_rows':len(pred),'trials':len(trials),'all_model_metrics_recomputed':True,
        'original_splits_matched':True,'report_sha256':sha(report_path),'script_sha256':sha(__file__)})
    print(report_path,flush=True)


if __name__=='__main__':
    main()
