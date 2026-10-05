"""Cross-check saved revision artifacts independently of the training loop."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from revision_common import ROOT, OUT, TARGETS, FEATURES, dataset, data_path, sha

def main():
    e=OUT/'evaluation'
    manifest=json.loads((OUT/'audit/manifest.json').read_text())
    assert all(sha(data_path(a))==manifest['data_sha256'][a] for a in ['detached','semi'])
    np.testing.assert_allclose(dataset('detached')[FEATURES],dataset('semi')[FEATURES],atol=1e-12)
    audit=pd.read_csv(OUT/'audit/hourly_audit.csv')
    assert len(audit)==4000 and audit.status.eq('ok').all()
    assert audit.filter(like='canonical_difference_').abs().max().max()<1e-6
    protocol=json.loads((e/'protocol.json').read_text())
    trials=pd.read_csv(e/'search_trials_all.csv')
    assert len(trials)==180
    for (a,s,m),g in trials.groupby(['archetype','seed','family']):
        assert len(g)==6
        selected=json.loads((e/a/f'seed_{s}'/f'{m}_selected.json').read_text())
        assert selected['candidate']==g.loc[g.normalized_val_mse.idxmin(),'candidate']
    for a in ['detached','semi']:
        for s in protocol['seeds']:
            split=pd.read_csv(e/a/f'seed_{s}'/'split.csv')
            assert split.run_id.is_unique and len(split)==2000
            assert split.split.value_counts().to_dict()=={'train':1400,'validation':300,'test':300}
    pred=pd.read_csv(e/'predictions_all.csv')
    perf=pd.read_csv(e/'performance_all.csv').set_index(['archetype','seed','model','target'])
    assert len(pred)==45000
    for (a,s,m,t),g in pred.groupby(['archetype','seed','model','target']):
        assert len(g)==300 and g.run_id.is_unique
        source=dataset(a).set_index('run_id').loc[g.run_id,t].to_numpy()
        np.testing.assert_allclose(source,g.y_true)
        splits=pd.read_csv(e/a/f'seed_{s}'/'split.csv').set_index('run_id')
        assert splits.loc[g.run_id,'split'].eq('test').all()
        actual=[r2_score(g.y_true,g.y_pred),mean_absolute_error(g.y_true,g.y_pred),mean_squared_error(g.y_true,g.y_pred)**.5]
        np.testing.assert_allclose(actual,perf.loc[(a,s,m,t),['R2','MAE','RMSE']].to_numpy(float),atol=1e-8)
    ranks=pd.read_csv(e/'shap_mean_values_and_ranks.csv')
    assert len(ranks)==140 and not ranks[['archetype','target','feature']].duplicated().any()
    source_manifest=json.loads((OUT/'paper/source_manifest.json').read_text())
    assert sha(source_manifest['original_docx'])==source_manifest['original_sha256']
    print('PASS: 4,000 audited records; unchanged source hashes; matched archetype inputs; 180 trials; 10 disjoint partitions; 45,000 predictions; 150 recomputed metric rows; 140 SHAP table rows; original manuscript unchanged.')

if __name__=='__main__': main()
