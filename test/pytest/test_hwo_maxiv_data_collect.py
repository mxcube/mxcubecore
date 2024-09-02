import math
import pytest
from mxcubecore.HardwareObjects.MAXIV.DataCollect import DataCollect


class _DummyAutoProcessing:
    SPACE_GROUPS_FULL_NAMES = {
        "P1": "P 1",
        "P21": "P 1 21 1",
    }

    def find_spg_full_name(self, space_group: str) -> str:
        return self.SPACE_GROUPS_FULL_NAMES[space_group]


@pytest.fixture
def data_collect():
    data_collect_hwo = DataCollect("dummy")
    data_collect_hwo.autoprocessing_hwobj = _DummyAutoProcessing()

    return data_collect_hwo


def _sample_ref_dicts_equal(got: dict, expected: dict) -> bool:
    """
    check if two sample reference dictionaries are equal

    takes care of checking unit cell parameters with math.isclose(),
    to handle floating point values
    """

    #
    # check space_group section
    #
    if got.get("space_group") != expected.get("space_group"):
        return False

    #
    # check unit_cell section
    #
    got_unit_cell = got.get("unit_cell")
    expected_unit_cell = expected.get("unit_cell")

    if expected_unit_cell is None and got_unit_cell is None:
        # no unit cells expected, we did not get any, we are done
        return True

    # check that got exactly the keys we expect
    if got_unit_cell.keys() != expected_unit_cell.keys():
        return False

    # check that all unit cell values are what we expect
    for key, expected in expected_unit_cell.items():
        got = got_unit_cell[key]
        if not math.isclose(expected, got):
            return False

    return True


def test_header_appendix_sample_reference_none(data_collect):
    """
    test the case where no sample reference parameters where specified
    """
    sample_ref = data_collect.get_header_appendix_sample_reference_dict({})
    assert sample_ref is None


def test_header_appendix_sample_reference_all(data_collect):
    """
    test the case where both space group and all unit cell parameters are specified
    """
    params = dict(spacegroup="P21", cell="53.55,60.87,119.46,90.0,100.1,120")
    sample_ref = data_collect.get_header_appendix_sample_reference_dict(params)

    assert _sample_ref_dicts_equal(
        sample_ref,
        {
            "space_group": "P 1 21 1",
            "unit_cell": {
                "a": 53.55,
                "b": 60.87,
                "c": 119.46,
                "alpha": 90.0,
                "beta": 100.1,
                "gamma": 120,
            },
        },
    )


def test_header_appendix_sample_reference_only_space_group(data_collect):
    """
    test the case where only space group parameter is specified
    """
    params = dict(spacegroup="P1", cell=",,,,,")
    sample_ref = data_collect.get_header_appendix_sample_reference_dict(params)

    assert _sample_ref_dicts_equal(sample_ref, {"space_group": "P 1"})


def test_header_appendix_sample_reference_only_unit_cell(data_collect):
    """
    test the case where only unit cell parameter are specified
    """
    params = dict(spacegroup="", cell="53.55,60.87,119.46,90.0,100.1,120")
    sample_ref = data_collect.get_header_appendix_sample_reference_dict(params)

    assert _sample_ref_dicts_equal(
        sample_ref,
        {
            "unit_cell": {
                "a": 53.55,
                "b": 60.87,
                "c": 119.46,
                "alpha": 90.0,
                "beta": 100.1,
                "gamma": 120,
            }
        },
    )


def test_header_appendix_sample_reference_sparce_unit_cell(data_collect):
    """
    test the case where only partial unit cell parameter are specified
    """
    params = dict(spacegroup="", cell="12,,42,90,,")
    sample_ref = data_collect.get_header_appendix_sample_reference_dict(params)

    assert _sample_ref_dicts_equal(
        sample_ref,
        {
            "unit_cell": {
                "a": 12.0,
                "c": 42.0,
                "alpha": 90.0,
            }
        },
    )
