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

def test_get(beamline):
    beam_div_hor, beam_div_ver = beamline.beam.get_beam_divergence()
    assert isinstance(beam_div_hor, (int, float)), "Horizontal beam divergence has to be int or float"
    assert isinstance(beam_div_ver, (int, float)), "Vertical beam divergence has to be int or float"
    beam_shape = beamline.beam.get_beam_shape()
    assert isinstance(beam_shape, BeamShape), "Beam shape should be defined in BeamShape Enum"
    
    beam_width, beam_height = beamline.beam.get_beam_size()
    assert isinstance(beam_width, (int, float)), "Horizontal beam size has to be int or float"
    assert isinstance(beam_height, (int, float)), "Vertical beam size has to be int or float"

def test_set_aperture_diameters(beamline):
    """
    Set large slit gaps and in the sequence select all aperture diameters.
    Beam shape is eliptical and size defined by the selected aperture
    """
    beamline.beam.slits.set_horizontal_gap(1)
    beamline.beam.slits.set_vertical_gap(1)
    for aperture_diameter in beamline.beam.aperture.get_diameter_size_list():
        beamline.beam.aperture.set_diameter_size(aperture_diameter)
        beam_width, beam_height = beamline.beam.get_beam_size()
        #TODO get_beam_size returns size in mm, but aperture diameters are in microns
        # Use microns in all beam related hwobj
        assert beam_width == beam_height == aperture_diameter / 1000.
 
        beam_shape = beamline.beam.get_beam_shape()
        assert beam_shape == BeamShape.ELIPTICAL

def test_set_slit_gaps(beamline):
    """
    Set slits smaller as the largest aperture diameter.
    In this case beam size and shape is defined by slits 
    """
    max_diameter = max(beamline.beam.aperture.get_diameter_size_list())
    beamline.beam.aperture.set_diameter_size(max_diameter)
    
    target_width = 0.01
    target_height = 0.01
    beamline.beam.slits.set_horizontal_gap(target_width)
    beamline.beam.slits.set_vertical_gap(target_height)
    
    beam_width, beam_height = beamline.beam.get_beam_size()
    assert target_width == beam_width
    assert target_height == beam_height

    beam_shape = beamline.beam.get_beam_shape()
    assert beam_shape == BeamShape.RECTANGULAR
