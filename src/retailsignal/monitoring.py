"""Distribution shift diagnostics; neither PSI nor shift proves accuracy decay."""
import numpy as np
import pandas as pd


def population_stability(reference, current, bins=10):
    reference, current = np.asarray(reference, dtype=float), np.asarray(current, dtype=float)
    if len(reference)==0 or len(current)==0 or not np.isfinite(reference).all() or not np.isfinite(current).all():
        raise ValueError("PSI requires finite, non-empty distributions")
    inner = np.unique(np.quantile(reference, np.linspace(0,1,bins+1)[1:-1]))
    edges = np.r_[-np.inf, inner, np.inf]
    # Additive smoothing keeps empty bins finite without dropping observations.
    expected = np.histogram(reference,bins=edges)[0].astype(float) + .5
    observed = np.histogram(current,bins=edges)[0].astype(float) + .5
    expected /= expected.sum(); observed /= observed.sum()
    return float(np.sum((observed-expected)*np.log(observed/expected)))


def drift_report(reference, current, features):
    rows = []
    for f in features:
        psi = population_stability(reference[f],current[f])
        rows.append({'feature':f,'psi':psi,'reference_mean':float(reference[f].mean()),
                     'current_mean':float(current[f].mean()),
                     'review_signal':'Review' if psi >= .2 else 'Monitor'})
    return pd.DataFrame(rows).sort_values('psi',ascending=False)
