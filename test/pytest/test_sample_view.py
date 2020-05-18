#! /usr/bin/env python
# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import pytest

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


@pytest.fixture
def sample_view(beamline):
    assert beamline.sample_view is not None, "sample_view is None (not initialized)"

    # Add a shape to work with
    beamline.sample_view.add_shape_from_mpos(
        [
            {
                "phi": 0,
                "phiz": 0,
                "phiy": 0,
                "sampx": 0,
                "sampy": 0,
                "kappa": 0,
                "kappa_phi": 0,
            }
        ],
        (0, 0),
        "P",
    )

    beamline.sample_view.add_shape_from_mpos(
        [
            {
                "phi": 0,
                "phiz": 0,
                "phiy": 0,
                "sampx": 0,
                "sampy": 0,
                "kappa": 0,
                "kappa_phi": 0,
            },
            {
                "phi": 1,
                "phiz": 1,
                "phiy": 1,
                "sampx": 1,
                "sampy": 1,
                "kappa": 1,
                "kappa_phi": 1,
            },
        ],
        [(0, 0)],
        "L",
    )

    beamline.sample_view.add_shape_from_mpos(
        [
            {
                "phi": 0,
                "phiz": 0,
                "phiy": 0,
                "sampx": 0,
                "sampy": 0,
                "kappa": 0,
                "kappa_phi": 0,
            }
        ],
        [(0, 0)],
        "G",
    )

    yield beamline.sample_view


def test_sample_view_get_shape(sample_view):
    assert len(sample_view.get_points()) == 1

    s = sample_view.get_points()[0]
    assert sample_view.get_shape(s.id) is not None


def test_sample_view_add_shape(sample_view):
    assert len(sample_view.get_points()) == 1
    assert len(sample_view.get_lines()) == 1
    assert len(sample_view.get_grids()) == 1


def test_sample_view_delete_shape(sample_view):
    s = sample_view.get_points()[0]

    sample_view.delete_shape(s.id)
    assert len(sample_view.get_points()) == 0


def test_sample_view_clear_all(sample_view):
    sample_view.clear_all()
    assert len(sample_view.get_shapes()) == 0


def test_sample_view_select_shape(sample_view):
    s = sample_view.get_points()[0]

    sample_view.select_shape(s.id)
    assert sample_view.is_selected(s.id)

    s = sample_view.get_selected_shapes()[0]

    sample_view.de_select_shape(s.id)
    assert not sample_view.is_selected(s.id)

    sample_view.select_shape(s.id)
    assert sample_view.is_selected(s.id)

    sample_view.de_select_all()
    assert len(sample_view.get_selected_shapes()) == 0
