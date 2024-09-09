from math import isclose
from mxcubecore.utils.units import (
    us_to_sec,
    sec_to_us,
    sec_to_hour,
    ev_to_kev,
    meter_to_mm,
    mm_to_meter,
    um_to_mm,
    A_to_mA,
)


def test_us_to_sec():
    assert isclose(us_to_sec(500_000), 0.5)
    assert isclose(us_to_sec(123.4), 0.0001234)


def test_sec_to_us():
    assert isclose(sec_to_us(2), 2_000_000.0)
    assert isclose(sec_to_us(0.42), 420_000.0)


def test_sec_to_hour():
    assert isclose(sec_to_hour(3800), 1.056, abs_tol=0.001)
    assert isclose(sec_to_hour(1800.0), 0.5)


def test_ev_to_kev():
    assert isclose(ev_to_kev(12000), 12.0)
    assert isclose(ev_to_kev(10.5), 0.0105)


def test_meter_to_mm():
    assert isclose(meter_to_mm(10), 10_000.0)
    assert isclose(meter_to_mm(0.5214), 521.4)


def test_mm_to_meter():
    assert isclose(mm_to_meter(1200), 1.2)
    assert isclose(mm_to_meter(10.5), 0.0105)


def test_um_to_mm():
    assert isclose(um_to_mm(5), 0.005)
    assert isclose(um_to_mm(42.2), 0.0422)


def test_A_to_mA():
    assert isclose(A_to_mA(2), 2000.0)
    assert isclose(A_to_mA(0.3921), 392.1)
