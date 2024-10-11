#! /usr/bin/env python
# encoding: utf-8
#
"""
License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""

__copyright__ = """ Copyright © 2016 -  2023 MXCuBE Collaboration."""
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "30/04/2023"

import operator
from collections import namedtuple, OrderedDict

CrystalClassInfo = namedtuple(
    "CrystalClassInfo",
    (
        "number",
        "name",
        "bravais_lattice",
        "point_group",
        "crystal_system",
        "laue_group",
    ),
)


# Crystal families (one-letter codes) compatible with a solution in a given family
# These are the solutions that could aply using the same axes,
# hence "c" not compatible with "h
SUB_LATTICE_MAP = {
    "a": "a",
    "m": "am",
    "o": "amo",
    "t": "amot",
    "h": "amh",
    "c": "amotc",
}

# Data from https://onlinelibrary.wiley.com/iucr/itc/Cb/ch1o4v0001/
# Laue group names from http://pd.chem.ucl.ac.uk/pdnn/symm2/laue1.htm
# Point group names from https://en.wikipedia.org/wiki/Crystallographic_point_group
CRYSTAL_CLASS_DATA = [
    CrystalClassInfo(0, "", "", "", "", ""),  # Null member, so number == index
    CrystalClassInfo(1, "1P", "aP", "1", "Triclinic", "-1"),
    CrystalClassInfo(2, "-1P", "aP", "-1", "Triclinic", "-1"),
    CrystalClassInfo(3, "2P", "mP", "2", "Monoclinic", "2/m"),
    CrystalClassInfo(4, "2C", "mC", "2", "Monoclinic", "2/m"),
    CrystalClassInfo(5, "mP", "mP", "m", "Monoclinic", "2/m"),
    CrystalClassInfo(6, "mC", "mC", "m", "Monoclinic", "2/m"),
    CrystalClassInfo(7, "2/mP", "mP", "2/m", "Monoclinic", "2/m"),
    CrystalClassInfo(8, "2/mC", "mC", "2/m", "Monoclinic", "2/m"),
    CrystalClassInfo(9, "222P", "oP", "222", "Orthorhombic", "mmm"),
    CrystalClassInfo(10, "222C", "oC", "222", "Orthorhombic", "mmm"),
    CrystalClassInfo(11, "222F", "oF", "222", "Orthorhombic", "mmm"),
    CrystalClassInfo(12, "222I", "oI", "222", "Orthorhombic", "mmm"),
    CrystalClassInfo(13, "mm2P", "oP", "mm2", "Orthorhombic", "mmm"),
    CrystalClassInfo(14, "mm2C", "oC", "mm2", "Orthorhombic", "mmm"),
    CrystalClassInfo(
        15, "2mmC", "oC", "mm2", "Orthorhombic", "mmm"
    ),  # NB was2mmC(Amm2)
    CrystalClassInfo(16, "mm2F", "oF", "mm2", "Orthorhombic", "mmm"),
    CrystalClassInfo(17, "mm2I", "oI", "mm2", "Orthorhombic", "mmm"),
    CrystalClassInfo(18, "mmmP", "oP", "mmm", "Orthorhombic", "mmm"),
    CrystalClassInfo(19, "mmmC", "oC", "mmm", "Orthorhombic", "mmm"),
    CrystalClassInfo(20, "mmmF", "oF", "mmm", "Orthorhombic", "mmm"),
    CrystalClassInfo(21, "mmmI", "oI", "mmm", "Orthorhombic", "mmm"),
    CrystalClassInfo(22, "4P", "tP", "4", "Tetragonal", "4/m"),
    CrystalClassInfo(23, "4I", "tI", "4", "Tetragonal", "4/m"),
    CrystalClassInfo(24, "-4P", "tP", "-4", "Tetragonal", "4/m"),
    CrystalClassInfo(25, "-4I", "tI", "-4", "Tetragonal", "4/m"),
    CrystalClassInfo(26, "4/mP", "tP", "4/m", "Tetragonal", "4/m"),
    CrystalClassInfo(27, "4/mI", "tI", "4/m", "Tetragonal", "4/m"),
    CrystalClassInfo(28, "422P", "tP", "422", "Tetragonal", "4/mmm"),
    CrystalClassInfo(29, "422I", "tI", "422", "Tetragonal", "4/mmm"),
    CrystalClassInfo(30, "4mmP", "tP", "4mm", "Tetragonal", "4/mmm"),
    CrystalClassInfo(31, "4mmI", "tI", "4mm", "Tetragonal", "4/mmm"),
    CrystalClassInfo(32, "-42mP", "tP", "-42m", "Tetragonal", "4/mmm"),
    CrystalClassInfo(33, "-4m2P", "tP", "-42m", "Tetragonal", "4/mmm"),
    CrystalClassInfo(34, "-4m2I", "tI", "-42m", "Tetragonal", "4/mmm"),
    CrystalClassInfo(35, "-42mI", "tI", "-42m", "Tetragonal", "4/mmm"),
    CrystalClassInfo(36, "4/mmmP", "tP", "4/mmm", "Tetragonal", "4/mmm"),
    CrystalClassInfo(37, "4/mmmI", "tI", "4/mmm", "Tetragonal", "4/mmm"),
    CrystalClassInfo(38, "3P", "hP", "3", "Trigonal", "-3"),
    CrystalClassInfo(39, "3R", "hR", "3", "Trigonal", "-3"),
    CrystalClassInfo(40, "-3P", "hP", "-3", "Trigonal", "-3"),
    CrystalClassInfo(41, "-3R", "hR", "-3", "Trigonal", "-3"),
    CrystalClassInfo(42, "312P", "hP", "32", "Trigonal", "-3m"),
    CrystalClassInfo(43, "321P", "hP", "32", "Trigonal", "-3m"),
    CrystalClassInfo(44, "32R", "hR", "32", "Trigonal", "-3m"),
    CrystalClassInfo(45, "3m1P", "hP", "3m", "Trigonal", "-3m"),
    CrystalClassInfo(46, "31mP", "hP", "3m", "Trigonal", "-3m"),
    CrystalClassInfo(47, "3mR", "hR", "3m", "Trigonal", "-3m"),
    CrystalClassInfo(48, "-31mP", "hP", "-3m", "Trigonal", "-3m"),
    CrystalClassInfo(49, "-3m1P", "hP", "-3m", "Trigonal", "-3m"),
    CrystalClassInfo(50, "-3mR", "hR", "-3m", "Trigonal", "-3m"),
    CrystalClassInfo(51, "6P", "hP", "6", "Hexagonal", "6/m"),
    CrystalClassInfo(52, "-6P", "hP", "-6", "Hexagonal", "6/m"),
    CrystalClassInfo(53, "6/mP", "hP", "6/m", "Hexagonal", "6/m"),
    CrystalClassInfo(54, "622P", "hP", "622", "Hexagonal", "6/mmm"),
    CrystalClassInfo(55, "6mmP", "hP", "6mm", "Hexagonal", "6/mmm"),
    CrystalClassInfo(56, "-6m2P", "hP", "-6m2", "Hexagonal", "6/mmm"),
    CrystalClassInfo(57, "-62mP", "hP", "-6m2", "Hexagonal", "6/mmm"),
    CrystalClassInfo(58, "6/mmmP", "hP", "6/mmm", "Hexagonal", "6/mmm"),
    CrystalClassInfo(59, "23P", "cP", "23", "Cubic", "m-3"),
    CrystalClassInfo(60, "23F", "cF", "23", "Cubic", "m-3"),
    CrystalClassInfo(61, "23I", "cI", "23", "Cubic", "m-3"),
    CrystalClassInfo(62, "m-3P", "cP", "m-3", "Cubic", "m-3"),
    CrystalClassInfo(63, "m-3F", "cF", "m-3", "Cubic", "m-3"),
    CrystalClassInfo(64, "m-3I", "cI", "m-3", "Cubic", "m-3"),
    CrystalClassInfo(65, "432P", "cP", "432", "Cubic", "m-3m"),
    CrystalClassInfo(66, "432F", "cF", "432", "Cubic", "m-3m"),
    CrystalClassInfo(67, "432I", "cI", "432", "Cubic", "m-3m"),
    CrystalClassInfo(68, "-43mP", "cP", "-43m", "Cubic", "m-3m"),
    CrystalClassInfo(69, "-43mF", "cF", "-43m", "Cubic", "m-3m"),
    CrystalClassInfo(70, "-43mI", "cI", "-43m", "Cubic", "m-3m"),
    CrystalClassInfo(71, "m-3mP", "cP", "m-3m", "Cubic", "m-3m"),
    CrystalClassInfo(72, "m-3mF", "cF", "m-3m", "Cubic", "m-3m"),
    CrystalClassInfo(73, "m-3mI", "cI", "m-3m", "Cubic", "m-3m"),
]
CRYSTAL_CLASS_MAP = OrderedDict((info.name, info) for info in CRYSTAL_CLASS_DATA)

SpaceGroupInfo = namedtuple(
    "SpaceGroupInfo", ("number", "name", "crystal_class", "synonyms")
)
# Names and synonyms derived from CCP4 (v9.) symop.lib
# Additional synonyms added for SG3-15 (e.g. 'P 21')
# Alternative axis orders added as synonyms for SG17,18
# SG 146,148,155,160,161,166,167 are given names starting with 'R',
# with 'H' names as synonyms
# Crystal class names from https://onlinelibrary.wiley.com/iucr/itc/Cb/ch1o4v0001/
SPACEGROUP_DATA = [
    SpaceGroupInfo(number=1, name="P1", crystal_class="1P", synonyms=("P 1",)),
    SpaceGroupInfo(number=2, name="P-1", crystal_class="-1P", synonyms=("P -1",)),
    SpaceGroupInfo(
        number=3, name="P2", crystal_class="2P", synonyms=("P 1 2 1", "P121", "P 2")
    ),
    SpaceGroupInfo(
        number=4, name="P21", crystal_class="2P", synonyms=("P 1 21 1", "P1211", "P 21")
    ),
    SpaceGroupInfo(
        number=5, name="C2", crystal_class="2C", synonyms=("C 1 2 1", "C121", "C 2")
    ),
    SpaceGroupInfo(
        number=6, name="Pm", crystal_class="mP", synonyms=("P 1 m 1", "P1m1", "P m")
    ),
    SpaceGroupInfo(
        number=7, name="Pc", crystal_class="mP", synonyms=("P 1 c 1", "P1c1", "P c")
    ),
    SpaceGroupInfo(
        number=8, name="Cm", crystal_class="mC", synonyms=("C 1 m 1", "C1m1", "C m")
    ),
    SpaceGroupInfo(
        number=9, name="Cc", crystal_class="mC", synonyms=("C 1 c 1", "C1c1", "C c")
    ),
    SpaceGroupInfo(
        number=10,
        name="P2/m",
        crystal_class="2/mP",
        synonyms=("P 1 2/m 1", "P12/m1", "P 2/m"),
    ),
    SpaceGroupInfo(
        number=11,
        name="P21/m",
        crystal_class="2/mP",
        synonyms=("P 1 21/m 1", "P121/m1", "P 21/m"),
    ),
    SpaceGroupInfo(
        number=12,
        name="C2/m",
        crystal_class="2/mC",
        synonyms=("C 1 2/m 1", "C12/m1", "C 2/m"),
    ),
    SpaceGroupInfo(
        number=13,
        name="P2/c",
        crystal_class="2/mP",
        synonyms=("P 1 2/c 1", "P12/c1", "P 2/c"),
    ),
    SpaceGroupInfo(
        number=14,
        name="P21/c",
        crystal_class="2/mP",
        synonyms=("P 1 21/c 1", "P121/c1", "P 21/c"),
    ),
    SpaceGroupInfo(
        number=15,
        name="C2/c",
        crystal_class="2/mC",
        synonyms=("C 1 2/c 1", "C12/c1", "C 2/c"),
    ),
    SpaceGroupInfo(number=16, name="P222", crystal_class="222P", synonyms=("P 2 2 2",)),
    SpaceGroupInfo(
        number=17,
        name="P2221",
        crystal_class="222P",
        synonyms=("P 2 2 21", "P2212", "P 2 21 2", "P2122", "P 21 2 2"),
    ),
    SpaceGroupInfo(
        number=18,
        name="P21212",
        crystal_class="222P",
        synonyms=("P 21 21 2", "P21221", "P 21 2 21", "P22121", "P 2 21 21"),
    ),
    SpaceGroupInfo(
        number=19, name="P212121", crystal_class="222P", synonyms=("P 21 21 21",)
    ),
    SpaceGroupInfo(
        number=20, name="C2221", crystal_class="222C", synonyms=("C 2 2 21",)
    ),
    SpaceGroupInfo(number=21, name="C222", crystal_class="222C", synonyms=("C 2 2 2",)),
    SpaceGroupInfo(number=22, name="F222", crystal_class="222F", synonyms=("F 2 2 2",)),
    SpaceGroupInfo(number=23, name="I222", crystal_class="222I", synonyms=("I 2 2 2",)),
    SpaceGroupInfo(
        number=24, name="I212121", crystal_class="222I", synonyms=("I 21 21 21",)
    ),
    SpaceGroupInfo(number=25, name="Pmm2", crystal_class="mm2P", synonyms=("P m m 2",)),
    SpaceGroupInfo(
        number=26, name="Pmc21", crystal_class="mm2P", synonyms=("P m c 21",)
    ),
    SpaceGroupInfo(number=27, name="Pcc2", crystal_class="mm2P", synonyms=("P c c 2",)),
    SpaceGroupInfo(number=28, name="Pma2", crystal_class="mm2P", synonyms=("P m a 2",)),
    SpaceGroupInfo(
        number=29, name="Pca21", crystal_class="mm2P", synonyms=("P c a 21",)
    ),
    SpaceGroupInfo(number=30, name="Pnc2", crystal_class="mm2P", synonyms=("P n c 2",)),
    SpaceGroupInfo(
        number=31, name="Pmn21", crystal_class="mm2P", synonyms=("P m n 21",)
    ),
    SpaceGroupInfo(number=32, name="Pba2", crystal_class="mm2P", synonyms=("P b a 2",)),
    SpaceGroupInfo(
        number=33, name="Pna21", crystal_class="mm2P", synonyms=("P n a 21",)
    ),
    SpaceGroupInfo(number=34, name="Pnn2", crystal_class="mm2P", synonyms=("P n n 2",)),
    SpaceGroupInfo(number=35, name="Cmm2", crystal_class="mm2C", synonyms=("C m m 2",)),
    SpaceGroupInfo(
        number=36, name="Cmc21", crystal_class="mm2C", synonyms=("C m c 21",)
    ),
    SpaceGroupInfo(number=37, name="Ccc2", crystal_class="mm2C", synonyms=("C c c 2",)),
    SpaceGroupInfo(number=38, name="Amm2", crystal_class="2mmC", synonyms=("A m m 2",)),
    SpaceGroupInfo(number=39, name="Abm2", crystal_class="2mmC", synonyms=("A b m 2",)),
    SpaceGroupInfo(number=40, name="Ama2", crystal_class="2mmC", synonyms=("A m a 2",)),
    SpaceGroupInfo(number=41, name="Aba2", crystal_class="2mmC", synonyms=("A b a 2",)),
    SpaceGroupInfo(number=42, name="Fmm2", crystal_class="mm2F", synonyms=("F m m 2",)),
    SpaceGroupInfo(number=43, name="Fdd2", crystal_class="mm2F", synonyms=("F d d 2",)),
    SpaceGroupInfo(number=44, name="Imm2", crystal_class="mm2I", synonyms=("I m m 2",)),
    SpaceGroupInfo(number=45, name="Iba2", crystal_class="mm2I", synonyms=("I b a 2",)),
    SpaceGroupInfo(number=46, name="Ima2", crystal_class="mm2I", synonyms=("I m a 2",)),
    SpaceGroupInfo(
        number=47,
        name="Pmmm",
        crystal_class="mmmP",
        synonyms=("P 2/m 2/m 2/m", "P2/m2/m2/m", "P m m m"),
    ),
    SpaceGroupInfo(
        number=48,
        name="Pnnn",
        crystal_class="mmmP",
        synonyms=("P 2/n 2/n 2/n", "P2/n2/n2/n", "P n n n"),
    ),
    SpaceGroupInfo(
        number=49,
        name="Pccm",
        crystal_class="mmmP",
        synonyms=("P 2/c 2/c 2/m", "P2/c2/c2/m", "P c c m"),
    ),
    SpaceGroupInfo(
        number=50,
        name="Pban",
        crystal_class="mmmP",
        synonyms=("P 2/b 2/a 2/n", "P2/b2/a2/n", "P b a n"),
    ),
    SpaceGroupInfo(
        number=51,
        name="Pmma",
        crystal_class="mmmP",
        synonyms=("P 21/m 2/m 2/a", "P21/m2/m2/a", "P m m a"),
    ),
    SpaceGroupInfo(
        number=52,
        name="Pnna",
        crystal_class="mmmP",
        synonyms=("P 2/n 21/n 2/a", "P2/n21/n2/a", "P n n a"),
    ),
    SpaceGroupInfo(
        number=53,
        name="Pmna",
        crystal_class="mmmP",
        synonyms=("P 2/m 2/n 21/a", "P2/m2/n21/a", "P m n a"),
    ),
    SpaceGroupInfo(
        number=54,
        name="Pcca",
        crystal_class="mmmP",
        synonyms=("P 21/c 2/c 2/a", "P21/c2/c2/a", "P c c a"),
    ),
    SpaceGroupInfo(
        number=55,
        name="Pbam",
        crystal_class="mmmP",
        synonyms=("P 21/b 21/a 2/m", "P21/b21/a2/m", "P b a m"),
    ),
    SpaceGroupInfo(
        number=56,
        name="Pccn",
        crystal_class="mmmP",
        synonyms=("P 21/c 21/c 2/n", "P21/c21/c2/n", "P c c n"),
    ),
    SpaceGroupInfo(
        number=57,
        name="Pbcm",
        crystal_class="mmmP",
        synonyms=("P 2/b 21/c 21/m", "P2/b21/c21/m", "P b c m"),
    ),
    SpaceGroupInfo(
        number=58,
        name="Pnnm",
        crystal_class="mmmP",
        synonyms=("P 21/n 21/n 2/m", "P21/n21/n2/m", "P n n m"),
    ),
    SpaceGroupInfo(
        number=59,
        name="Pmmn",
        crystal_class="mmmP",
        synonyms=("P 21/m 21/m 2/n", "P21/m21/m2/n", "P m m n"),
    ),
    SpaceGroupInfo(
        number=60,
        name="Pbcn",
        crystal_class="mmmP",
        synonyms=("P 21/b 2/c 21/n", "P21/b2/c21/n", "P b c n"),
    ),
    SpaceGroupInfo(
        number=61,
        name="Pbca",
        crystal_class="mmmP",
        synonyms=("P 21/b 21/c 21/a", "P21/b21/c21/a", "P b c a"),
    ),
    SpaceGroupInfo(
        number=62,
        name="Pnma",
        crystal_class="mmmP",
        synonyms=("P 21/n 21/m 21/a", "P21/n21/m21/a", "P n m a"),
    ),
    SpaceGroupInfo(
        number=63,
        name="Cmcm",
        crystal_class="mmmC",
        synonyms=("C 2/m 2/c 21/m", "C2/m2/c21/m", "C m c m"),
    ),
    SpaceGroupInfo(
        number=64,
        name="Cmca",
        crystal_class="mmmC",
        synonyms=("C 2/m 2/c 21/a", "C2/m2/c21/a", "C m c a"),
    ),
    SpaceGroupInfo(
        number=65,
        name="Cmmm",
        crystal_class="mmmC",
        synonyms=("C 2/m 2/m 2/m", "C2/m2/m2/m", "C m m m"),
    ),
    SpaceGroupInfo(
        number=66,
        name="Cccm",
        crystal_class="mmmC",
        synonyms=("C 2/c 2/c 2/m", "C2/c2/c2/m", "C c c m"),
    ),
    SpaceGroupInfo(
        number=67,
        name="Cmma",
        crystal_class="mmmC",
        synonyms=("C 2/m 2/m 2/a", "C2/m2/m2/a", "C m m a"),
    ),
    SpaceGroupInfo(
        number=68,
        name="Ccca",
        crystal_class="mmmC",
        synonyms=("C 2/c 2/c 2/a", "C2/c2/c2/a", "C c c a"),
    ),
    SpaceGroupInfo(
        number=69,
        name="Fmmm",
        crystal_class="mmmF",
        synonyms=("F 2/m 2/m 2/m", "F2/m2/m2/m", "F m m m"),
    ),
    SpaceGroupInfo(
        number=70,
        name="Fddd",
        crystal_class="mmmF",
        synonyms=("F 2/d 2/d 2/d", "F2/d2/d2/d", "F d d d"),
    ),
    SpaceGroupInfo(
        number=71,
        name="Immm",
        crystal_class="mmmI",
        synonyms=("I 2/m 2/m 2/m", "I2/m2/m2/m", "I m m m"),
    ),
    SpaceGroupInfo(
        number=72,
        name="Ibam",
        crystal_class="mmmI",
        synonyms=("I 2/b 2/a 2/m", "I2/b2/a2/m", "I b a m"),
    ),
    SpaceGroupInfo(
        number=73,
        name="Ibca",
        crystal_class="mmmI",
        synonyms=("I 21/b 21/c 21/a", "I21/b21/c21/a", "I b c a"),
    ),
    SpaceGroupInfo(
        number=74,
        name="Imma",
        crystal_class="mmmI",
        synonyms=("I 21/m 21/m 21/a", "I21/m21/m21/a", "I m m a"),
    ),
    SpaceGroupInfo(number=75, name="P4", crystal_class="4P", synonyms=("P 4",)),
    SpaceGroupInfo(number=76, name="P41", crystal_class="4P", synonyms=("P 41",)),
    SpaceGroupInfo(number=77, name="P42", crystal_class="4P", synonyms=("P 42",)),
    SpaceGroupInfo(number=78, name="P43", crystal_class="4P", synonyms=("P 43",)),
    SpaceGroupInfo(number=79, name="I4", crystal_class="4I", synonyms=("I 4",)),
    SpaceGroupInfo(number=80, name="I41", crystal_class="4I", synonyms=("I 41",)),
    SpaceGroupInfo(number=81, name="P-4", crystal_class="-4P", synonyms=("P -4",)),
    SpaceGroupInfo(number=82, name="I-4", crystal_class="-4I", synonyms=("I -4",)),
    SpaceGroupInfo(number=83, name="P4/m", crystal_class="4/mP", synonyms=("P 4/m",)),
    SpaceGroupInfo(number=84, name="P42/m", crystal_class="4/mP", synonyms=("P 42/m",)),
    SpaceGroupInfo(number=85, name="P4/n", crystal_class="4/mP", synonyms=("P 4/n",)),
    SpaceGroupInfo(number=86, name="P42/n", crystal_class="4/mP", synonyms=("P 42/n",)),
    SpaceGroupInfo(number=87, name="I4/m", crystal_class="4/mI", synonyms=("I 4/m",)),
    SpaceGroupInfo(number=88, name="I41/a", crystal_class="4/mI", synonyms=("I 41/a",)),
    SpaceGroupInfo(number=89, name="P422", crystal_class="422P", synonyms=("P 4 2 2",)),
    SpaceGroupInfo(
        number=90, name="P4212", crystal_class="422P", synonyms=("P 4 21 2",)
    ),
    SpaceGroupInfo(
        number=91, name="P4122", crystal_class="422P", synonyms=("P 41 2 2",)
    ),
    SpaceGroupInfo(
        number=92, name="P41212", crystal_class="422P", synonyms=("P 41 21 2",)
    ),
    SpaceGroupInfo(
        number=93, name="P4222", crystal_class="422P", synonyms=("P 42 2 2",)
    ),
    SpaceGroupInfo(
        number=94, name="P42212", crystal_class="422P", synonyms=("P 42 21 2",)
    ),
    SpaceGroupInfo(
        number=95, name="P4322", crystal_class="422P", synonyms=("P 43 2 2",)
    ),
    SpaceGroupInfo(
        number=96, name="P43212", crystal_class="422P", synonyms=("P 43 21 2",)
    ),
    SpaceGroupInfo(number=97, name="I422", crystal_class="422I", synonyms=("I 4 2 2",)),
    SpaceGroupInfo(
        number=98, name="I4122", crystal_class="422I", synonyms=("I 41 2 2",)
    ),
    SpaceGroupInfo(number=99, name="P4mm", crystal_class="4mmP", synonyms=("P 4 m m",)),
    SpaceGroupInfo(
        number=100, name="P4bm", crystal_class="4mmP", synonyms=("P 4 b m",)
    ),
    SpaceGroupInfo(
        number=101, name="P42cm", crystal_class="4mmP", synonyms=("P 42 c m",)
    ),
    SpaceGroupInfo(
        number=102, name="P42nm", crystal_class="4mmP", synonyms=("P 42 n m",)
    ),
    SpaceGroupInfo(
        number=103, name="P4cc", crystal_class="4mmP", synonyms=("P 4 c c",)
    ),
    SpaceGroupInfo(
        number=104, name="P4nc", crystal_class="4mmP", synonyms=("P 4 n c",)
    ),
    SpaceGroupInfo(
        number=105, name="P42mc", crystal_class="4mmP", synonyms=("P 42 m c",)
    ),
    SpaceGroupInfo(
        number=106, name="P42bc", crystal_class="4mmP", synonyms=("P 42 b c",)
    ),
    SpaceGroupInfo(
        number=107, name="I4mm", crystal_class="4mmI", synonyms=("I 4 m m",)
    ),
    SpaceGroupInfo(
        number=108, name="I4cm", crystal_class="4mmI", synonyms=("I 4 c m",)
    ),
    SpaceGroupInfo(
        number=109, name="I41md", crystal_class="4mmI", synonyms=("I 41 m d",)
    ),
    SpaceGroupInfo(
        number=110, name="I41cd", crystal_class="4mmI", synonyms=("I 41 c d",)
    ),
    SpaceGroupInfo(
        number=111, name="P-42m", crystal_class="-42mP", synonyms=("P -4 2 m",)
    ),
    SpaceGroupInfo(
        number=112, name="P-42c", crystal_class="-42mP", synonyms=("P -4 2 c",)
    ),
    SpaceGroupInfo(
        number=113, name="P-421m", crystal_class="-42mP", synonyms=("P -4 21 m",)
    ),
    SpaceGroupInfo(
        number=114, name="P-421c", crystal_class="-42mP", synonyms=("P -4 21 c",)
    ),
    SpaceGroupInfo(
        number=115, name="P-4m2", crystal_class="-4m2P", synonyms=("P -4 m 2",)
    ),
    SpaceGroupInfo(
        number=116, name="P-4c2", crystal_class="-4m2P", synonyms=("P -4 c 2",)
    ),
    SpaceGroupInfo(
        number=117, name="P-4b2", crystal_class="-4m2P", synonyms=("P -4 b 2",)
    ),
    SpaceGroupInfo(
        number=118, name="P-4n2", crystal_class="-4m2P", synonyms=("P -4 n 2",)
    ),
    SpaceGroupInfo(
        number=119, name="I-4m2", crystal_class="-4m2I", synonyms=("I -4 m 2",)
    ),
    SpaceGroupInfo(
        number=120, name="I-4c2", crystal_class="-4m2I", synonyms=("I -4 c 2",)
    ),
    SpaceGroupInfo(
        number=121, name="I-42m", crystal_class="-42mI", synonyms=("I -4 2 m",)
    ),
    SpaceGroupInfo(
        number=122, name="I-42d", crystal_class="-42mI", synonyms=("I -4 2 d",)
    ),
    SpaceGroupInfo(
        number=123,
        name="P4/mmm",
        crystal_class="4/mmmP",
        synonyms=("P 4/m 2/m 2/m", "P4/m2/m2/m", "P4/m m m"),
    ),
    SpaceGroupInfo(
        number=124,
        name="P4/mcc",
        crystal_class="4/mmmP",
        synonyms=("P 4/m 2/c 2/c", "P4/m2/c2/c", "P4/m c c"),
    ),
    SpaceGroupInfo(
        number=125,
        name="P4/nbm",
        crystal_class="4/mmmP",
        synonyms=("P 4/n 2/b 2/m", "P4/n2/b2/m", "P4/n b m"),
    ),
    SpaceGroupInfo(
        number=126,
        name="P4/nnc",
        crystal_class="4/mmmP",
        synonyms=("P 4/n 2/n 2/c", "P4/n2/n2/c", "P4/n n c"),
    ),
    SpaceGroupInfo(
        number=127,
        name="P4/mbm",
        crystal_class="4/mmmP",
        synonyms=("P 4/m 21/b 2/m", "P4/m21/b2/m", "P4/m b m"),
    ),
    SpaceGroupInfo(
        number=128,
        name="P4/mnc",
        crystal_class="4/mmmP",
        synonyms=("P 4/m 21/n 2/c", "P4/m21/n2/c", "P4/m n c"),
    ),
    SpaceGroupInfo(
        number=129,
        name="P4/nmm",
        crystal_class="4/mmmP",
        synonyms=("P 4/n 21/m 2/m", "P4/n21/m2/m", "P4/n m m"),
    ),
    SpaceGroupInfo(
        number=130,
        name="P4/ncc",
        crystal_class="4/mmmP",
        synonyms=("P 4/n 2/c 2/c", "P4/n2/c2/c", "P4/n c c"),
    ),
    SpaceGroupInfo(
        number=131,
        name="P42/mmc",
        crystal_class="4/mmmP",
        synonyms=("P 42/m 2/m 2/c", "P42/m2/m2/c", "P42/m m c"),
    ),
    SpaceGroupInfo(
        number=132,
        name="P42/mcm",
        crystal_class="4/mmmP",
        synonyms=("P 42/m 2/c 2/m", "P42/m2/c2/m", "P42/m c m"),
    ),
    SpaceGroupInfo(
        number=133,
        name="P42/nbc",
        crystal_class="4/mmmP",
        synonyms=("P 42/n 2/b 2/c", "P42/n2/b2/c", "P42/n b c"),
    ),
    SpaceGroupInfo(
        number=134,
        name="P42/nnm",
        crystal_class="4/mmmP",
        synonyms=("P 42/n 2/n 2/m", "P42/n2/n2/m", "P42/n n m"),
    ),
    SpaceGroupInfo(
        number=135,
        name="P42/mbc",
        crystal_class="4/mmmP",
        synonyms=("P 42/m 21/b 2/c", "P42/m21/b2/c", "P42/m b c"),
    ),
    SpaceGroupInfo(
        number=136,
        name="P42/mnm",
        crystal_class="4/mmmP",
        synonyms=("P 42/m 21/n 2/m", "P42/m21/n2/m", "P42/m n m"),
    ),
    SpaceGroupInfo(
        number=137,
        name="P42/nmc",
        crystal_class="4/mmmP",
        synonyms=("P 42/n 21/m 2/c", "P42/n21/m2/c", "P42/n m c"),
    ),
    SpaceGroupInfo(
        number=138,
        name="P42/ncm",
        crystal_class="4/mmmP",
        synonyms=("P 42/n 21/c 2/m", "P42/n21/c2/m", "P42/n c m"),
    ),
    SpaceGroupInfo(
        number=139,
        name="I4/mmm",
        crystal_class="4/mmmI",
        synonyms=("I 4/m 2/m 2/m", "I4/m2/m2/m", "I4/m m m"),
    ),
    SpaceGroupInfo(
        number=140,
        name="I4/mcm",
        crystal_class="4/mmmI",
        synonyms=("I 4/m 2/c 2/m", "I4/m2/c2/m", "I4/m c m"),
    ),
    SpaceGroupInfo(
        number=141,
        name="I41/amd",
        crystal_class="4/mmmI",
        synonyms=("I 41/a 2/m 2/d", "I41/a2/m2/d", "I41/a m d"),
    ),
    SpaceGroupInfo(
        number=142,
        name="I41/acd",
        crystal_class="4/mmmI",
        synonyms=("I 41/a 2/c 2/d", "I41/a2/c2/d", "I41/a c d"),
    ),
    SpaceGroupInfo(number=143, name="P3", crystal_class="3P", synonyms=("P 3",)),
    SpaceGroupInfo(number=144, name="P31", crystal_class="3P", synonyms=("P 31",)),
    SpaceGroupInfo(number=145, name="P32", crystal_class="3P", synonyms=("P 32",)),
    SpaceGroupInfo(
        number=146, name="R3", crystal_class="3R", synonyms=("H 3", "H3", " R 3")
    ),
    SpaceGroupInfo(number=147, name="P-3", crystal_class="-3P", synonyms=("P -3",)),
    SpaceGroupInfo(
        number=148, name="R-3", crystal_class="-3R", synonyms=("H -3", "H-3", "R -3")
    ),
    SpaceGroupInfo(
        number=149, name="P312", crystal_class="312P", synonyms=("P 3 1 2",)
    ),
    SpaceGroupInfo(
        number=150, name="P321", crystal_class="321P", synonyms=("P 3 2 1",)
    ),
    SpaceGroupInfo(
        number=151, name="P3112", crystal_class="312P", synonyms=("P 31 1 2",)
    ),
    SpaceGroupInfo(
        number=152, name="P3121", crystal_class="321P", synonyms=("P 31 2 1",)
    ),
    SpaceGroupInfo(
        number=153, name="P3212", crystal_class="312P", synonyms=("P 32 1 2",)
    ),
    SpaceGroupInfo(
        number=154, name="P3221", crystal_class="321P", synonyms=("P 32 2 1",)
    ),
    SpaceGroupInfo(
        number=155, name="R32", crystal_class="32R", synonyms=("H 3 2", "H32", "R 3 2")
    ),
    SpaceGroupInfo(
        number=156, name="P3m1", crystal_class="3m1P", synonyms=("P 3 m 1",)
    ),
    SpaceGroupInfo(
        number=157, name="P31m", crystal_class="31mP", synonyms=("P 3 1 m",)
    ),
    SpaceGroupInfo(
        number=158, name="P3c1", crystal_class="3m1P", synonyms=("P 3 c 1",)
    ),
    SpaceGroupInfo(
        number=159, name="P31c", crystal_class="31mP", synonyms=("P 3 1 c",)
    ),
    SpaceGroupInfo(
        number=160, name="R3m", crystal_class="3mR", synonyms=("H 3 m", "H3m", "R 3 m")
    ),
    SpaceGroupInfo(
        number=161, name="R3c", crystal_class="3mR", synonyms=("H 3 c", "H3c", "R 3 c")
    ),
    SpaceGroupInfo(
        number=162,
        name="P-31m",
        crystal_class="-31mP",
        synonyms=("P -3 1 2/m", "P-312/m", "P -3 1 m"),
    ),
    SpaceGroupInfo(
        number=163,
        name="P-31c",
        crystal_class="-31mP",
        synonyms=("P -3 1 2/c", "P-312/c", "P -3 1 c"),
    ),
    SpaceGroupInfo(
        number=164,
        name="P-3m1",
        crystal_class="-3m1P",
        synonyms=("P -3 2/m 1", "P-32/m1", "P -3 m 1"),
    ),
    SpaceGroupInfo(
        number=165,
        name="P-3c1",
        crystal_class="-3m1P",
        synonyms=("P -3 2/c 1", "P-32/c1", "P -3 c 1"),
    ),
    SpaceGroupInfo(
        number=166,
        name="R-3m",
        crystal_class="-3mR",
        synonyms=(
            "H-3m",
            "H -3 2/m",
            "H-32/m",
            "H -3 m",
            "R -3 2/m",
            "R-32/m",
            "R -3 m",
        ),
    ),
    SpaceGroupInfo(
        number=167,
        name="R-3c",
        crystal_class="-3mR",
        synonyms=(
            "H-3c",
            "H -3 2/c",
            "H-32/c",
            "H -3 c",
            "R -3 2/c",
            "R-32/c",
            "R -3 c",
        ),
    ),
    SpaceGroupInfo(number=168, name="P6", crystal_class="6P", synonyms=("P 6",)),
    SpaceGroupInfo(number=169, name="P61", crystal_class="6P", synonyms=("P 61",)),
    SpaceGroupInfo(number=170, name="P65", crystal_class="6P", synonyms=("P 65",)),
    SpaceGroupInfo(number=171, name="P62", crystal_class="6P", synonyms=("P 62",)),
    SpaceGroupInfo(number=172, name="P64", crystal_class="6P", synonyms=("P 64",)),
    SpaceGroupInfo(number=173, name="P63", crystal_class="6P", synonyms=("P 63",)),
    SpaceGroupInfo(number=174, name="P-6", crystal_class="-6P", synonyms=("P -6",)),
    SpaceGroupInfo(number=175, name="P6/m", crystal_class="6/mP", synonyms=("P 6/m",)),
    SpaceGroupInfo(
        number=176, name="P63/m", crystal_class="6/mP", synonyms=("P 63/m",)
    ),
    SpaceGroupInfo(
        number=177, name="P622", crystal_class="622P", synonyms=("P 6 2 2",)
    ),
    SpaceGroupInfo(
        number=178, name="P6122", crystal_class="622P", synonyms=("P 61 2 2",)
    ),
    SpaceGroupInfo(
        number=179, name="P6522", crystal_class="622P", synonyms=("P 65 2 2",)
    ),
    SpaceGroupInfo(
        number=180, name="P6222", crystal_class="622P", synonyms=("P 62 2 2",)
    ),
    SpaceGroupInfo(
        number=181, name="P6422", crystal_class="622P", synonyms=("P 64 2 2",)
    ),
    SpaceGroupInfo(
        number=182, name="P6322", crystal_class="622P", synonyms=("P 63 2 2",)
    ),
    SpaceGroupInfo(
        number=183, name="P6mm", crystal_class="6mmP", synonyms=("P 6 m m",)
    ),
    SpaceGroupInfo(
        number=184, name="P6cc", crystal_class="6mmP", synonyms=("P 6 c c",)
    ),
    SpaceGroupInfo(
        number=185, name="P63cm", crystal_class="6mmP", synonyms=("P 63 c m",)
    ),
    SpaceGroupInfo(
        number=186, name="P63mc", crystal_class="6mmP", synonyms=("P 63 m c",)
    ),
    SpaceGroupInfo(
        number=187, name="P-6m2", crystal_class="-6m2P", synonyms=("P -6 m 2",)
    ),
    SpaceGroupInfo(
        number=188, name="P-6c2", crystal_class="-6m2P", synonyms=("P -6 c 2",)
    ),
    SpaceGroupInfo(
        number=189, name="P-62m", crystal_class="-62mP", synonyms=("P -6 2 m",)
    ),
    SpaceGroupInfo(
        number=190, name="P-62c", crystal_class="-62mP", synonyms=("P -6 2 c",)
    ),
    SpaceGroupInfo(
        number=191,
        name="P6/mmm",
        crystal_class="6/mmmP",
        synonyms=("P 6/m 2/m 2/m", "P6/m2/m2/m", "P 6/m m m"),
    ),
    SpaceGroupInfo(
        number=192,
        name="P6/mcc",
        crystal_class="6/mmmP",
        synonyms=("P 6/m 2/c 2/c", "P6/m2/c2/c", "P 6/m c c"),
    ),
    SpaceGroupInfo(
        number=193,
        name="P63/mcm",
        crystal_class="6/mmmP",
        synonyms=("P 63/m 2/c 2/m", "P63/m2/c2/m", "P 63/m c m"),
    ),
    SpaceGroupInfo(
        number=194,
        name="P63/mmc",
        crystal_class="6/mmmP",
        synonyms=("P 63/m 2/m 2/c", "P63/m2/m2/c", "P 63/m m c"),
    ),
    SpaceGroupInfo(number=195, name="P23", crystal_class="23P", synonyms=("P 2 3",)),
    SpaceGroupInfo(number=196, name="F23", crystal_class="23F", synonyms=("F 2 3",)),
    SpaceGroupInfo(number=197, name="I23", crystal_class="23I", synonyms=("I 2 3",)),
    SpaceGroupInfo(number=198, name="P213", crystal_class="23P", synonyms=("P 21 3",)),
    SpaceGroupInfo(number=199, name="I213", crystal_class="23I", synonyms=("I 21 3",)),
    SpaceGroupInfo(
        number=200,
        name="Pm-3",
        crystal_class="m-3P",
        synonyms=("P 2/m -3", "P2/m-3", "P m -3"),
    ),
    SpaceGroupInfo(
        number=201,
        name="Pn-3",
        crystal_class="m-3P",
        synonyms=("P 2/n -3", "P2/n-3", "P n -3"),
    ),
    SpaceGroupInfo(
        number=202,
        name="Fm-3",
        crystal_class="m-3F",
        synonyms=("F 2/m -3", "F2/m-3", "F m -3"),
    ),
    SpaceGroupInfo(
        number=203,
        name="Fd-3",
        crystal_class="m-3F",
        synonyms=("F 2/d -3", "F2/d-3", "F d -3"),
    ),
    SpaceGroupInfo(
        number=204,
        name="Im-3",
        crystal_class="m-3I",
        synonyms=("I 2/m -3", "I2/m-3", "I m -3"),
    ),
    SpaceGroupInfo(
        number=205,
        name="Pa-3",
        crystal_class="m-3P",
        synonyms=("P 21/a -3", "P21/a-3", "P a -3"),
    ),
    SpaceGroupInfo(
        number=206,
        name="Ia-3",
        crystal_class="m-3I",
        synonyms=("I 21/a -3", "I21/a-3", "I a -3"),
    ),
    SpaceGroupInfo(
        number=207, name="P432", crystal_class="432P", synonyms=("P 4 3 2",)
    ),
    SpaceGroupInfo(
        number=208, name="P4232", crystal_class="432P", synonyms=("P 42 3 2",)
    ),
    SpaceGroupInfo(
        number=209, name="F432", crystal_class="432F", synonyms=("F 4 3 2",)
    ),
    SpaceGroupInfo(
        number=210, name="F4132", crystal_class="432F", synonyms=("F 41 3 2",)
    ),
    SpaceGroupInfo(
        number=211, name="I432", crystal_class="432I", synonyms=("I 4 3 2",)
    ),
    SpaceGroupInfo(
        number=212, name="P4332", crystal_class="432P", synonyms=("P 43 3 2",)
    ),
    SpaceGroupInfo(
        number=213, name="P4132", crystal_class="432P", synonyms=("P 41 3 2",)
    ),
    SpaceGroupInfo(
        number=214, name="I4132", crystal_class="432I", synonyms=("I 41 3 2",)
    ),
    SpaceGroupInfo(
        number=215, name="P-43m", crystal_class="-43mP", synonyms=("P -4 3 m",)
    ),
    SpaceGroupInfo(
        number=216, name="F-43m", crystal_class="-43mF", synonyms=("F -4 3 m",)
    ),
    SpaceGroupInfo(
        number=217, name="I-43m", crystal_class="-43mI", synonyms=("I -4 3 m",)
    ),
    SpaceGroupInfo(
        number=218, name="P-43n", crystal_class="-43mP", synonyms=("P -4 3 n",)
    ),
    SpaceGroupInfo(
        number=219, name="F-43c", crystal_class="-43mF", synonyms=("F -4 3 c",)
    ),
    SpaceGroupInfo(
        number=220, name="I-43d", crystal_class="-43mI", synonyms=("I -4 3 d",)
    ),
    SpaceGroupInfo(
        number=221,
        name="Pm-3m",
        crystal_class="m-3mP",
        synonyms=("P 4/m -3 2/m", "P4/m-32/m", "P m -3 m"),
    ),
    SpaceGroupInfo(
        number=222,
        name="Pn-3n",
        crystal_class="m-3mP",
        synonyms=("P 4/n -3 2/n", "P4/n-32/n", "P n -3 n"),
    ),
    SpaceGroupInfo(
        number=223,
        name="Pm-3n",
        crystal_class="m-3mP",
        synonyms=("P 42/m -3 2/n", "P42/m-32/n", "P m -3 n"),
    ),
    SpaceGroupInfo(
        number=224,
        name="Pn-3m",
        crystal_class="m-3mP",
        synonyms=("P 42/n -3 2/m", "P42/n-32/m", "P n -3 m"),
    ),
    SpaceGroupInfo(
        number=225,
        name="Fm-3m",
        crystal_class="m-3mF",
        synonyms=("F 4/m -3 2/m", "F4/m-32/m", "F m -3 m"),
    ),
    SpaceGroupInfo(
        number=226,
        name="Fm-3c",
        crystal_class="m-3mF",
        synonyms=("F 4/m -3 2/c", "F4/m-32/c", "F m -3 c"),
    ),
    SpaceGroupInfo(
        number=227,
        name="Fd-3m",
        crystal_class="m-3mF",
        synonyms=("F 41/d -3 2/m", "F41/d-32/m", "F d -3 m"),
    ),
    SpaceGroupInfo(
        number=228,
        name="Fd-3c",
        crystal_class="m-3mF",
        synonyms=("F 41/d -3 2/c", "F41/d-32/c", "F d -3 c"),
    ),
    SpaceGroupInfo(
        number=229,
        name="Im-3m",
        crystal_class="m-3mI",
        synonyms=("I 4/m -3 2/m", "I4/m-32/m", "I m -3 m"),
    ),
    SpaceGroupInfo(
        number=230,
        name="Ia-3d",
        crystal_class="m-3mI",
        synonyms=("I 41/a -3 2/d", "I41/a-32/d", "I a -3 d"),
    ),
]
SPACEGROUP_MAP = OrderedDict((info.name, info) for info in SPACEGROUP_DATA)
for tpl in SPACEGROUP_DATA:
    # Done this way so that first elemets in map are on item per spacegroup
    for tag in tpl.synonyms:
        SPACEGROUP_MAP[tag] = tpl

# Space group names for space groups compatible with chiral molecules,
# i.e. that do not contain mirror planes or centres of symmetry,
# in order of space group number
XTAL_SPACEGROUPS = [""] + [
    info.name
    for info in SPACEGROUP_DATA
    if CRYSTAL_CLASS_MAP[info.crystal_class].point_group.isdigit()
]

BRAVAIS_LATTICES = (
    "aP",
    "mP",
    "mC",
    "oP",
    "oC",
    "oF",
    "oI",
    "tP",
    "tI",
    "hP",
    "hR",
    "cP",
    "cF",
    "cI",
)
UI_LATTICES = BRAVAIS_LATTICES + ("mI",)


def filter_crystal_classes(bravais_lattice, crystal_classes=()):
    """Filter crystal classes to select those compatible with selected Bravais lattice

    including sublattices

    Args:
        bravais_lattice: str
        crystal_classes: Sequence

    Returns:
        tuople

    """
    compatibles = SUB_LATTICE_MAP[bravais_lattice[0]]
    result = tuple(
        xcls
        for xcls in crystal_classes
        if CRYSTAL_CLASS_MAP[xcls].bravais_lattice[0] in compatibles
    )
    #
    return result


def space_groups_from_params(lattices=(), point_groups=(), chiral_only=True):
    """list of names of space groups compatible with lattices and point groups
    Given in space group number order

    Args:
        lattices:
        point_groups:
        chiral_only:

    Returns:

    """
    if chiral_only:
        space_groups = XTAL_SPACEGROUPS[1:]
    else:
        space_groups = list(info.name for info in SPACEGROUP_DATA)
    if lattices or point_groups:
        sgs1 = []
        if lattices:
            converter = {
                "Triclinic": "a",
                "Monoclinic": "m",
                "Orthorhombic": "o",
                "Tetragonal": "t",
                "Trigonal": "h",
                "Hexagonal": "h",
                "Cubic": "c",
            }
            tsts = set(converter.get(tag, tag) for tag in lattices)
            if "mI" in tsts:
                # Special case. mI is supported in XDS and UI but is not official
                tsts.add("mC")
            for spg in space_groups:
                blattice = CRYSTAL_CLASS_MAP[
                    SPACEGROUP_MAP[spg].crystal_class
                ].bravais_lattice
                if any(blattice.startswith(tst) for tst in tsts):
                    sgs1.append(spg)

        sgs2 = []
        if point_groups:
            for spg in space_groups:
                info = SPACEGROUP_MAP[spg]
                ccinfo = CRYSTAL_CLASS_MAP[(info.crystal_class)]
                for pgp in point_groups:
                    if ccinfo.point_group == pgp or (
                        pgp in ("312", "321") and ccinfo.name[:3] == pgp
                    ):
                        sgs2.append(spg)
                        break
        if sgs1 and sgs2:
            tstset = set(sgs1)
            space_groups = list(spg for spg in sgs2 if spg in tstset)
        else:
            space_groups = sgs1 + sgs2
    #
    return space_groups


def crystal_classes_from_params(
    lattices: tuple = (), point_groups: tuple = (), space_group: str = None
):
    """
    Get tuple of crystal class names compatible with input parameters,
    in crystal class number order
    Raises error for incompatible data.
    NB If lattices or point_groups are set will return relevant tuple
    even if space_group is also set

    Args:
        lattices: list of lattice strings (Bravais Lattice or 'Monoclinic' etc.
        point_groups: list(str) List of point group names (or '312', '321')
        space_group:  Space group name

    Returns: tuple(str) of crystal class names

    """
    if lattices or point_groups:
        space_groups = space_groups_from_params(
            lattices=lattices, point_groups=point_groups
        )
        if not space_groups or (space_group and space_group not in space_groups):
            result = ()
        else:
            infos = frozenset(
                CRYSTAL_CLASS_MAP[SPACEGROUP_MAP[space_group].crystal_class]
                for space_group in space_groups
            )
            result = tuple(
                info.name for info in sorted(infos, key=operator.attrgetter("number"))
            )
    elif space_group:
        result = (SPACEGROUP_MAP[space_group].crystal_class,)
    else:
        # Return empty list (nothing is set)
        result = ()
    #
    return result


def strategy_laue_group(crystal_classes: tuple, phasing=False):
    """Get laue group and point-group-like to use for strategy calculation
    for a given set of crystal classes.

    Args:
        crystal_classes (tuple): Crystal class names
        phasing (bool): Is this for phasing (default is native)

    Returns: (str, str) laue_group, point_group_like

    """

    laue_group_map = {
        frozenset(("-1",)): ("-1", "1"),
        frozenset(("2/m",)): ("2/m", "2"),
        frozenset(("mmm",)): ("mmm", "222"),
        frozenset(("4/m",)): ("4/m", "4"),
        frozenset(("4/mmm",)): ("4/mmm", "422"),
        frozenset(("4/m", "4/mmm")): ("4/m", "4"),
        frozenset(("-3",)): ("-3", "3"),
        frozenset(("6/m",)): ("6/m", "6"),
        frozenset(("6/mmm",)): ("6/mmm", "622"),
        frozenset(("6/m", "6/mmm")): ("6/m", "6"),
        frozenset(("m-3",)): ("m-3", "23"),
        frozenset(("m-3m",)): ("m-3m", "432"),
        frozenset(("m-3", "m-3m")): ("m-3", "23"),
    }
    # NB Other combinations are dealt with separately

    laue_groups = set()
    lattices = set()
    for name in crystal_classes:
        info = CRYSTAL_CLASS_MAP[name]
        laue_groups.add(info.laue_group)
        lattices.add(info.bravais_lattice)
    laue_groups = frozenset(laue_groups)
    result = laue_group_map.get(laue_groups)
    if result is None:
        if lattices and lattices.issubset(set(("hP", "hR"))):
            if laue_groups == set(("-3m",)) and lattices == set(("hR",)):
                # NB Includes non-chiral crystal classes
                result = ("-3m", "32")
            elif len(crystal_classes) == 1 and crystal_classes[0] in ("312P", "321P"):
                # NB excludes non-chiral crystal classes
                result = ("-3m", crystal_classes[0][:-1])
            else:
                result = ("-3", "3")
        else:
            result = ("-1", "1")
    #
    return result


def regularise_space_group(sgname: str):
    """Convert input (ISPyB) space group name to official space group name"""

    sginfo = SPACEGROUP_MAP.get(sgname)
    if sginfo:
        return sginfo.name
    return None
