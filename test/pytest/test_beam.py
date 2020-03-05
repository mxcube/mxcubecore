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


def test_beam_atributes(beamline):
    assert not beamline.beam is None, "Beamline.Beam objects is None (not initialized)"

    beam_size = beamline.beam.get_size()

    assert isinstance(beam_size[0], (int, float)), "Horizontal beam size in microns has to be int or float. Now %s" %str(beam_size[0])
    assert isinstance(beam_size[1], (int, float)), "Horizontal beam size in microns has to be int or float. Now %s" %str(beam_size[1])
