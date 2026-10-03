"""Fresh known-truth experiments: fixed effect units, held-out prediction.

RDFL classifier functions are reused from a hashed legacy snapshot. The DGP and
diagnostics here are new. No semantic teachers are simulated by this experiment.
"""
import argparse
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits
from common import CONFIG, load_legacy, start_run, complete, dump

SCENARIOS = {
    'null_effect': {'signal':0.0, 'noise':1.0},
    'strong_signal': {'noise':0.45},
    'high_noise': {'noise':1.8},
    'cancellation_050': {'cancel':0.5},
    'cancellation_085': {'cancel':0.85},
    'cancellation_100': {'cancel':1.0},
    'anticipation': {'response':0.3},
    'stale_price': {'stale':0.3},
    'informative_missing': {'missing':True},
    'regime_shift': {'shift':True},
}

def generate(seed, scenario, n_train, n_test, features=20):
    rng = np.random.default_rng(seed)
    p = SCENARIOS[scenario]
    xtr = rng.normal(size=(n_train,features))
    xte = rng.normal(size=(n_test,features))
    beta = np.zeros(features)
    beta[:3] = [0.7,-0.5,0.4]
    beta /= np.linalg.norm(beta)  # known population scale; no test normalization
    btest = -beta if p.get('shift') else beta
    def parts(x,b):
        first = p.get('signal',1.0) * (x @ b)
        second = -p.get('cancel',0.0)*first
        if p.get('cancel',0.0)>0:
            second = second + 0.3*x[:,5]
        return first, second, first+second
    a,b,t = parts(xtr,beta)
    ae,be,te = parts(xte,btest)
    y = p.get('response',1.0)*t + p.get('noise',0.7)*rng.normal(size=n_train)
    ye = p.get('response',1.0)*te + p.get('noise',0.7)*rng.normal(size=n_test)
    if p.get('stale'):
        st = rng.random(n_train)<p['stale']
        se = rng.random(n_test)<p['stale']
        y[st] = 0.05*rng.normal(size=st.sum())
        ye[se] = 0.05*rng.normal(size=se.sum())
    volume = 0.8*np.abs(t)+rng.normal(scale=0.75,size=n_train)
    keep = np.ones(n_train,bool)
    if p.get('missing'):
        prob = 0.90-0.55/(1+np.exp(-2*(np.abs(t)-0.8)))
        keep = rng.random(n_train)<prob
    return {'x':xtr[keep], 'xt':xte, 'y':y[keep], 'yt':ye,
            'theta':t[keep], 'thetat':te, 'component':np.maximum(np.abs(a[keep]),np.abs(b[keep])),
            'volume':volume[keep], 'preselection_net_sd':float(t.std(ddof=1))}

def absence_diagnostics(rdfl, theta, component, threshold):
    retained = rdfl['retain']
    weights = rdfl['probabilities'][:,1] * rdfl['confidence'] * retained
    hard = retained & (rdfl['hard']==1)
    mass = weights.sum()
    active = component>threshold
    net_active = np.abs(theta)>threshold
    return {
        'weighted_component_absence_error':float(weights@active/mass) if mass>0 else np.nan,
        'weighted_net_absence_error':float(weights@net_active/mass) if mass>0 else np.nan,
        'hard_component_absence_error':float(active[hard].mean()) if hard.any() else np.nan,
        'component_prevalence':float(active.mean()), 'net_active_prevalence':float(net_active.mean()),
        'low_response_weight_mass':float(mass), 'hard_low_response_count':int(hard.sum()),
        'retained_fraction':float(retained.mean()), 'training_n':len(theta),
    }

