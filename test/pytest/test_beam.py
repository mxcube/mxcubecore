#
#  Project: MXCuBE
#  https://github.com/mxcube
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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from HardwareRepository.HardwareObjects.abstract.AbstractBeam import BeamShape


def test_beam_atributes(beamline):
    assert not beamline.beam is None, "Beamline.Beam objects is None (not initialized)"

    beam_div_hor, beam_div_ver = beamline.beam.get_beam_divergence()
    beam_width, beam_height, beam_shape, beam_label = beamline.beam.get_value()

    assert isinstance(beam_div_hor, (int, float)), "Horizontal beam divergence has to be int or float"
    assert isinstance(beam_div_ver, (int, float)), "Vertical beam divergence has to be int or float"
    assert isinstance(beam_width, (int, float)), "Horizontal beam size has to be int or float"
    assert isinstance(beam_height, (int, float)), "Vertical beam size has to be int or float"
    assert isinstance(beam_shape, BeamShape), "Beam shape should be defined in BeamShape Enum"

def test_set_get(beamline):
    beam_shape = beamline.beam.get_beam_shape()
    assert isinstance(beam_shape, BeamShape), "Beam shape should be defined in BeamShape Enum"
    
    beam_width, beam_height = beamline.beam.get_beam_size()
    assert isinstance(beam_width, (int, float)), "Horizontal beam size has to be int or float"
    assert isinstance(beam_height, (int, float)), "Vertical beam size has to be int or float"

