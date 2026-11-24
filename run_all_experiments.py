"""Canonical, reproducible audit experiment for this repository.

This runner deliberately labels its input as synthetic.  It does not download or
claim to reproduce CEEW data.  It evaluates a *one-step-ahead* 15-minute
forecast: at origin t-1, observations through t-1 and contemporaneous
exogenous variables are available to predict t.  Future weather availability is
an assumption of the synthetic experiment, not an operational claim.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
import statsmodels
from sklearn.cluster import KMeans
from sklearn.metrics import (calinski_harabasz_score, davies_bouldin_score,
                             mean_absolute_error, mean_squared_error, r2_score,
                             silhouette_score)
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from load_forecasting_unit_commitment import IndianFeederTelemetryGenerator

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
SEED, TEST_FRACTION, SLOTS = 42, 0.15, 96
GRID = {"svr__C": [1., 10., 100.], "svr__gamma": ["scale", .1, .01],
        "svr__epsilon": [.05, .1, .2]}


def dump(path, obj):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    finite = np.isfinite(y) & np.isfinite(p)
    y, p = y[finite], p[finite]
    denom = np.abs(y)
    valid = denom > 1e-6
    ape = np.abs(y[valid] - p[valid]) / denom[valid]
    return {"n": int(len(y)), "MAE_kW": float(mean_absolute_error(y, p)),
            "RMSE_kW": float(np.sqrt(mean_squared_error(y, p))),
            "R2": float(r2_score(y, p)), "MAPE_percent": float(100 * ape.mean()),
            "sMAPE_percent": float(200 * np.mean(np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-6))),
            "WAPE_percent": float(100*np.abs(y-p).sum()/np.abs(y).sum()),
            "max_absolute_error_kW": float(np.abs(y-p).max())}


def audit_raw(raw):
    idx = raw.index
    meter = [c for c in raw if c.startswith("meter_kW_")]
    intervals = idx.to_series().diff().dropna().dt.total_seconds().div(60)
    return {"data_source": "SYNTHETIC: IndianFeederTelemetryGenerator", "real_CEEW_data_present": False,
            "meters": len(meter), "temporal_coverage": {"start": str(idx.min()), "end": str(idx.max())},
            "original_sampling_minutes": sorted(intervals.unique().tolist()),
            "rows": len(raw), "missing_cells": int(raw.isna().sum().sum()),
            "missing_percent": float(raw.isna().mean().mean()*100), "duplicate_timestamps": int(idx.duplicated().sum()),
            "irregular_intervals": int((intervals != 3).sum()),
            "negative_meter_values": int((raw[meter] < 0).sum().sum()),
            "outlier_policy": "No automatic outlier removal; synthetic generator clips loads to positive values.",
            "labels": "Generator assigns latent alternating residential/agricultural mechanisms; K-Means labels are inferred profiles, not external labels."}


def resample_and_impute(raw, method):
    df = raw.resample("15min").mean()
    if method == "drop": return df
    if method == "ffill": return df.ffill().bfill()
    if method == "linear": return df.interpolate("linear", limit_direction="both").ffill().bfill()
    if method == "cubic": return df.interpolate("cubicspline", limit_direction="both").ffill().bfill()
    raise ValueError(method)


def daily_shapes(df, meters):
    out = []
    for m in meters:
        for _, g in df[m].groupby(df.index.date):
            if len(g) == SLOTS and g.notna().all():
                a = g.to_numpy(float); d = a.max()-a.min()
                out.append((a-a.min())/d if d else np.zeros(SLOTS))
    return np.asarray(out)


def slp_from_train(df, meters):
    a = daily_shapes(df, meters)
    km = KMeans(n_clusters=2, random_state=SEED, n_init=20).fit(a)
    centers = km.cluster_centers_
    evening = [c[72:88].mean()/(c.mean()+1e-9) for c in centers]
    return centers[int(np.argmax(evening))], km, a


def feature_frame(df, target, slp=None, feature_set="full"):
    rows, ys, ts = [], [], []
    for i in range(SLOTS, len(target)):
        t = target.index[i]; slot = t.hour*4 + t.minute//15
        d = {"lag_1": target.iloc[i-1], "lag_2": target.iloc[i-2], "lag_96": target.iloc[i-SLOTS],
             "sin_time": np.sin(2*np.pi*slot/SLOTS), "cos_time": np.cos(2*np.pi*slot/SLOTS),
             "temperature": df["temperature"].iloc[i], "solar_irradiance": df["solar_irradiance"].iloc[i],
             "is_weekend": df["is_weekend"].iloc[i], "is_holiday": df["is_holiday"].iloc[i]}
        if slp is not None: d["slp_anchor"] = slp[slot]
        groups = {"ar": ["lag_1","lag_2","lag_96"], "cyclic": ["sin_time","cos_time"],
                  "weather": ["temperature","solar_irradiance","is_weekend","is_holiday"], "slp": ["slp_anchor"]}
        keep = sum((groups[x] for x in feature_set.split("+")), [])
        rows.append([d[x] for x in keep]); ys.append(target.iloc[i]); ts.append(t)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(ts), columns=keep), pd.Series(ys, index=pd.DatetimeIndex(ts))


def tune_predict(Xtr, ytr, Xte):
    cv = TimeSeriesSplit(n_splits=3)
    model = Pipeline([("scaler", StandardScaler()), ("svr", SVR(kernel="rbf"))])
    gs = GridSearchCV(model, GRID, scoring="neg_root_mean_squared_error", cv=cv, n_jobs=-1, refit=True)
    gs.fit(Xtr, ytr)
    return gs, pd.Series(gs.predict(Xte), index=Xte.index), cv


def baseline_seasonal(y_all, test_index): return y_all.shift(SLOTS).loc[test_index]
def baseline_persistence(y_all, test_index): return y_all.shift(1).loc[test_index]


def error_segments(y, p):
    e = pd.DataFrame({"actual": y, "pred": p}); hour=e.index.hour
    masks={"00_06":hour<6,"06_18":(hour>=6)&(hour<18),"18_22":(hour>=18)&(hour<22),"22_00":hour>=22,
           "peak_actual_top10pct":e.actual>=e.actual.quantile(.9), "ramp_up":e.actual.diff()>e.actual.diff().quantile(.9),
           "ramp_down":e.actual.diff()<e.actual.diff().quantile(.1)}
    return {n: metrics(e.loc[m,"actual"],e.loc[m,"pred"]) for n,m in masks.items() if m.sum()>1}


def main():
    RESULTS.mkdir(exist_ok=True); FIGURES.mkdir(exist_ok=True)
    raw = IndianFeederTelemetryGenerator(days=45, num_consumers=6, seed=SEED).generate()
    da = audit_raw(raw); dump(RESULTS/"dataset_audit.json", da)
    # Canonical preprocessing intentionally happens after raw generation.  This is non-causal
    # interpolation; it is disclosed and therefore unsuitable for an online claim.
    clean = resample_and_impute(raw, "cubic")
    meter = [c for c in clean if c.startswith("meter_kW_")]
    target = clean[meter].sum(axis=1)
    split_raw = int(len(clean)*(1-TEST_FRACTION))
    train_clean = clean.iloc[:split_raw]
    slp, km, shapes = slp_from_train(train_clean, meter)
    X, y = feature_frame(clean, target, slp, "ar+cyclic+weather+slp")
    split = int(len(X)*(1-TEST_FRACTION)); Xtr,Xte,ytr,yte=X.iloc[:split],X.iloc[split:],y.iloc[:split],y.iloc[split:]
    gs, pred, cv = tune_predict(Xtr,ytr,Xte)
    # assertions expose only correct chronological mechanics, not the non-causal imputation limitation
    splits=[]
    for i,(a,b) in enumerate(cv.split(Xtr),1):
        assert a.max() < b.min(); splits.append({"fold":i,"train_start":str(Xtr.index[a.min()]),"train_end":str(Xtr.index[a.max()]),"validation_start":str(Xtr.index[b.min()]),"validation_end":str(Xtr.index[b.max()])})
    assert Xtr.index.max() < Xte.index.min()
    dump(RESULTS/"cv_splits.json", splits)
    params={k.replace("svr__",""):v for k,v in gs.best_params_.items()}
    hp={**params,"CV_RMSE_kW":float(-gs.best_score_),"scoring":"neg_root_mean_squared_error","cv":"TimeSeriesSplit(n_splits=3)","random_seed":SEED,"feature_set":list(X.columns)}
    dump(RESULTS/"best_hyperparameters.json", hp)
    final_metrics={"SVR_AR_cyclic_weather_SLP":metrics(yte,pred),"Persistence":metrics(yte,baseline_persistence(y,test_index=yte.index)),"Seasonal_naive_t_minus_96":metrics(yte,baseline_seasonal(y,yte.index))}
    # Ablations use identical split and tune only on the training partition.
    specs={"SVR_AR":"ar","SVR_AR_cyclic":"ar+cyclic","SVR_AR_weather":"ar+weather","SVR_AR_SLP":"ar+slp","SVR_full":"ar+cyclic+weather+slp"}
    ab=[]
    for name,spec in specs.items():
        xx,yy=feature_frame(clean,target,slp,spec); n=int(len(xx)*(1-TEST_FRACTION)); g,p,_=tune_predict(xx.iloc[:n],yy.iloc[:n],xx.iloc[n:]); ab.append({"model":name,**metrics(yy.iloc[n:],p)})
    ab.insert(0,{"model":"Persistence",**final_metrics["Persistence"]}); ab.insert(1,{"model":"Seasonal_naive",**final_metrics["Seasonal_naive_t_minus_96"]})
    pd.DataFrame(ab).to_csv(RESULTS/"feature_ablation.csv",index=False)
    pd.DataFrame([{"model":k,**v} for k,v in final_metrics.items()]).to_csv(RESULTS/"final_metrics.csv",index=False)
    predout=pd.DataFrame({"actual_kW":yte,"SVR_prediction_kW":pred,"persistence_kW":baseline_persistence(y,yte.index),"seasonal_naive_kW":baseline_seasonal(y,yte.index)})
    predout.to_csv(RESULTS/"final_predictions.csv",index_label="timestamp")
    # cluster diagnostics, deliberately not mapped to real-world categories
    ks=[]
    for k in range(2,6):
        z=KMeans(n_clusters=k,random_state=SEED,n_init=20).fit_predict(shapes)
        ks.append({"k":k,"silhouette":float(silhouette_score(shapes,z)),"davies_bouldin":float(davies_bouldin_score(shapes,z)),"calinski_harabasz":float(calinski_harabasz_score(shapes,z))})
    pd.DataFrame(ks).to_csv(RESULTS/"clustering_sensitivity.csv",index=False)
    stability=[]
    for seed in range(10):
        z=KMeans(n_clusters=2,random_state=seed,n_init=20).fit(shapes).cluster_centers_
        stability.append(float(np.min([np.linalg.norm(z[0]-km.cluster_centers_[0])+np.linalg.norm(z[1]-km.cluster_centers_[1]),np.linalg.norm(z[0]-km.cluster_centers_[1])+np.linalg.norm(z[1]-km.cluster_centers_[0])])/2))
    dump(RESULTS/"clustering_stability.json",{"seeds":list(range(10)),"centroid_distance_mean":float(np.mean(stability)),"centroid_distance_max":float(np.max(stability))})
    # Imputation ablation evaluates a complete canonical target against alternative training preprocessing.
    imp=[]
    for method in ["ffill","linear","cubic"]:
        q=resample_and_impute(raw,method); tt=q[[c for c in q if c.startswith("meter_kW_")]].sum(axis=1); ss,_k,_a=slp_from_train(q.iloc[:split_raw],[c for c in q if c.startswith("meter_kW_")]); xx,yy=feature_frame(q,tt,ss,"ar+cyclic+weather+slp"); n=int(len(xx)*(1-TEST_FRACTION)); _,pp,_=tune_predict(xx.iloc[:n],yy.iloc[:n],xx.iloc[n:]); imp.append({"imputation":method,**metrics(yy.iloc[n:],pp)})
    pd.DataFrame(imp).to_csv(RESULTS/"imputation_ablation.csv",index=False)
    # One-step experiment cannot yield genuine 48-hour recursive/direct horizon evidence.
    pd.DataFrame({"horizon":["15m","30m","1h","2h","4h","6h","12h","24h","36h","48h"],"status":"NOT_EVALUATED","reason":"Canonical model is one-step-ahead; no recursive or direct multi-step protocol was implemented."}).to_csv(RESULTS/"horizon_metrics.csv",index=False)
    dump(RESULTS/"final_experiment_config.json",{"dataset":da["data_source"],"seed":SEED,"test_fraction":TEST_FRACTION,"forecast_definition":"one-step ahead at 15 minutes","known_at_forecast_origin":"lags through t-1; contemporaneous synthetic weather assumed known","imputation":"global cubic spline (non-causal; limitation)","SLP_fit_period":"raw training period only","canonical_model":hp})
    dump(RESULTS/"leakage_audit.json",{"test_holdout_before_tuning":True,"scaler_inside_cv_pipeline":True,"SLP_fit_on_training_only":True,"lags_are_past_only":True,"warning":"Cubic spline interpolation is global/non-causal and can use future observations. It remains a documented limitation; use causal imputation for deployment claims."})
    dump(RESULTS/"error_by_segment.json",error_segments(yte,pred))
    # diagnostics
    fig,ax=plt.subplots(figsize=(6,6)); ax.scatter(yte,pred,s=8,alpha=.55); lo=min(yte.min(),pred.min());hi=max(yte.max(),pred.max());ax.plot([lo,hi],[lo,hi],"k--");ax.set(xlabel="Actual load (kW)",ylabel="Predicted load (kW)",title=f"Actual vs predicted; R²={final_metrics['SVR_AR_cyclic_weather_SLP']['R2']:.6f}");fig.tight_layout();fig.savefig(FIGURES/"actual_vs_predicted.png",dpi=200);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,3));ax.plot(yte.index,yte-pred,lw=.8);ax.axhline(0,color="k",lw=.7);ax.set(ylabel="Residual (kW)",title="SVR residuals");fig.tight_layout();fig.savefig(FIGURES/"residuals.png",dpi=200);plt.close(fig)
    print("Completed canonical synthetic audit experiment.")

if __name__ == "__main__": main()