def replication(seed, scenario, legacy):
    cfg = CONFIG['simulation']
    d = generate(seed,scenario,cfg['n_train'],cfg['n_test'],cfg['features'])
    x,xt,y,t = d['x'],d['xt'],d['y'],d['theta']
    v,_,_,_ = legacy.robust_standardize(d['volume'],d['volume'])
    v = np.abs(v)
    f = legacy.rdfl_labels(y,v)
    sel = f['retain']
    if sel.sum()<20 or not f['probabilities'][sel].sum(axis=0).min()>0:
        raise RuntimeError('Insufficient retained labels: do not silently omit failed replication')
    q = f['probabilities'][sel]
    w = f['confidence'][sel]
    soft = legacy.fit_soft_classifier(x[sel],q,w)
    ps = legacy.predict_probabilities(soft,xt)
    softpred = ps @ legacy.class_centers(y[sel],q,w)
    hard = legacy.fit_hard_classifier(x[sel],f['hard'][sel])
    ph = legacy.predict_probabilities(hard,xt)
    hardpred = ph @ legacy.class_centers(y[sel],np.eye(3)[f['hard'][sel]],np.ones(sel.sum()))
    qo = legacy.ordinary_labels(y,v)
    ordinary = legacy.fit_soft_classifier(x,qo,np.ones(len(x)))
    po = legacy.predict_probabilities(ordinary,xt)
    ordinarypred = po @ legacy.class_centers(y,qo,np.ones(len(x)))
    preds = {'ZERO':np.zeros(len(xt)), 'DIRECT':Ridge(alpha=1.0).fit(x,y).predict(xt),
             'HARD_RDFL':hardpred, 'ORDINARY_SOFT':ordinarypred, 'RDFL_SOFT':softpred,
             'ORACLE_RIDGE':Ridge(alpha=1.0).fit(x,t).predict(xt)}
    rows = []
    zero = float(np.mean(d['thetat']**2))
    for method,pred in preds.items():
        mse = float(np.mean((pred-d['thetat'])**2))
        rows.append({'scenario':scenario,'seed':seed,'method':method,'latent_mse':mse,
                     'observed_mse':float(np.mean((pred-d['yt'])**2)),
                     'latent_skill_vs_zero':1-mse/zero if zero>1e-12 else np.nan,
                     'training_n':len(x)})
    diagnostics=[]
    thresholds=[(f'fixed_{z:g}',z) for z in cfg['fixed_thresholds']]
    thresholds += [('net_sd_scaled_legacy_style',max(1e-10,d['preselection_net_sd'])*0.35)]
    for name,value in thresholds:
        diagnostics.append({'scenario':scenario,'seed':seed,'threshold_definition':name,
                            'threshold':value,**absence_diagnostics(f,t,d['component'],value)})
    return rows,diagnostics

def exact_equivalence(seed=7001,n=10000):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    eps = rng.normal(size=n)
    v = rng.normal(size=n)
    y0 = np.zeros(n)+eps
    y1 = x-x+eps
    return {'n':n, 'observed_outcomes_identical':bool(np.array_equal(y0,y1)),
            'volume_identical_by_construction':True,
            'component_active_world0':0.0,
            'component_active_world1':float((np.abs(x)>0.35).mean()),
            'scope':'Only rules observing identical X,Y,V; text identifying components changes the premise.'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    out=start_run('simulation_smoke' if args.smoke else 'simulation',resume=True)
    cfg=CONFIG['simulation']
    n=2 if args.smoke else cfg['replications']
    legacy=load_legacy('06_run_known_truth_simulation.py')
    checkpoints=out/'checkpoints'
    checkpoints.mkdir(exist_ok=True)
    allrows,alldiag=[],[]
    from sklearn.exceptions import ConvergenceWarning
    warnings.filterwarnings('error',category=ConvergenceWarning)
    with threadpool_limits(limits=1):
        for scenario in SCENARIOS:
            rows,diags=[],[]
            for seed in range(cfg['seed_start'],cfg['seed_start']+n):
                cache=checkpoints/f'{scenario}_{seed}.json'
                if cache.exists():
                    import json
                    payload=json.loads(cache.read_text(encoding='utf-8'))
                    r,d=payload['metrics'],payload['diagnostics']
                else:
                    r,d=replication(seed,scenario,legacy)
                    # Store null, not nonstandard JSON NaN, for undefined null-scenario skill.
                    clean=pd.DataFrame(r).astype(object).where(pd.notna(pd.DataFrame(r)),None).to_dict('records')
                    dump(cache,{'metrics':clean,'diagnostics':d})
                rows.extend(r); diags.extend(d)
            allrows.extend(rows); alldiag.extend(diags)
            print(f'{scenario}: {n} independent replications complete',flush=True)
    metrics=pd.DataFrame(allrows)
    metrics.to_csv(out/'replication_metrics.csv',index=False)
    pd.DataFrame(alldiag).to_csv(out/'absence_diagnostics.csv',index=False)
    metrics.groupby(['scenario','method'])[['latent_mse','observed_mse','latent_skill_vs_zero']].mean().to_csv(out/'means.csv')
    eq=exact_equivalence()
    dump(out/'observational_equivalence.json',eq)
    skill=float(metrics.loc[(metrics.scenario=='strong_signal')&(metrics.method=='DIRECT'),'latent_skill_vs_zero'].mean())
    assert skill>0.5, 'Planted positive control failed: pipeline cannot support negative claims'
    assert eq['observed_outcomes_identical']
    complete(out,replications_per_scenario=n,scenarios=len(SCENARIOS),positive_control_direct_skill=skill,
             scope='RDFL outcome-derived labels, not semantic teacher ensembles')

if __name__=='__main__':
    main()
