from unittest.mock import Mock, call, patch

import pytest

from mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline import SampleDelivery
from mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions import (
    MeasureFlux,
    MoveToMD3SavedPosition,
    PrepareOpenHutch,
    SaveMD3Position,
)


def _assert_open_hutch_calls(hwr, laser, log):
    """Checks that expected standard calls for 'prepare open hutch' where made."""

    hwr.beamline.get_object_by_role.assert_called_once_with("laser")
    laser.disarm.assert_called_once()

    # check calls on collect hardware object
    collect = hwr.beamline.collect
    collect.close_safety_shutter.assert_called_once()
    collect.close_detector_cover.assert_called_once()
    collect.close_fast_shutter.assert_called_once()
    collect.move_detector_to_safe_position.assert_called_once()

    # check calls on diffractometer hardware object
    diffractometer = hwr.beamline.diffractometer
    diffractometer.wait_device_ready.assert_called_once()
    if hwr.beamline.is_hve_sample_delivery():
        diffractometer.channel_dict[
            "BeamstopPosition"
        ].set_value.assert_called_once_with("PARK")
        diffractometer.channel_dict[
            "CapillaryPosition"
        ].set_value.assert_called_once_with("PARK")
        log.info.assert_has_calls(
            [
                call("Preparing experimental hutch for door opening."),
                call("Setting diffractometer to 'equivalent' of Transfer phase."),
                call("Moving detector to safe position."),
            ],
        )
    else:
        diffractometer.set_phase.assert_called_once_with("Transfer")
        # check logging calls
        log.info.assert_has_calls(
            [
                call("Preparing experimental hutch for door opening."),
                call("Setting diffractometer to Transfer phase."),
                call("Moving detector to safe position."),
            ],
        )


@pytest.mark.parametrize("sample_delivery", [SampleDelivery.osc, SampleDelivery.hve])
def test_prepare_open_hutch_eiger(sample_delivery: SampleDelivery):
    """Test PrepareOpenHutch beamline action with Eiger detector."""

    hwr = Mock()
    hwr.beamline.detector.get_property.return_value = "Eiger"
    hwr.beamline.sample_delivery = sample_delivery
    hwr.beamline.diffractometer.channel_dict = {
        "BeamstopPosition": Mock(),
        "CapillaryPosition": Mock(),
    }
    laser = Mock()
    hwr.beamline.get_object_by_role.return_value = laser
    log = Mock()

    with (
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr),
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.log", log),
    ):
        bl_action = PrepareOpenHutch()
        bl_action()

    _assert_open_hutch_calls(hwr, laser, log)
    # take pedestal should not be called for Eiger
    hwr.beamline.detector.pedestal.assert_not_called()


@pytest.mark.parametrize("sample_delivery", [SampleDelivery.osc, SampleDelivery.hve])
def test_prepare_open_hutch_jungfrau(sample_delivery: SampleDelivery):
    """Test PrepareOpenHutch beamline action with Jungfrau detector."""

    hwr = Mock()
    hwr.beamline.detector.get_property.return_value = "JUNGFRAU"
    hwr.beamline.sample_delivery = sample_delivery
    hwr.beamline.diffractometer.channel_dict = {
        "BeamstopPosition": Mock(),
        "CapillaryPosition": Mock(),
    }
    laser = Mock()
    hwr.beamline.get_object_by_role.return_value = laser
    log = Mock()

    with (
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr),
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.log", log),
    ):
        bl_action = PrepareOpenHutch()
        bl_action()

    _assert_open_hutch_calls(hwr, laser, log)

    # check take pedestal operation was invoked
    hwr.beamline.detector.pedestal.assert_called_once()


def test_prepare_open_hutch_error():
    """Test a case where PrepareOpenHutch beamline action fails."""

    hwr = Mock()
    hwr.beamline.collect.close_safety_shutter.side_effect = Exception("dummy")
    laser = Mock()
    hwr.beamline.get_object_by_role.return_value = laser
    log = Mock()

    with (
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr),
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.log", log),
    ):
        bl_action = PrepareOpenHutch()
        bl_action()

    hwr.beamline.get_object_by_role.assert_called_once_with("laser")
    laser.disarm.assert_called_once()
    log.exception.assert_called_with(
        "Error preparing to open hutch.\nError was: '%s'",
        "dummy",
    )


def test_measure_flux():
    """Test MeasureFlux beamline action."""

    hwr = Mock()
    hwr.beamline.collect.get_instant_flux.return_value = 0.42

    log = Mock()

    with (
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr),
        patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.log", log),
    ):
        bl_action = MeasureFlux()
        bl_action()
    log.info.assert_called_once_with("Flux at sample position is %.2e ph/s", 0.42)


def test_save_md3_position():
    """Test SaveMD3Position beamline action."""

    hwr = Mock()
    with patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr):
        bl_action = SaveMD3Position()
        bl_action()

    hwr.beamline.diffractometer.save_centered_position.assert_called_once()


def test_move_to_md3_saved_position_ok():
    """Test the successful run of MoveToMD3SavedPosition beamline action."""
    hwr = Mock()

    with patch("mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline_actions.HWR", hwr):
        bl_action = MoveToMD3SavedPosition()
        bl_action()

    hwr.beamline.diffractometer.goto_centered_position.assert_called_once()
