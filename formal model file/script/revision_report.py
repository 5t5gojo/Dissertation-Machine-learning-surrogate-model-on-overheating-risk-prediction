"""Build reviewer evidence tables, readable figures and manuscript replacement text."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from revision_common import ROOT, OUT, FEATURES, LABELS, TARGETS, TITLES, UNITS, dataset

FIG = OUT / 'figures'
DOC = OUT / 'reports'
EVAL = OUT / 'evaluation'
DISPLAY = dict(zip(FEATURES, LABELS))
COLORS = {'RF':'#56718b','XGBoost':'#be6539','MLP':'#23795e'}

def save(fig, name):
    fig.savefig(FIG/f'{name}.png', dpi=220, bbox_inches='tight', facecolor='white')
    fig.savefig(FIG/f'{name}.pdf', bbox_inches='tight', facecolor='white')
    plt.close(fig)

def write(name, text):
    (DOC/name).write_text(text.strip()+'\n')

def table(d):
    return d.to_markdown(index=False, floatfmt='.4f')

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    DOC.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':12,
                         'axes.labelsize':11,'pdf.fonttype':42,'ps.fonttype':42})
    shap=pd.read_csv(EVAL/'shap_importance_all.csv')
    shap['rank']=shap.groupby(['archetype','seed','target']).mean_abs_shap.rank(ascending=False,method='min')
    ss=shap.groupby(['archetype','target','feature']).agg(mean_abs_shap=('mean_abs_shap','mean'),
        sd_abs_shap=('mean_abs_shap','std'),mean_rank=('rank','mean'),min_rank=('rank','min'),max_rank=('rank','max')).reset_index()
    ss['rank_of_mean']=ss.groupby(['archetype','target']).mean_abs_shap.rank(ascending=False,method='min')
    ss.to_csv(EVAL/'shap_mean_values_and_ranks.csv',index=False)
    baseline=[]
    for a in ['detached','semi']:
        b=pd.read_csv(ROOT/f'output/results/shap_importance_{a}.csv')
        b['rank']=b.groupby('target').mean_abs_shap.rank(ascending=False,method='min')
        baseline.append(b)
    baseline=pd.concat(baseline)
    baseline.to_csv(EVAL/'original_shap_values_and_ranks.csv',index=False)
    for i,t in enumerate(TARGETS):
        fig,axs=plt.subplots(1,2,figsize=(12,6.7),layout='constrained')
        subset=ss[ss.target.eq(t)]
        limit=(subset.mean_abs_shap+subset.sd_abs_shap).max()*1.12
        for ax,a in zip(axs,['detached','semi']):
            s=subset[subset.archetype.eq(a)].sort_values('mean_abs_shap')
            ax.barh([DISPLAY[f] for f in s.feature],s.mean_abs_shap,xerr=s.sd_abs_shap,
                    color='#467a8e' if a=='detached' else '#bb744d',capsize=2)
            ax.set_title('Detached' if a=='detached' else 'Semi-detached', fontsize=18)
            ax.set_xlabel(f'Mean absolute SHAP\n({UNITS[i]})', fontsize=17)
            ax.tick_params(axis='both', labelsize=16)
            ax.set_xlim(0,limit)
            ax.grid(axis='x',alpha=.18)
        save(fig,f'shap_{t}_repeated')
    # Beeswarms use a prespecified split, never a split selected for a clearer narrative.
    import shap as shaplib
    for a in ['detached','semi']:
        d=dataset(a).set_index('run_id')
        for i,t in enumerate(TARGETS):
            v=pd.read_csv(EVAL/a/'seed_42'/f'shap_values_{t}.csv')
            x=d.loc[v.run_id,FEATURES]
            np.random.seed(42)
            shaplib.summary_plot(v[FEATURES].to_numpy(),x.to_numpy(),feature_names=LABELS,
                                 max_display=14,show=False,plot_size=(8,6.5))
            fig=plt.gcf()
            fig.axes[0].set_xlabel(f'SHAP contribution ({UNITS[i]})')
            fig.axes[0].set_title(f'{a.capitalize()}: {TITLES[i]}\nSelected XGBoost; prespecified split 42')
            save(fig,f'{a}_beeswarm_{t}')
    for i,t in enumerate(TARGETS):
        if t not in ['T_op_peak','hours_gt26_night']:
            continue
        fig,axs=plt.subplots(1,2,figsize=(12,7))
        fig.subplots_adjust(left=.22,right=.97,bottom=.16,top=.90,wspace=1.1)
        for ax,a in zip(axs,['detached','semi']):
            v=pd.read_csv(EVAL/a/'seed_42'/f'shap_values_{t}.csv')
            x=dataset(a).set_index('run_id').loc[v.run_id,FEATURES]
            plt.sca(ax)
            shaplib.summary_plot(v[FEATURES].to_numpy(),x.to_numpy(),feature_names=LABELS,
                max_display=10,show=False,plot_size=None,color_bar=False,rng=np.random.default_rng(42))
            ax.set_title('Detached' if a=='detached' else 'Semi-detached',fontsize=18)
            ax.set_xlabel(f'SHAP contribution\n({UNITS[i]})',fontsize=17)
            ax.tick_params(axis='both',labelsize=16)
            ax.locator_params(axis='x',nbins=4)
        fig.subplots_adjust(left=.22,right=.99,bottom=.16,top=.90,wspace=1.5)
        save(fig,f'paired_beeswarm_{t}')
    performance=pd.read_csv(EVAL/'performance_summary.csv')
    perf=performance[performance.model.isin(COLORS)]
    formatted=[]
    for a in ['detached','semi']:
        fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
        for j,m in enumerate(COLORS):
            s=perf[(perf.archetype==a)&(perf.model==m)].set_index('target').loc[TARGETS]
            ax.errorbar(np.arange(5)+(j-1)*.17,s.R2_mean,yerr=s.R2_std,fmt='o',
                        color=COLORS[m],capsize=4,label=m)
        ax.set_xticks(np.arange(5),['Seasonal','Daily stepped','Peak temp.','Bedroom night','Heating'])
        ax.set_ylabel('Test R-squared (mean and SD across 5 splits)')
        ax.set_title(a.capitalize()+' | equal candidate configuration budget')
        ax.legend(); ax.grid(axis='y',alpha=.2)
        save(fig,f'{a}_repeated_performance')
        for t in TARGETS:
            row=dict(archetype=a,target=t)
            for m in COLORS:
                v=perf[(perf.archetype==a)&(perf.model==m)&(perf.target==t)].iloc[0]
                row[m]=f'{v.R2_mean:.3f} +/- {v.R2_std:.3f}'
            formatted.append(row)
    formatted=pd.DataFrame(formatted)
    formatted.to_csv(EVAL/'table_R2_mean_sd.csv',index=False)
    perm=pd.read_csv(EVAL/'permutation_importance_all.csv')
    pm=perm.groupby(['archetype','seed','model','target','feature']).normalized_mse_increase.mean().reset_index()
    pm['rank']=pm.groupby(['archetype','seed','model','target']).normalized_mse_increase.rank(ascending=False)
    pm.to_csv(EVAL/'permutation_ranks_by_split.csv',index=False)
    comparisons=[]
    for (a,s,t),g in pm.groupby(['archetype','seed','target']):
        wide=g.pivot(index='feature',columns='model',values='normalized_mse_increase')
        m=wide.MLP.nlargest(3).index
        x=wide.XGBoost.nlargest(3).index
        comparisons.append(dict(archetype=a,seed=s,target=t,
            spearman=spearmanr(wide.MLP,wide.XGBoost).statistic,top3_overlap=len(set(m)&set(x)),
            MLP_top3=', '.join(m),XGBoost_top3=', '.join(x)))
    compare=pd.DataFrame(comparisons)
    compare.to_csv(EVAL/'cross_model_importance_comparison.csv',index=False)
    pc=compare.groupby(['archetype','target']).agg(mean_spearman=('spearman','mean'),
        min_spearman=('spearman','min'),mean_top3_overlap=('top3_overlap','mean')).reset_index()
    for a in ['detached','semi']:
        fig,axs=plt.subplots(1,2,figsize=(12,6.5),layout='constrained')
        for ax,m in zip(axs,['XGBoost','MLP']):
            s=pm[(pm.archetype==a)&(pm.model==m)&(pm.target=='hours_gt26_night')]
            s=s.groupby('feature').normalized_mse_increase.agg(['mean','std']).sort_values('mean')
            ax.barh([DISPLAY[f] for f in s.index],s['mean'],xerr=s['std'],color=COLORS[m],capsize=2)
            ax.set_title(m); ax.set_xlabel('Permutation increase in normalized MSE')
            ax.axvline(0,color='grey',lw=.8)
        fig.suptitle(a.capitalize()+' | bedroom night predictive reliance, not causal effects')
        save(fig,f'{a}_night_cross_model_importance')
    ng=pd.read_csv(EVAL/'night_subgroups_all.csv')
    ns=ng.groupby(['archetype','model','subgroup']).agg(mean_n=('n','mean'),
        MAE_mean=('MAE','mean'),MAE_sd=('MAE','std'),RMSE_mean=('RMSE','mean'),
        RMSE_sd=('RMSE','std'),bias_mean=('bias','mean')).reset_index()
    ns.to_csv(EVAL/'night_subgroup_summary.csv',index=False)
    ev=pd.read_csv(EVAL/'night_event_detection_all.csv')
    es=ev.groupby(['archetype','model'])[['precision','recall','f1','balanced_accuracy','roc_auc','average_precision']].agg(['mean','std'])
    es.columns=['_'.join(c) for c in es.columns]
    es.to_csv(EVAL/'night_detection_summary.csv')
    pred=pd.read_csv(EVAL/'predictions_all.csv')
    for a in ['detached','semi']:
        fig,axs=plt.subplots(1,3,figsize=(12,4.4),layout='constrained',sharex=True,sharey=True)
        for ax,m in zip(axs,COLORS):
            s=pred[(pred.archetype==a)&(pred.seed==42)&(pred.model==m)&(pred.target=='hours_gt26_night')]
            hi=max(s.y_true.max(),s.y_pred.max())
            ax.scatter(s.y_true,s.y_pred,s=14,alpha=.45,color=COLORS[m])
            ax.plot([0,hi],[0,hi],color='black',ls='--',lw=.8)
            ax.set_title(m); ax.set_xlabel('Simulated summer night hours')
        axs[0].set_ylabel('Predicted summer night hours')
        fig.suptitle(a.capitalize()+' | prespecified split 42; negative predictions retained')
        save(fig,f'{a}_night_parity')
    audit=pd.read_csv(OUT/'audit/hourly_audit.csv')
    summary=pd.read_csv(OUT/'audit/metric_summary.csv')
    annual=audit.groupby('archetype').hours_gt26_night_annual.agg(['mean','median','max']).reset_index()
    fig,axs=plt.subplots(1,2,figsize=(10,4.6),layout='constrained')
    for ax,a in zip(axs,['detached','semi']):
        s=audit[audit.archetype==a]
        ax.scatter(s.hours_gt26_night,s.hours_gt26_night_annual,s=12,alpha=.4)
        lim=s.hours_gt26_night_annual.max()
        ax.plot([0,lim],[0,lim],'k--',lw=.8)
        ax.axhline(32,color='firebrick',ls=':',label='32 h annual reference')
        ax.set_xlabel('May-Sep bedroom night hours > 26 C')
        ax.set_ylabel('Annual bedroom night hours > 26 C')
        ax.set_title(a.capitalize()); ax.legend(fontsize=9)
    save(fig,'annual_vs_summer_night')
    # Original distribution plots corrected without overwriting archived publications.
    for a in ['detached','semi']:
        d=dataset(a)
        fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained')
        for i,(t,ax) in enumerate(zip(TARGETS,axs.flat)):
            ax.hist(d[t],bins=35,color='#467a8e',edgecolor='white',lw=.3)
            ax.axvline(d[t].median(),color='black',ls='--')
            threshold={'He_worst':3,'We_max_worst':6}.get(t)
            if threshold:
                ax.axvline(threshold,color='firebrick',ls=':')
                ax.text(.98,.92,f'Above reference: {100*d[t].gt(threshold).mean():.2f}%',
                        transform=ax.transAxes,ha='right',fontsize=10)
            ax.set_title(TITLES[i]); ax.set_xlabel(UNITS[i]); ax.set_ylabel('Simulations')
        axs.flat[-1].set_visible(False)
        fig.suptitle(a.capitalize()+' | summer proxies; reference comparisons are not compliance')
        save(fig,f'{a}_target_distributions_corrected')
    protocol=json.loads((EVAL/'protocol.json').read_text())
    trials=pd.read_csv(EVAL/'search_trials_all.csv')
    assert len(trials)==180 and trials.groupby(['archetype','seed','family']).size().eq(6).all()
    write('results_summary.md', f'''# Non-DSY revision results

Source of truth: `{ROOT}`. Original 4,000 simulation records are unchanged. All hourly records were audited before fitting. Five repeated splits are descriptive robustness checks on the same finite dataset, not five independent external validations.

## Repeated model accuracy

Mean +/- sample SD across seeds 42, 123, 202, 340 and 567. Six candidate configurations per model family per split; selected using joint normalized validation MSE only. RF/XGBoost each fit five estimators per candidate; MLP is multi-output. Equal configuration budget is not equal compute time or per-target tuning budget.

{table(formatted)}

Do not retain the old claims that MLP wins all three detached daytime targets, that XGBoost is best on night-time outcomes, or that RF defaults approach its achievable ceiling. The new experiment supersedes those single-split comparisons. No statistical-significance claim follows from the displayed mean/SD.

## Night-time errors

The tail is defined before testing from the 90th percentile of positive training outcomes. Predictions are not clipped or rounded. Empty or constant subgroups have undefined R-squared. The >32h subgroup is too sparse for a reliable compliance classifier.

{table(ns[ns.subgroup.isin(['nonzero','positive_training_p90_tail'])])}

Event detection uses regression output as a score, with a cut-off selected by validation balanced accuracy. It is exploratory discrimination of any nonzero summer hours, not calibrated probability or TM59 compliance.

{table(es.reset_index())}

## XGBoost and MLP interpretation agreement

Both models use the same held-out permutation-MSE measure for this comparison. This is not MLP SHAP and does not establish matching directions. Feature dependence and the sampled distribution affect both methods.

{table(pc)}

Full SHAP values, ranks and cross-split ranges: `../evaluation/shap_mean_values_and_ranks.csv`. Every SHAP figure uses explicit target units. Split-42 beeswarms are prespecified examples; global conclusions use all five splits. Individual panels should be placed at readable full-column/full-page width, not compressed into five tiny subplots.

## Audit results

{table(summary)}

Annual bedroom night diagnostic (not a newly trained target):

{table(annual)}

## Reproducibility

Hardware for the new experiment: {protocol['processor']}; {protocol['machine']}. Versions, search spaces, sampled candidates and input hashes are in `../evaluation/protocol.json`. All 180 trials have recorded durations and selection scores. This hardware report does not prove which machine ran the original EnergyPlus campaign. Single-sample timings are exploratory CPU timings during concurrent training, not a controlled speed benchmark.
''')
    write('shap_table.md','# Mean absolute SHAP values and ranks\n\nFive selected XGBoost models per archetype. Rank of mean is distinct from mean rank.\n\n'+table(ss))
    print(f'Generated reports and {len(list(FIG.glob("*.png")))} figure pairs in {OUT}',flush=True)

if __name__=='__main__':
    main()
