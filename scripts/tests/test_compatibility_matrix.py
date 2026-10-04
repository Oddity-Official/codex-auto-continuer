from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

spec = spec_from_file_location("compatibility_matrix", Path(__file__).parents[1] / "compatibility-matrix.py")
module = module_from_spec(spec)
spec.loader.exec_module(module)


def test_equivalent_versions_have_one_probe_but_new_stable_has_all_three():
    assert len(module.matrix("0.160.0", "0.160.0")["include"]) == 1
    rows = module.matrix("0.160.0", "0.173.0")["include"]
    assert {(x["cli"], x["daemon"]) for x in rows} == {
        ("0.160.0", "0.160.0"), ("0.173.0", "0.173.0"), ("0.160.0", "0.173.0")}


@pytest.mark.parametrize("value", ["latest", "0.173.0-alpha", "invalid"])
def test_unresolved_or_nonstable_versions_fail(value):
    with pytest.raises(ValueError):
        module.matrix("0.160.0", value)
