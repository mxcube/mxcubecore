import logging
from tango import DeviceProxy
from dataclasses import dataclass


TANGO_DEVICE = "B312A-A101232-CAB01/CTL/PANDA-01"


log = logging.getLogger("HWR")


@dataclass
class SSXInjectConfig:
    enable_eiger: bool = False
    enable_custom_output: bool = False
    custom_output_delay: float = 0.0
    custom_output_pulse_width: float = 0.0
    max_triggers: int = 0


@dataclass
class OSCConfig:
    enable_eiger: bool = False
    enable_jungfrau: bool = False


def _get_tango_dev():
    return DeviceProxy(TANGO_DEVICE)


def _load_schema(dev: DeviceProxy, schema_name: str):
    # avoid reloading schema if it is already loaded,
    # this way we don't reset attributes to default values,
    # allowing users to tweak parameters outside MXCuBE
    if dev.Schema != schema_name:
        dev.Schema = schema_name


def load_osc_schema(conf: OSCConfig):
    log.info(f"[PandABox] configuring 'osc' schema with {conf}")

    dev = _get_tango_dev()

    _load_schema(dev, "osc")

    dev.EnableEiger = conf.enable_eiger
    dev.EnableJungfrau = conf.enable_jungfrau


def load_ssx_inject_schema(conf: SSXInjectConfig):
    log.info(f"[PandABox] configuring 'ssx_inject' schema with {conf}")

    dev = _get_tango_dev()

    _load_schema(dev, "ssx_inject")

    dev.EnableEiger = conf.enable_eiger
    dev.EnableCustomOutput = conf.enable_custom_output
    dev.CustomOutputDelay = conf.custom_output_delay
    dev.CustomOutputPulseWidth = conf.custom_output_pulse_width
    dev.ClockRunning = True
    dev.EnableCounterGate = True
    dev.MaxJungfrauCounts = conf.max_triggers

    # make sure measurement not running, before resetting counters,
    # otherwise counters will have bogus values
    dev.EnableMeasurement = False

    #
    # reset counters
    #
    dev.EnableShutterCount = False
    dev.EnableShutterCount = True

    dev.EnableJungfrauCount = False
    dev.EnableJungfrauCount = True


def start_measurement():
    dev = _get_tango_dev()
    dev.EnableMeasurement = True


def stop_measurement():
    dev = _get_tango_dev()
    dev.EnableCounterGate = False
    dev.EnableMeasurement = False
