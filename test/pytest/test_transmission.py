#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.


def test_transmission_attributes(beamline):
    assert (
        not beamline.energy is None
    ), "Energy hardware objects is None (not initialized)"

    value = beamline.transmission.get_value()
    limits = beamline.transmission.get_limits()

    assert isinstance(value, float), "Transmission value has to be float"
    assert isinstance(
        limits, (list, tuple)
    ), "Energy limits has to be defined as tuple or list"
    assert not None in limits, "One or several limits is None"
    assert limits[0] < limits[1], "First value of energy limits has to be the low limit"


def test_transmission_methods(beamline):
    target = 60.0
    beamline.transmission.set_value(target)
    assert beamline.transmission.get_value() == target
