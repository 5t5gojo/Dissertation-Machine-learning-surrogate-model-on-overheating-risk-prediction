"""Create a separate conference revision and evidence-linked reviewer response."""
from copy import deepcopy
import json
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pandas as pd
from revision_common import ROOT, OUT, TARGETS, sha

SOURCE = Path('/Users/hlbao/Desktop/bso/p129v1.docx')

def replace(p, text):
    fmt=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    p.clear()
    r=p.add_run(text)
    if fmt is not None:
        r._r.insert(0,fmt)
    r.bold=False

def main():
    dest=OUT/'paper'
    dest.mkdir(parents=True,exist_ok=True)
    ev=OUT/'evaluation'
    fig=OUT/'figures'
    perf=pd.read_csv(ev/'performance_summary.csv').set_index(['archetype','target','model'])
    def score(a,t,m):
        r=perf.loc[(a,t,m)]
        return f'{r.R2_mean:.3f} ± {r.R2_std:.3f}'
    ranks=pd.read_csv(ev/'shap_mean_values_and_ranks.csv').set_index(['archetype','target','feature'])
    def rank(a,t,f): return int(ranks.loc[(a,t,f),'rank_of_mean'])
    def importance(a,t,f): return f'{ranks.loc[(a,t,f),"mean_abs_shap"]:.3f}'
    d=Document(SOURCE)
    p=d.paragraphs
    assert p[8].text.startswith('Summertime overheating') and p[53].text.startswith('This paper developed')
    replacements={
8: 'This study develops simulation-based surrogates for summertime thermal screening and ideal heating demand in UK detached and semi-detached houses. A 14-parameter EnergyPlus workflow generated 2,000 samples per archetype under London TMYx 2009–2023. This typical-year dataset contains no Criterion-1-proxy reference exceedances and only two Criterion-3-active cases; the models are not validated for severe-weather or regulatory compliance assessment. Random Forest, XGBoost and a multi-output MLP were evaluated over five repeated 70/15/15 splits, with six candidate configurations per algorithm and validation-only selection. XGBoost achieved mean peak-temperature R² of 0.970 and 0.960 for detached and semi-detached houses respectively; MLP achieved heating-demand R² of 0.972 and 0.939. Night-time performance was less stable, and no universal algorithm winner is claimed. SHAP and cross-model permutation analyses identify glazing-related features as important predictors, with window opening factor more prominent for semi-detached night-time outcomes. These are model-specific associations under the sampled assumptions. An hourly audit confirms zero C1 occupied-hours offset but finds that annual bedroom night counts differ from the trained summer proxy. The workflow supports exploration within this simulation domain; DSY and monitored-data validation remain outstanding.',
19: 'Simulation setup. EnergyPlus v25.1 (U.S. Department of Energy, 2025) was executed through a Python batch runner using the London St James’s Park TMYx 2009–2023 file (maximum summer dry-bulb temperature 31.0°C). Simulations cover one year at a 15-minute timestep with hourly reporting. IdealLoadsAirSystem heating uses 21°C day / 18°C night setpoints, and the output is interpreted as ideal heating demand rather than delivered energy. Active cooling is disabled; all audited cooling-energy outputs are zero, although heating remains available. Ground heat transfer uses Foundation:Kiva. This is a typical-year modelling experiment, not an overheating compliance assessment.',
20: 'Archetypes. Both models have ground-floor living, first-floor bedroom and unoccupied attic zones, developed in OpenStudio (Figure 2), with a fixed masonry-based construction including a 200 mm brick layer. The detached model has 15 windows and one door. External overhang projection depth is sampled; eight natural-ventilation openings use a 24°C indoor minimum and 10°C outdoor minimum, with a 10 m/s wind-speed limit. No occupancy, noise or security restriction is imposed, and the temperature-difference setting does not require outdoor air to be cooler than indoor air. The semi-detached model changes one lateral facade to adiabatic on both occupied floors, removes its windows, overhangs and ventilation openings, and reduces the exposed ground perimeter fraction from 1.0 to 0.75. These simultaneous changes prevent attribution to any one factor. Realised WWR can be clipped by geometry. SAP 2012 determines household size, split equally between the occupied zones; the template’s NECB-G-Occupancy schedule supplies time variation and is not a validated UK room-specific occupancy profile.',
23: 'Parameter space and sampling. Fourteen continuous parameters (Table 1) were sampled using uniform marginal Latin Hypercube Sampling with seed 42, yielding the same 2,000 input vectors for each archetype. The ranges support exploration of geometry, envelope and operation assumptions, informed by comparable studies (Symonds et al., 2016; Botti et al., 2022; Lawrence et al., 2021). They are not a probability model of the housing stock: independently varied materials, glazing and operation can create combinations uncommon in actual dwellings. Python derives geometry, opening areas, headcounts and infiltration coefficients before running EnergyPlus with eight parallel workers. All 4,000 runs completed successfully. The previously stated 28-minute batch timing is omitted because retained records do not establish the original timing and hardware together.',
25: 'Target variables. The five targets represent four overheating-related screening outcomes and annual ideal heating demand (Table 2). The adaptive limit is Tmax = 0.33Trm + 21.8°C, with a running-mean coefficient of 0.8. He,worst counts raw operative-temperature exceedances ΔT ≥1 K over May–September, divided by occupied summer hours. An audit of every generated IDF establishes that both zones have positive scheduled occupancy throughout: the minimum schedule fraction is 0.3. Therefore occupied and all-summer denominators coincide at 3,672 hours, with zero offset for every case. This is a consequence of the implemented schedules, not evidence of realistic occupancy. We,max,worst is the stepped daily proxy in Equation (1), and Top,peak is the maximum operative temperature over all summer hours, not a daytime-only measure. The bedroom target counts summer hours above 26°C in zone 102 from 22:00 to 07:00. Annual night counts are reported separately because TM59 (2017) uses an annual basis. Heating demand is summed across both occupied zones and divided by their combined floor area.',
26: 'All overheating outputs remain screening proxies under the specified weather, schedules and zone aggregation. The hourly CSV explicitly labels the beginning of each interval; 22:00–07:00 therefore comprises nine bins per night. Reference exceedances use strict >3% and >6 comparisons, and >32 h is reported only with its assessment period specified. A C3-like diagnostic counts summer hours with ΔT >4 K. A two-of-three proxy flag is evaluated within each zone before aggregating to the dwelling; it is not a formal TM52 outcome. The study does not establish compliance under TM52 or TM59.',
28: 'Model training and evaluation. Each archetype was evaluated using split seeds 42, 123, 202, 340 and 567, with 1,400 training, 300 validation and 300 test rows per split. Identical partitions were used for all algorithms. Each family received six candidate pipeline configurations: the original setting plus five reproducibly sampled alternatives. Selection minimized mean validation MSE normalized by training-target variance across the five outputs. RF and XGBoost fit five separate regressors with a shared candidate configuration; MLP is multi-output. Thus the budget is equal in candidate configurations, not estimator count or computation time. RF searches tree count, feature fraction, depth and leaf size; XGBoost searches tree count, learning rate, depth, sampling and regularisation; MLP searches architecture, dropout, learning rate, weight decay and batch size. MLP scalers use training rows only, with Adam, up to 300 epochs and validation early stopping (patience 30). All 180 trials, configurations, timings and split assignments are retained. Held-out metrics are reported as mean ± sample SD over five splits, not independent confidence intervals. The original dataset had already been examined, so this is repeated internal evaluation, not external validation.',
29: 'Sensitivity and night-time diagnostics. Exact tree SHAP contributions (Lundberg and Lee, 2017) were computed for each selected XGBoost model using its native TreeSHAP interface, with additivity checked against predictions. Global values and rank ranges span all five splits; beeswarms use the prespecified split 42. XGBoost supports exact tree explanations but is not claimed to be the best model for every target. MLP and XGBoost rankings were also compared using the same held-out permutation-MSE measure, with five permutations per feature. For night-time outcomes, evaluation additionally separates zero, nonzero and high-tail cases; the tail cut-off is the 90th percentile of positive training values. All-zero and training-mean baselines are included. Nonzero-event detection uses a validation-selected regression-score cut-off and test precision, recall, balanced accuracy and AUROC. This is neither a calibrated probability model nor a compliance classifier.',
31: 'Simulation dataset. All five canonical targets were reproduced from the 4,000 saved hourly outputs. Detached medians are He =0.22%, We =10.0, peak temperature =29.94°C and heating demand =78.20 kWh/m²·yr; corresponding semi-detached medians are 0.11%, 6.0, 29.60°C and 55.10 kWh/m²·yr. No case exceeds the C1 proxy reference, while 67.15% and 47.10% exceed We >6. The old 72.8% and 52.9% rates counted values equal to six and have been corrected. Two detached cases have both C2 and C3 proxy flags in the same bedroom zone; no semi-detached case does. Summer night counts have median zero and zero fraction 56.6% in both archetypes, but mean values are 0.9335 and 1.1750 h respectively. The annual diagnostic differs in 99 detached and 93 semi-detached cases: annual means are 1.582 and 1.866 h, and 15 and 16 cases exceed 32 h, compared with three and zero under the summer-only definition. Annual counts are not surrogate training targets.',
32: f'Model accuracy. Table 3 replaces the original single-split ranking with repeated evaluation after a modest equal-configuration search. For detached houses, MLP leads on He ({score("detached","He_worst","MLP")}) and heating demand ({score("detached","heat_kWh_m2","MLP")}), while XGBoost leads on peak temperature ({score("detached","T_op_peak","XGBoost")}). Mean daily-proxy R² is approximately 0.946 for both. In semi-detached houses, XGBoost has higher mean R² on the three seasonal/peak indicators, while MLP leads on heating demand. RF remains below these models on mean performance but improves with tuning; no claim about an inherent RF performance ceiling is made. For summer bedroom night hours, MLP and XGBoost achieve {score("detached","hours_gt26_night","MLP")} and {score("detached","hours_gt26_night","XGBoost")} in detached houses, and {score("semi","hours_gt26_night","MLP")} and {score("semi","hours_gt26_night","XGBoost")} in semi-detached houses. MLP exceeds XGBoost on three of five night-time splits in each archetype, so a stable night-time winner is not established.',
33: 'Table 3: Held-out R², mean ± sample SD over five repeated splits after equal candidate-configuration search. No bold winner is assigned; variability and paired differences inform interpretation.',
34: 'Night-time prediction quality. R² is supplemented by errors conditional on nonzero outcomes and by high-tail diagnostics. For nonzero detached test cases, mean RMSE across splits is 2.36 h for XGBoost and 2.37 h for MLP, versus 4.48 h for an all-zero predictor. For semi-detached cases, the corresponding values are 1.82, 1.74 and 4.01 h. Thus the models capture information beyond predicting zeros, but both tend to underpredict positive outcomes and remain uncertain in the sparse tail. Full MAE/RMSE, subgroup counts, event-detection metrics, baselines and per-run predictions are retained in the revision supplement. These internal diagnostics do not validate predictions of rare severe overheating under other weather conditions.',
35: f'Global feature importance. Figures 3 and 4 show readable paired panels for peak temperature and summer bedroom night hours; the supplementary SHAP table gives all five targets, all 14 features, mean absolute values and rank ranges. In the new five-split mean ranking, orientation moves from position {rank("detached","He_worst","orientation")} to {rank("semi","He_worst","orientation")} for He, and from {rank("detached","T_op_peak","orientation")} to {rank("semi","T_op_peak","orientation")} for peak temperature. These supersede the erroneous tenth-to-fifth and eighth-to-fourth claims. The original saved single-split CSVs instead give twelfth-to-fourth and eleventh-to-third, which must not be mixed with the revised experiment. Rankings describe model reliance within the independent LHS design distribution and are not isolated causal effects.',
37: 'Figure 3: Peak-temperature SHAP importance for detached (left) and semi-detached (right) houses. Bars show mean absolute contributions across five held-out splits; whiskers show SD. Units are °C.',
39: 'Figure 4: Summer bedroom night SHAP importance for detached (left) and semi-detached (right) houses. Bars show five-split means; whiskers show SD. Units are hours.',
40: 'Seasonal and peak-temperature predictors. WWR and g-value are leading XGBoost features for the seasonal and peak-temperature targets, with orientation more prominent in the semi-detached model. Figure 5 illustrates the signed contributions for a prespecified split. The physical hypothesis is that glazing-related solar gains and facade exposure contribute to these associations. SHAP does not independently establish that increasing a particular feature causes the predicted change, and orientation is circular rather than a monotonic exposure scale. The phrase daytime mechanism is avoided because the targets include all summer hours.',
42: 'Figure 5: Peak-temperature beeswarms for the prespecified split 42: detached (left), semi-detached (right). Colour denotes feature value and the horizontal axis is the model contribution in °C. These are XGBoost explanations.',
43: f'Night-time predictors. Across the five XGBoost fits, detached mean absolute SHAP is highest for g-value ({importance("detached","hours_gt26_night","g_value")} h), followed by window U-factor ({importance("detached","hours_gt26_night","u_windows")} h) and opening factor ({importance("detached","hours_gt26_night","wof")} h). In the semi-detached model, opening factor ranks first ({importance("semi","hours_gt26_night","wof")} h), followed by g-value ({importance("semi","hours_gt26_night","g_value")} h) and window U-factor ({importance("semi","hours_gt26_night","u_windows")} h). The XGBoost/MLP permutation-rank correlation averages 0.83 and 0.92 for detached and semi-detached outcomes; the semi-detached top three are opening factor, g-value and U-factor in both models for all five splits. Detached lower rankings differ by explanation method, particularly WWR versus opening factor. These checks support the broad predictive contrast but not identical rankings or a uniquely identified ventilation mechanism. Facade exposure, openings and ground perimeter change together, and unconstrained opening assumptions limit behavioural interpretation.',
45: 'Figure 6: Summer bedroom night beeswarms for split 42: detached (left), semi-detached (right). Contributions are in hours. Cross-model permutation results support broad predictive associations, not unique causal attribution.',
47: 'Performance in context. The repeated experiment shows that model ranking depends on the target and split. Cross-study R² values are not directly comparable because weather, target variance, parameter ranges and evaluation designs differ (Symonds et al., 2016; Botti et al., 2022; Lawrence et al., 2021). This study therefore reports an internally controlled comparison rather than superiority over previous surrogates. The six-configuration search is small and may favour some algorithms; equal candidate counts do not eliminate differences in model capacity or optimisation cost. Overlapping repeated splits support descriptive robustness checks but not a definitive significance claim.',
48: 'Climate boundary. The London TMYx dataset covers a typical-year response domain with sparse seasonal proxy exceedances; it does not establish performance under DSY or future heat extremes. No DSY file was available for this revision, so the climate-coverage concern remains unresolved. Zero C1 reference exceedances are not due to an occupied-hours denominator offset under the implemented schedules, but the schedule assumptions themselves remain restrictive. The annual night audit also shows why summer-only counts must not be presented as annual TM59 outcomes. Alternative climates require new simulations and retraining or independently demonstrated transfer validity. Surrogates accelerate subsequent predictions only after those climate-specific datasets have been generated.',
49: 'Model and sampling limitations. Two simplified masonry-based archetypes do not span terraced houses, flats or lightweight construction. The building models have not been validated against monitored temperatures or an independent benchmark; reproducing saved targets is a computational consistency check, not physical validation. SAP headcounts and NECB-named schedules do not reproduce actual UK room-use patterns. Window opening is unconstrained by occupancy, security, noise or occupant preference and can occur without a cooler-outdoor-air condition. Independent uniform marginals may generate uncommon combinations and should not be interpreted as housing-stock prevalence. WWR clipping, zone aggregation, proxy definitions and the limited search budget further restrict generalisation. Annual bedroom counts require a separately trained target if predictive annual assessment is intended.',
50: 'Potential stock-level workflow. A future deployment could use a surrogate to prioritize designs for detailed assessment after mapping real dwelling attributes to the model domain and screening for unsupported combinations. Stock distributions and parameter dependencies would need to be represented explicitly, and the chosen weather must match the intended application. Within-domain interpolation alone does not validate stock-level risk estimates. High-priority cases should undergo detailed simulation, survey and monitored validation before operational decisions. This is a proposed application pathway, not a demonstrated population screening service.',
51: 'Interpretation boundary. Lower median seasonal proxies and heating demand in the semi-detached sample describe the combined archetype modifications. They do not show that a party wall alone reduces overall thermal exposure: mean night counts are higher in the semi-detached dataset, including on the annual diagnostic. An intervention study changing facade exposure, openings and ground coupling separately would be required to distinguish their effects. SHAP and permutation importance instead quantify how the fitted models use the available features within the sampled design distribution.',
53: 'The study provides a documented simulation-to-surrogate workflow for two UK dwelling archetypes under a London TMYx baseline. An audit of 4,000 hourly runs corrected C2 reference comparisons, confirmed zero occupied-hours offset under the implemented schedules, identified two same-zone C2/C3 proxy cases, and distinguished summer from annual bedroom night counts. Repeated equal-configuration evaluation replaces the single-split algorithm ranking: XGBoost predicts peak temperature well in both archetypes, MLP is strongest on heating demand, and summer night-time performance remains less stable. SHAP and permutation checks retain a broad cross-archetype contrast in predictive feature importance, without establishing a unique causal mechanism. Results support exploration of this simulation domain, not severe-weather, stock-wide or regulatory compliance claims.',
54: 'Future work. Priorities are paired DSY simulations using the same input vectors, validation of building models against benchmark or monitored data, and assessment under realistic room-specific occupancy and opening constraints. Controlled changes to facade exposure, ventilation and ground coupling would help test the proposed mechanisms. Additional archetypes and stock-informed joint parameter distributions are required before population-level use. These extensions have not been completed in this revision.',
56: 'Simulation templates, parameter configurations, scripts and original outputs are retained in the project repository [link withheld for review]. The local revision supplement adds hourly audit records, all search trials, repeated test predictions, full SHAP tables and diagnostic figures. These materials should accompany the revised submission; publication of the new supplement remains an author action.'
    }
    replacements[23]=replacements[23].replace(' The previously stated 28-minute batch timing is omitted because retained records do not establish the original timing and hardware together.','')
    replacements[31]=replacements[31].replace(' The old 72.8% and 52.9% rates counted values equal to six and have been corrected.','')
    replacements[32]=replacements[32].replace('Table 3 replaces the original single-split ranking with repeated evaluation after a modest equal-configuration search.', 'Table 3 reports repeated evaluation after a modest equal-configuration search.')
    start=replacements[35].index(' These supersede')
    end=replacements[35].index(' Rankings describe')
    replacements[35]=replacements[35][:start]+replacements[35][end:]
    replacements[35]=replacements[35].replace('readable paired panels','paired panels')
    replacements[40]=replacements[40].replace(' The phrase daytime mechanism is avoided because the targets include all summer hours.','')
    replacements[56]='Simulation templates, parameter configurations, scripts and original outputs are retained in the project repository [link withheld for review]. The supplementary material reports hourly audit records, search configurations, repeated evaluation, full SHAP values and diagnostic figures.'
    replacements[42]='Figure 5: Peak-temperature beeswarms for split 42, showing ten leading features: detached (left), semi-detached (right). Blue denotes low feature values and red denotes high values. The horizontal axis is the XGBoost contribution in °C.'
    replacements[45]='Figure 6: Summer bedroom night beeswarms for split 42, showing ten leading features: detached (left), semi-detached (right). Blue denotes low feature values and red denotes high values; contributions are in hours. These describe predictive associations, not causal effects.'
    replacements[14]=p[14].text.replace('continuous TM52/TM59-derived overheating indicators', 'TM52/TM59-informed overheating screening indicators')
    for i,text in replacements.items(): replace(p[i],text)
    # Replace the invalid equation row with an independent numbered paragraph.
    target_table=d.tables[1]
    target_table._tbl.remove(target_table.rows[-1]._tr)
    target_table.cell(1,2).text='May–September occupied-hour exceedance (ΔT ≥1 K); all hours occupied under the implemented schedule'
    target_table.cell(2,1).text='K h (proxy)'
    target_table.cell(4,2).text='SUMMER bedroom hours >26°C, 22:00–07:00; annual counts reported separately'
    eq=d.add_paragraph('W_d,z = Σᵢ∈d∩S∩O_z rint[max(T_op,z,i − T_max,i, 0)] Δtᵢ;   W_e,max,worst = max_z max_d W_d,z.     (1)')
    eq.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for run in eq.runs: run.font.size=Pt(9)
    target_table._tbl.addnext(eq._p)
    note=d.add_paragraph('Here S is May–September, O_z is the set of occupied intervals, and Δtᵢ =1 h. rint rounds to the nearest integer with ties to even; the quantity is retained as a stepped proxy rather than a formal compliance result.')
    eq._p.addnext(note._p)
    performance_table=d.tables[2]
    for j,a in enumerate(['detached','semi']):
        for k,t in enumerate(TARGETS):
            row=performance_table.rows[1+j*5+k]
            for c,m in zip(row.cells[2:],['RF','XGBoost','MLP']):
                c.text=score(a,t,m)
                for para in c.paragraphs:
                    for r in para.runs:
                        r.font.size=Pt(9); r.bold=False
    for i,name in [(36,'shap_T_op_peak_repeated.png'),(38,'shap_hours_gt26_night_repeated.png')]:
        p[i].clear(); p[i].alignment=WD_ALIGN_PARAGRAPH.CENTER
        p[i].add_run().add_picture(str(fig/name),width=Inches(6.1))
    for i,t in [(41,'T_op_peak'),(44,'hours_gt26_night')]:
        p[i].clear(); p[i].alignment=WD_ALIGN_PARAGRAPH.CENTER
        p[i].add_run().add_picture(str(fig/f'paired_beeswarm_{t}.png'),width=Inches(6.1))
    cap=d.add_paragraph('Table 4: Selected five-split mean absolute SHAP values, with rank of the mean in parentheses. Full values and rank ranges are provided in the supplement.')
    cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.keep_with_next=True
    p[39]._p.addnext(cap._p)
    st=d.add_table(rows=1, cols=4)
    st.autofit=False
    for c,text in zip(st.rows[0].cells,['Target (unit)','Feature','Detached','Semi-detached']): c.text=text
    for t,fs in [('T_op_peak',['wwr','g_value','fixedShadingDepth','orientation']),
                 ('hours_gt26_night',['g_value','u_windows','wof'])]:
        for f in fs:
            cells=st.add_row().cells
            names={'wwr':'WWR','g_value':'g-value','fixedShadingDepth':'Overhang depth','orientation':'Orientation',
                   'u_windows':'Window U-factor','wof':'Window opening factor'}
            texts=['Peak temperature (°C)' if t=='T_op_peak' else 'Summer night (h)',names[f],
                   f'{importance("detached",t,f)} ({rank("detached",t,f)})',
                   f'{importance("semi",t,f)} ({rank("semi",t,f)})']
            for c,text in zip(cells,texts): c.text=text
    for row in st.rows:
        for c in row.cells:
            c.width=Inches(1.53)
            for para in c.paragraphs:
                para.paragraph_format.space_after=Pt(3)
                para.paragraph_format.space_before=Pt(3)
                for run in para.runs: run.font.size=Pt(9)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','bottom','left','right','insideH','insideV']:
        e=OxmlElement('w:'+side); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
    st._tbl.tblPr.append(borders)
    for c in st.rows[0].cells:
        fill=OxmlElement('w:shd'); fill.set(qn('w:fill'),'EEEEEE'); c._tc.get_or_add_tcPr().append(fill)
        for run in c.paragraphs[0].runs: run.bold=True
    cap._p.addnext(st._tbl)
    # Keep each figure and its caption together, without chaining full results sections.
    for i in [17,21,36,38,41,44]: p[i].paragraph_format.keep_with_next=True
    output=dest/'p129v1_revised_no_DSY.docx'
    d.save(output)
    text='\n\n'.join(f'## Replacement paragraph {i}\n\n{text}' for i,text in replacements.items())
    (OUT/'reports/manuscript_replacements.md').write_text('# Evidence-based manuscript replacements\n\n'+text+'\n')
    (dest/'source_manifest.json').write_text(json.dumps({'original_docx':str(SOURCE),'original_sha256':sha(SOURCE),
        'revised_docx':str(output),'revision_data_protocol':str(ev/'protocol.json')},indent=2))
    print(output)

if __name__=='__main__':
    main()
