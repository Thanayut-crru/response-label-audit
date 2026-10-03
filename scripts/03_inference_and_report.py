"""Generate paired uncertainty, explicit claim boundaries, figures, and manuscript draft."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import ROOT, CONFIG, start_run, complete, dump, bootstrap_paired, interval, holm, markdown

def paired_row(a,b,rng,block=1,family_size=4):
    iterations=CONFIG['inference']['bootstrap_iterations']
    diff,rel=bootstrap_paired(a,b,iterations,rng,block)
    observed=float(np.mean(a)-np.mean(b))
    lo,hi=interval(diff)
    rel_lo,rel_hi=interval(rel)
    eqlo,eqhi=interval(rel,.1)
    familylo,familyhi=interval(rel,.1/family_size)
    simultaneouslo,simultaneoushi=interval(diff,.05/family_size)
    denominator=float(np.mean(a))
    rawp=float((1+np.sum(np.abs(diff-observed)>=abs(observed)))/(iterations+1))
    row={'loss_difference_baseline_minus_rdfl':observed,'ci95_low':lo,'ci95_high':hi,
         'family_ci_low':simultaneouslo,'family_ci_high':simultaneoushi,'raw_p':rawp,
         'relative_improvement':observed/denominator if denominator>1e-15 else np.nan,
         'relative_ci95_low':rel_lo,'relative_ci95_high':rel_hi,
         'relative_ci90_low':eqlo,'relative_ci90_high':eqhi,
         'relative_family_equivalence_ci_low':familylo,'relative_family_equivalence_ci_high':familyhi}
    for margin in [.01,.02,.05]:
        tag=str(int(100*margin))+'pct'
        row['equivalent_'+tag]=bool(eqlo is not None and eqlo>-margin and eqhi<margin)
        row['family_equivalent_'+tag]=bool(familylo is not None and familylo>-margin and familyhi<margin)
    return row

def empirical(frame,label,out,rng):
    if frame.duplicated(['Date','Symbol','method']).any():
        raise ValueError('Duplicate unit-method rows; inference would pseudo-replicate')
    if frame.groupby(['Date','Symbol']).actual.nunique().max()!=1:
        raise ValueError('Different outcomes across methods')
    if (pd.to_datetime(frame.train_end)>=pd.to_datetime(frame.Date)).any():
        raise ValueError('Training date reaches prediction date')
    if 'calibration_history_ends_before' in frame:
        if (pd.to_datetime(frame.calibration_history_ends_before)>pd.to_datetime(frame.Date)).any():
            raise ValueError('Future calibration cutoff')
    wide=frame.pivot(index=['Date','Symbol'],columns='method',values='loss')
    if wide.isna().any().any():
        raise ValueError('Methods must share the exact same evaluation mask')
    daily=wide.groupby(level='Date').mean().sort_index()
    summary=frame.groupby('method').agg(n=('loss','size'),stock_day_mean_loss=('loss','mean'))
    summary['equal_date_mean_loss']=daily.mean()
    summary.to_csv(out/f'{label}_metrics.csv')
    records=[]
    competitors=[c for c in wide.columns if c!='RDFL_SOFT']
    for length in CONFIG['inference']['block_lengths']:
        group=[]
        for competitor in competitors:
            row=paired_row(daily[competitor].to_numpy(),daily.RDFL_SOFT.to_numpy(),rng,length,len(competitors))
            row.update(dataset=label,competitor=competitor,block_length=length,n_dates=len(daily),n_stock_days=len(wide),
                       status='EXPLORATORY',equal_date_weighting=True)
            group.append(row)
        for r,p in zip(group,holm([r['raw_p'] for r in group])):
            r['holm_p']=float(p)
            r['interpretation']=('RDFL_LOWER_LOSS' if r['loss_difference_baseline_minus_rdfl']>0 else 'RDFL_HIGHER_LOSS') if p<.05 else 'NO_DETECTED_DIFFERENCE'
            r['equivalence_2pct_family']=r['family_equivalent_2pct']
        records+=group
    result=pd.DataFrame(records)
    result.to_csv(out/f'{label}_paired_inference.csv',index=False)
    slices=[]
    for dimension in ['Symbol','block']:
        for name,sub in frame.groupby(dimension):
            w=sub.pivot(index=['Date','Symbol'],columns='method',values='loss').groupby(level='Date').mean()
            for c in competitors:
                d=float(w[c].mean()-w.RDFL_SOFT.mean())
                slices.append({'dimension':dimension,'group':name,'competitor':c,'loss_difference':d,'n_dates':len(w),
                               'status':'DESCRIPTIVE_NOT_INDEPENDENT_TEST'})
    pd.DataFrame(slices).to_csv(out/f'{label}_slices.csv',index=False)
    return result

def main():
    for name in ['simulation','purged_pilot']:
        if not (ROOT/'results'/name/'COMPLETE.json').exists():
            raise RuntimeError(f'{name} is incomplete; do not generate a completed research report')
    out=start_run('report')
    rng=np.random.default_rng(CONFIG['inference']['seed'])
    sim=pd.read_csv(ROOT/'results/simulation/replication_metrics.csv')
    diag=pd.read_csv(ROOT/'results/simulation/absence_diagnostics.csv')
    pair=[]
    family=sim.scenario.nunique()*2
    for scenario,group in sim.groupby('scenario'):
        wide=group.pivot(index='seed',columns='method',values='latent_mse')
        for competitor in ['DIRECT','ZERO']:
            r=paired_row(wide[competitor].to_numpy(),wide.RDFL_SOFT.to_numpy(),rng,1,family)
            r.update(scenario=scenario,competitor=competitor,replications=len(wide))
            pair.append(r)
    for row,p in zip(pair,holm([r['raw_p'] for r in pair])):
        row['holm_p']=float(p)
    simpair=pd.DataFrame(pair)
    simpair.to_csv(out/'simulation_paired_inference.csv',index=False)
    ds=[]
    for (scenario,threshold),g in diag.groupby(['scenario','threshold_definition']):
        values=g.weighted_component_absence_error.to_numpy()
        boot=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(axis=1)
        lo,hi=interval(boot)
        ds.append({'scenario':scenario,'threshold':threshold,'component_error':float(values.mean()),
                   'ci95_low':lo,'ci95_high':hi,'net_error':float(g.weighted_net_absence_error.mean()),
                   'component_prevalence':float(g.component_prevalence.mean()),
                   'weight_mass_mean':float(g.low_response_weight_mass.mean()),
                   'hard_low_count_mean':float(g.hard_low_response_count.mean()),
                   'retained_fraction':float(g.retained_fraction.mean()),'replications':len(g)})
    diagnostic=pd.DataFrame(ds)
    diagnostic.to_csv(out/'absence_summary.csv',index=False)
    historical=pd.read_csv(ROOT/'provenance/historical/p2c_forward_calibration/calibrated_predictions.csv')
    historical['loss']=((historical.actual-historical.calibrated_prediction)/historical.stock_training_scale)**2
    if not np.allclose(historical.loss,historical.calibrated_normalized_squared_error):
        raise ValueError('Historical loss does not reproduce its prediction columns')
    old=empirical(historical,'historical_p2c',out,rng)
    fresh=pd.read_csv(ROOT/'results/purged_pilot/predictions.csv')
    fresh['loss']=((fresh.actual-fresh.prediction)/fresh.stock_training_scale)**2
    if not np.allclose(fresh.loss,fresh.normalized_squared_error):
        raise ValueError('Fresh loss mismatch')
    new=empirical(fresh,'purged_pilot',out,rng)

    legacy=pd.read_csv(ROOT/'provenance/historical/p3_known_truth_simulation/replication_metrics.csv')
    oldrate=float(legacy.loc[(legacy.scenario=='cancellation')&(legacy.method=='RDFL_SOFT'),'false_causal_absence'].mean())
    definitions={'legacy_cancellation_rate':oldrate,
        'denominator':'sum of confidence times soft LOW_RESPONSE probability over selected training observations',
        'threshold':'0.35 * SD(latent net training effect)',
        'not':'held-out error, proportion of all cases, or proof that multiple semantic teachers fail',
        'historical_results_metrics_used':False,
        'real_confirmatory_status':'BLOCKED: timestamps, official calendar, price adjustment, near-duplicate events',
        'margin_status':'retrospectively chosen sensitivity parameter; not a journal standard'}
    dump(out/'claim_audit.json',definitions)

    fixed=diagnostic[diagnostic.threshold=='fixed_0.35'].set_index('scenario')
    ordered=list(fixed.index)
    fig,ax=plt.subplots(figsize=(10,5))
    ax.errorbar(np.arange(len(ordered)),fixed.component_error,
                yerr=[fixed.component_error-fixed.ci95_low,fixed.ci95_high-fixed.component_error],
                fmt='o',capsize=3,label='Weighted component-absence error (95% CI)')
    ax.plot(np.arange(len(ordered)),fixed.component_prevalence,'x',label='Component prevalence in training population')
    ax.set_xticks(np.arange(len(ordered)),ordered,rotation=35,ha='right')
    ax.set_ylabel('Fraction'); ax.set_ylim(-.03,1.03)
    ax.set_title('RDFL low-response labels; fixed component threshold = 0.35')
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(out/'absence_fixed_threshold.png',dpi=220)
    fig.savefig(out/'absence_fixed_threshold.pdf'); plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,4))
    primary=new[new.block_length==20].reset_index(drop=True)
    y=np.arange(len(primary))
    ax.errorbar(primary.relative_improvement*100,y,
                xerr=[(primary.relative_improvement-primary.relative_ci95_low)*100,
                      (primary.relative_ci95_high-primary.relative_improvement)*100],fmt='o',capsize=3)
    ax.axvline(0,color='black',lw=.8)
    ax.axvspan(-2,2,color='gray',alpha=.15,label='Exploratory +/-2% practical margin')
    ax.set_yticks(y,primary.competitor)
    ax.set_xlabel('RDFL relative loss improvement (%); unadjusted paired 95% CI')
    ax.set_title('Retrospective purged pilot; unresolved data provenance')
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(out/'pilot_paired_intervals.png',dpi=220)
    fig.savefig(out/'pilot_paired_intervals.pdf'); plt.close(fig)

    smallcols=['competitor','relative_improvement','relative_ci95_low','relative_ci95_high','holm_p','equivalence_2pct_family']
    text=(
        '# Methodological results: scope-limited evidence\n\n'
        'Status: completed simulations and retrospective empirical pilot; NOT confirmatory market evidence.\n\n'
        '## Legacy result audit\n\n'
        f'Legacy P3 weighted component-absence error in cancellation: {oldrate:.6f}. '
        'This is a selected-training-label diagnostic with a net-SD-dependent threshold, not test-set accuracy. '
        'No files from results/metrics/ were ingested.\n\n'
        '## Fresh known-truth simulation\n\n'
        '100 independent replications per scenario; common train/test draws across methods. '
        'Primary learner functions are reused from a hashed P3 snapshot; the DGP is newly specified. '
        'Net-effect MSE and component absence answer different questions.\n\n'
        +markdown(simpair.loc[simpair.competitor=='DIRECT',['scenario','loss_difference_baseline_minus_rdfl','ci95_low','ci95_high','holm_p']])+
        '\n\nPositive differences favor RDFL. Report positive scenarios as well as failures. '
        'Holm correction spans DIRECT and ZERO comparisons across all scenarios.\n\n'
        '## Fixed-threshold component diagnostic\n\n'
        +markdown(fixed.reset_index()[['scenario','component_error','ci95_low','ci95_high','component_prevalence','net_error']])+
        '\n\nError is conditional on low-response soft weights. Compare population prevalence; '
        'the rate is not a conventional false-positive rate. Thresholds 0.2/0.5 and the net-SD threshold '
        'are in absence_summary.csv. The synthetic oracle and planted positive control are in simulation outputs.\n\n'
        '## Fresh purged empirical pilot\n\n'
        +markdown(primary[smallcols])+
        '\n\nLoss uses training-stock-SD normalization and equal-date weighting; it is not NMSE against zero. '
        'Relative improvement is a proportion (0.02 = 2%). Block length 20 is primary; 10/40 sensitivity is supplied. '
        'Equivalence is a conservative family-adjusted CI diagnostic at +/-2%, not proof of exact equality. '
        'Confidence intervals displayed here are unadjusted; simultaneous intervals are in CSV files.\n\n'
        '## Historical P2c sensitivity (already examined)\n\n'
        +markdown(old.loc[old.block_length==20,smallcols])+
        '\n\nDo not attribute differences between historical P2c and the fresh rerun solely to leakage: '
        'purging, overlap exclusion, calibration, evaluation dates, and fitted samples differ.\n\n'
        '## Claim boundary and remaining work\n\n'
        'The experiment tests outcome-derived RDFL labels and TF-IDF learners. It does not show that '
        'FinBERT, XLM-R, Gemma, or all emerging-market news lack predictive information. '
        'The identifiability counterexample assumes available observables do not reveal opposing components. '
        'A future article needs resolved temporal/price provenance, verified event deduplication, '
        'independent replication, related-work positioning, and an audited multi-teacher experiment if '
        'multi-teacher claims are retained. The current data cannot identify real-world causal absence.\n')
    (out/'REPORT.md').write_text(text,encoding='utf-8')
    draft=(
        '# When Low Response Does Not Mean No Effect: A Methodological Audit of Financial Weak Supervision\n\n'
        '**Working manuscript; not submission-ready.**\n\n'
        '## Abstract draft\n\n'
        'We investigate whether low observed financial responses can support labels of absent component effects. '
        'A constructive observational-equivalence example demonstrates that net response and component absence '
        'cannot in general be identified from the same restricted observables. We evaluate a response-derived '
        'fuzzy labeling procedure using known-truth simulations with fixed effect thresholds, including positive '
        'controls and opposing-component cancellation. A separate retrospective stock-day experiment evaluates '
        'forecast loss with temporal purging, exact-text overlap exclusion, paired date-block uncertainty, and '
        'practical-equivalence sensitivity. These experiments characterize limits of the tested procedure; '
        'they do not establish universal failure of semantic teacher ensembles.\n\n'
        '## Contributions to substantiate\n\n'
        '1. An explicit distinction between net-response absence and component-effect absence.\n'
        '2. Reproducible threshold/selection diagnostics and known-truth stress tests.\n'
        '3. An empirical uncertainty audit that distinguishes no detected benefit, practical equivalence, '
        'and inconclusive evidence.\n\n'
        '## Methods\n\n'
        'Use research/PROTOCOL.md and research/IDENTIFIABILITY.md. Cite the actual implemented classifiers '
        'and include source hashes. The target in the pilot is observed open-to-close return, not CAR.\n\n'
        '## Results\n\n'
        'Insert the generated tables from results/report/REPORT.md with their status and uncertainty labels. '
        'Do not import results/metrics/ tables or random-split PhaFin-FT performance. Report all simulation '
        'scenarios, including those favorable to RDFL. No additional numerical claim is authorized by this draft.\n\n'
        '## Discussion and limitations\n\n'
        'Explain conditional weighted error denominators, population component prevalence, dependence on '
        'threshold definitions, observable-equivalence assumptions, and eight-bank external-validity limits. '
        'The empirical data remain exploratory until timestamp/calendar/adjustment gates are resolved.\n\n'
        '## Submission positioning\n\n'
        'IEEE Access explicitly lists Negative Result as a manuscript type: '
        'https://ieeeaccess.ieee.org/authors/submission-guidelines/ . '
        'Do not equate article-type eligibility with acceptance or Q1 status. '
        'Expert Systems with Applications is published by Elsevier; verify current scope/ranking before selection.\n')
    (ROOT/'manuscript').mkdir(exist_ok=True)
    (ROOT/'manuscript/DRAFT.md').write_text(draft,encoding='utf-8')
    complete(out,status='EXPLORATORY_METHODS_REPORT',simulation_rows=len(sim),pilot_rows=len(fresh))
    print('Report, uncertainty tables, four figure artifacts, and manuscript draft generated.',flush=True)

if __name__=='__main__':
    main()
