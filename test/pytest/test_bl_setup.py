import pytest

def test_bl_setup_has_attr(hwr):
    blsetup = hwr.getHardwareObject("beamline-setup")
    assert hasattr(blsetup, "transmission_hwobj")
    assert hasattr(blsetup, "resolution_hwobj")
    assert hasattr(blsetup, "energy_hwobj")
    assert hasattr(blsetup, "session_hwobj")
    assert hasattr(blsetup, "beam_info_hwobj")
    assert hasattr(blsetup, "detector_hwobj")
    assert hasattr(blsetup, "diffractometer_hwobj")

def test_hwobj_get_value(hwr):
    blsetup = hwr.getHardwareObject("beamline-setup")
