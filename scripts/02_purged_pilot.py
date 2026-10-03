"""Fresh retrospective TF-IDF rerun with provisional session purge and exact-text exclusion."""
import hashlib
import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from threadpoolctl import threadpool_limits
from common import ROOT, CONFIG, load_legacy, start_run, complete

def fingerprint(text):
    normalized=re.sub(r'\s+',' ',str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def main():
    out=start_run('purged_pilot')
    m=load_legacy('04_run_tfidf_label_methods.py')
    m.P1=ROOT/'provenance/historical/p1_pilot_labels'
    m.SEEDS=CONFIG['real_data']['seeds']
    panel,bags=m.load_bags()
    articles=pd.read_csv(m.P1/'article_to_stock_day_pilot.csv')
    articles['Date']=pd.to_datetime(articles['decision_date'])
    articles['text_hash']=articles['model_text'].fillna('').map(fingerprint)
    article_groups=articles.groupby(['Date','Symbol'])['text_hash'].agg(set).to_dict()
    bags['text_hashes']=[article_groups.get((r.Date,r.Symbol),set()) for r in bags.itertuples()]
    valid=panel[panel.outcome_data_valid.astype(str).str.lower().eq('true')]
    dates=np.sort(valid.Date.unique())
    parts,folds=[],[]
    with threadpool_limits(limits=1):
        for start,stop in zip(m.OUTER_STARTS[:-1],m.OUTER_STARTS[1:]):
            prior=dates[dates<start.to_datetime64()]
            gap=CONFIG['real_data']['purge_observed_sessions']
            if len(prior)<=gap:
                continue
            boundary=pd.Timestamp(prior[-gap])
            train=bags[bags.Date<boundary].copy()
            test=bags[(bags.Date>=start)&(bags.Date<stop)].copy()
            if test.empty:
                continue
            test_hashes=set().union(*test.text_hashes)
            overlap=train.text_hashes.map(lambda s:bool(s & test_hashes))
            excluded=int(overlap.sum())
            train=train.loc[~overlap].reset_index(drop=True)
            assert train.Date.max()<boundary<start
            assert not any(s & test_hashes for s in train.text_hashes)
            retained=train[train.retain_for_text_training]
            ordinary=train[np.isfinite(train[['residual_z','volume_deviation']].to_numpy(float)).all(axis=1)]
            if len(retained)<100 or len(ordinary)<100:
                raise RuntimeError('Insufficient fold data after purge; do not silently omit the fold')
            vec=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),min_df=3,max_df=.98,
                                max_features=20000,sublinear_tf=True,norm='l2',dtype=np.float32)
            x=vec.fit_transform(train.bag_text); xt=vec.transform(test.bag_text)
            q=retained[['p_negative','p_low_response','p_positive']].to_numpy(float)
            w=retained.label_confidence.to_numpy(float)
            p=m.fit_soft_ensemble(x[retained.index],q,w,xt)
            rdfl=p @ m.class_centers(retained.target_open_close.to_numpy(float),q,w)
            hard=retained.weak_label.map(m.LABEL_TO_INT).to_numpy(int)
            hp=m.fit_hard_ensemble(x[retained.index],hard,xt)
            hpred=hp @ m.class_centers(retained.target_open_close.to_numpy(float),np.eye(3)[hard])
            oq=m.ordinary_probabilities(ordinary)
            op=m.fit_soft_ensemble(x[ordinary.index],oq,np.ones(len(ordinary)),xt)
            opred=op @ m.class_centers(ordinary.target_open_close.to_numpy(float),oq)
            predictions={'ZERO':np.zeros(len(test)),
                         'DIRECT_HUBER':m.fit_direct_ensemble(x,train.target_open_close.to_numpy(float),xt),
                         'HARD_RDFL':hpred,'ORDINARY_SOFT':opred,'RDFL_SOFT':rdfl}
            scales=valid[valid.Date<boundary].groupby('Symbol').target_open_close.std(ddof=1).clip(lower=1e-6)
            for method,pred in predictions.items():
                frame=test[['Date','Symbol','target_open_close']].rename(columns={'target_open_close':'actual'}).copy()
                frame['prediction']=pred
                frame['method']=method
                frame['block']=str(start.date())
                frame['train_end']=str(train.Date.max().date())
                frame['stock_training_scale']=frame.Symbol.map(scales)
                frame['normalized_squared_error']=((frame.actual-frame.prediction)/frame.stock_training_scale)**2
                assert np.isfinite(frame.normalized_squared_error).all()
                parts.append(frame)
            folds.append({'test_start':str(start.date()),'test_stop_exclusive':str(stop.date()),
                          'train_end':str(train.Date.max().date()),'purge_start':str(boundary.date()),
                          'purged_observed_sessions':gap,'train_bags':len(train),'test_bags':len(test),
                          'exact_text_overlap_train_bags_removed':excluded,'remaining_exact_text_overlap':0,
                          'near_duplicate_event_verification':'UNRESOLVED',
                          'calendar':'PROVISIONAL_OBSERVED_VALID_DATES'})
            print(f'{start.date()}: train={len(train)}, test={len(test)}, overlapping bags removed={excluded}',flush=True)
    predictions=pd.concat(parts,ignore_index=True)
    predictions.to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(folds).to_csv(out/'fold_manifest.csv',index=False)
    complete(out,status=CONFIG['real_data']['status'],folds=len(folds),prediction_rows=len(predictions),
             target='observed open-to-close return; not CAR',calibration='none; hyperparameters fixed')

if __name__=='__main__':
    main()
