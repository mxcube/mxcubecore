"""
Utility functions for converting between different units.
"""

#
# time units
#


def us_to_sec(us: float) -> float:
    """
    convert microseconds (μs) to seconds
    """
    return us / 1_000_000.0


def ms_to_sec(ms: float) -> float:
    """
    convert milliseconds (ms) to seconds
    """
    return ms / 1000.0


def sec_to_us(sec: float) -> float:
    """
    convert seconds to microseconds (μs)
    """
    return sec * 1_000_000.0


def sec_to_hour(sec: float) -> float:
    """
    convert seconds to hours
    """
    return sec / (60 * 60)


#
# energy units
#


def ev_to_kev(ev: float) -> float:
    """
    convert eV value to KeV value
    """
    return ev / 1000.0


#
# length units
#


def meter_to_mm(meters: float) -> float:
    """
    convert meters to millimeters (mm)
    """
    return meters * 1000.0


def mm_to_meter(millimeters: float) -> float:
    """
    convert millimeters (mm) to meters
    """
    return millimeters / 1000.0


def um_to_mm(micrometers: float) -> float:
    """
    convert micrometers (μm) to millimeters
    """
    return micrometers / 1000.0


#
# current units
#


def A_to_mA(amp: float) -> float:
    """
    convert Ampere (A) to milli Ampere (mA)
    """
    return amp * 1000
