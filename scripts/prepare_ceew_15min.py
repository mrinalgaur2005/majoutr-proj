"""Memory-bounded CEEW aggregation and meter-level SLP validation; no forecasting."""
from __future__ import annotations
import json, sys, platform
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score, adjusted_rand_score, normalized_mutual_info_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.ceew_loader import iter_ceew

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results/ceew'; FIG=OUT/'figures'; SEEDS=range(10)

def save_json(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,default=str))
def describe_centroid(c):
    early=c[:24].mean(); day=c[24:72].mean(); evening=c[72:88].mean()
    return 'relatively higher evening normalized demand' if evening>max(early,day)*1.1 else ('relatively higher daytime normalized demand' if day>early*1.1 else 'relatively flatter normalized profile')

def main():
 OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(exist_ok=True)
 # Aggregate each source chunk. A bin is later complete only after exact timestamp checks.
 parts=[]; malformed=0; off_boundary=0
 for raw in iter_ceew(chunksize=250_000):
  malformed+=int(raw.timestamp.isna().sum()); x=raw.dropna(subset=['timestamp','interval_energy_kwh']).copy()
  off_boundary+=int(((x.timestamp.dt.minute%3!=0)|(x.timestamp.dt.second!=0)).sum())
  x['bin']=x.timestamp.dt.floor('15min')
  parts.append(x.groupby(['meter_id','city','bin'],as_index=False).agg(energy_15min_kwh=('interval_energy_kwh','sum'),raw_rows=('timestamp','size'),unique_timestamps=('timestamp','nunique'),min_timestamp=('timestamp','min'),max_timestamp=('timestamp','max')))
 bins=pd.concat(parts,ignore_index=True)
 # Files can overlap at boundaries: consolidate source partials, preserving raw count and unique timestamp detail.
 bins=bins.groupby(['meter_id','city','bin'],as_index=False).agg(energy_15min_kwh=('energy_15min_kwh','sum'),raw_rows=('raw_rows','sum'),unique_timestamps=('unique_timestamps','sum'),min_timestamp=('min_timestamp','min'),max_timestamp=('max_timestamp','max'))
 expected=bins['bin']+pd.to_timedelta([0,3,6,9,12],unit='m') # only shape check needed after unique count
 bins['complete']=((bins.raw_rows==5)&(bins.unique_timestamps==5)&((bins.max_timestamp-bins.min_timestamp)==pd.Timedelta(minutes=12)))
 bins['load_kw']=np.where(bins.complete,bins.energy_15min_kwh/.25,np.nan)
 assert ((bins.loc[bins.complete,'load_kw']-bins.loc[bins.complete,'energy_15min_kwh']/.25).abs()<1e-12).all()
 assert (bins.groupby(['meter_id','bin']).size()<=1).all()
 bins.to_csv(OUT/'ceew_15min_bins.csv',index=False)
 # Daily wide profiles preserve absolute kW; incompletes remain NaN.
 b=bins.copy(); b['date']=b.bin.dt.date; b['slot']=(b.bin.dt.hour*4+b.bin.dt.minute//15)
 wide=b.pivot(index=['meter_id','city','date'],columns='slot',values='load_kw').reindex(columns=range(96))
 counts=wide.notna().sum(axis=1); meta=wide.reset_index()[['meter_id','city','date']]; meta['complete_slots']=counts.values; meta['valid_100']=counts.values==96; meta['valid_95']=counts.values>=92
 meta.to_csv(OUT/'ceew_daily_profile_summary.csv',index=False)
 # Primary threshold: 100% avoids creating values; 95% reported only as sensitivity, never filled.
 valid=wide[counts==96]; assert valid.shape[1]==96 and np.isfinite(valid.to_numpy()).all()
 daily_mean=valid.mean(axis=1); norm_mean=valid.div(daily_mean,axis=0); norm_max=valid.div(valid.max(axis=1),axis=0)
 # meter behaviour = median normalized daily profile; eligible only with >=14 complete days, predeclared as two weeks.
 nvalid=valid.groupby(level='meter_id').size(); eligible=nvalid[nvalid>=14].index
 profiles=norm_mean.loc[norm_mean.index.get_level_values('meter_id').isin(eligible)].groupby(level=['meter_id','city']).median()
 profiles.to_csv(OUT/'ceew_meter_profiles.csv')
 profile_meta=pd.DataFrame({'meter_id':nvalid.index,'valid_days_100':nvalid.values}); profile_meta['eligible_14_days']=profile_meta.meter_id.isin(eligible); profile_meta.to_csv(OUT/'ceew_meter_profile_eligibility.csv',index=False)
 X=profiles.to_numpy(); assert np.isfinite(X).all() and len(X)>=6
 metrics=[]; assignments=[]; centroids=[]; stability=[]
 for k in range(2,7):
  labels_by_seed=[]
  for seed in SEEDS:
   km=KMeans(n_clusters=k,random_state=seed,n_init=20).fit(X); labels_by_seed.append(km.labels_)
   if seed==0:
    metrics.append({'k':k,'silhouette':silhouette_score(X,km.labels_),'davies_bouldin':davies_bouldin_score(X,km.labels_),'calinski_harabasz':calinski_harabasz_score(X,km.labels_),'inertia':km.inertia_,'cluster_sizes':json.dumps(np.bincount(km.labels_,minlength=k).tolist())})
    assignments.extend({'meter_id':m,'city':c,'k':k,'cluster':int(z)} for (m,c),z in zip(profiles.index,km.labels_))
    for j,row in enumerate(km.cluster_centers_): centroids.extend({'k':k,'cluster':j,'slot':s,'normalized_load':v,'description':describe_centroid(row)} for s,v in enumerate(row))
  aris=[adjusted_rand_score(labels_by_seed[0],z) for z in labels_by_seed[1:]]; nmis=[normalized_mutual_info_score(labels_by_seed[0],z) for z in labels_by_seed[1:]]
  stability.append({'k':k,'seed_ARI_mean':float(np.mean(aris)),'seed_NMI_mean':float(np.mean(nmis)),'seed_ARI_min':float(np.min(aris))})
 pd.DataFrame(metrics).to_csv(OUT/'ceew_clustering_metrics.csv',index=False); pd.DataFrame(assignments).to_csv(OUT/'ceew_cluster_assignments.csv',index=False); pd.DataFrame(centroids).to_csv(OUT/'ceew_cluster_centroids.csv',index=False); pd.DataFrame(stability).to_csv(OUT/'ceew_cluster_stability.csv',index=False)
 # clear centroid / quality graphics, no unreadable mass line plot.
 for k in range(2,7):
  z=pd.read_csv(OUT/'ceew_cluster_centroids.csv').query('k==@k'); fig,ax=plt.subplots(figsize=(9,4));
  for c,g in z.groupby('cluster'): ax.plot(g.slot,g.normalized_load,label=f'Cluster {c}: {g.description.iloc[0]}')
  ax.set(xlabel='15-minute slot',ylabel='Daily-mean-normalized load',title=f'CEEW meter-profile centroids (K={k})');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(FIG/f'centroids_k{k}.png',dpi=200);plt.close(fig)
 m=pd.DataFrame(metrics); fig,axs=plt.subplots(1,3,figsize=(12,3));
 for ax,col in zip(axs,['silhouette','davies_bouldin','calinski_harabasz']): ax.plot(m.k,m[col],marker='o');ax.set(title=col,xlabel='K')
 fig.tight_layout();fig.savefig(FIG/'clustering_quality.png',dpi=200);plt.close(fig)
 summary={'raw_timestamp_validation':{'malformed_timestamps':malformed,'off_three_minute_boundaries':off_boundary,'timezone':'naive timestamps; no timezone/DST indicator in source'},'bins':{'complete':int(bins.complete.sum()),'incomplete':int((~bins.complete).sum()),'total':len(bins)},'daily_profiles':{'meter_days_total':int(len(meta)),'valid_100_percent':int(meta.valid_100.sum()),'valid_95_percent':int(meta.valid_95.sum()),'eligible_meters_min_14_complete_days':int(len(eligible)),'valid_days_per_meter_min_median_max':[int(nvalid.min()),float(nvalid.median()),int(nvalid.max())]},'normalization':{'primary':'daily mean normalization, then per-meter median of valid daily normalized profiles','sensitivity_considered':'max normalization computed for comparison but mean normalization selected to preserve relative shape around a unit daily mean','daily_completeness_primary':'100%; 95% reported as unfilled sensitivity','no_imputation':True},'reproducibility':{'seeds':list(SEEDS),'kmeans_n_init':20,'python':platform.python_version(),'pandas':pd.__version__}}
 save_json('ceew_15min_summary.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
