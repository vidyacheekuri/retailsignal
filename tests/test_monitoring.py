import numpy as np
import pytest
from retailsignal.monitoring import population_stability


def test_psi_identical_population_is_zero():
    assert population_stability(np.arange(100),np.arange(100)) == 0


def test_psi_detects_shift_and_handles_constant_reference():
    assert population_stability(np.arange(100),np.arange(100)+200) > .2
    assert np.isfinite(population_stability(np.ones(100), np.full(100,2)))


def test_psi_rejects_missing_values():
    with pytest.raises(ValueError):
        population_stability([1,2],[np.nan,3])
