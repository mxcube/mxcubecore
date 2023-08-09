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

SpaceGroupInfo = namedtuple("SpaceGroupInfo", ("number", "name", "crystal_class"))
# Data from https://onlinelibrary.wiley.com/iucr/itc/Cb/ch1o4v0001/
SPACEGROUP_DATA = [
    SpaceGroupInfo(1, "P1", "1P"),
    SpaceGroupInfo(2, "P-1", "-1P"),
    SpaceGroupInfo(3, "P2", "2P"),
    SpaceGroupInfo(4, "P21", "2P"),
    SpaceGroupInfo(5, "C2", "2C"),
    SpaceGroupInfo(6, "Pm", "mP"),
    SpaceGroupInfo(7, "Pc", "mP"),
    SpaceGroupInfo(8, "Cm", "mC"),
    SpaceGroupInfo(9, "Cc", "mC"),
    SpaceGroupInfo(10, "P2/m", "2/mP"),
    SpaceGroupInfo(11, "P21/m", "2/mP"),
    SpaceGroupInfo(12, "C2/m", "2/mC"),
    SpaceGroupInfo(13, "P2/c", "2/mP"),
    SpaceGroupInfo(14, "P21/c", "2/mP"),
    SpaceGroupInfo(15, "C2/c", "2/mC"),
    SpaceGroupInfo(16, "P222", "222P"),
    SpaceGroupInfo(17, "P2221", "222P"),
    SpaceGroupInfo(18, "P21212", "222P"),
    SpaceGroupInfo(19, "P212121", "222P"),
    SpaceGroupInfo(20, "C2221", "222C"),
    SpaceGroupInfo(21, "C222", "222C"),
    SpaceGroupInfo(22, "F222", "222F"),
    SpaceGroupInfo(23, "I222", "222I"),
    SpaceGroupInfo(24, "I212121", "222I"),
    SpaceGroupInfo(25, "Pmm2", "mm2P"),
    SpaceGroupInfo(26, "Pmc21", "mm2P"),
    SpaceGroupInfo(27, "Pcc2", "mm2P"),
    SpaceGroupInfo(28, "Pma2", "mm2P"),
    SpaceGroupInfo(29, "Pca21", "mm2P"),
    SpaceGroupInfo(30, "Pnc2", "mm2P"),
    SpaceGroupInfo(31, "Pmn21", "mm2P"),
    SpaceGroupInfo(32, "Pba2", "mm2P"),
    SpaceGroupInfo(33, "Pna21", "mm2P"),
    SpaceGroupInfo(34, "Pnn2", "mm2P"),
    SpaceGroupInfo(35, "Cmm2", "mm2C"),
    SpaceGroupInfo(36, "Cmc21", "mm2C"),
    SpaceGroupInfo(37, "Ccc2", "mm2C"),
    SpaceGroupInfo(38, "C2mm", "2mmC"),  # NB Standard setting is in A, not C
    SpaceGroupInfo(39, "C2me", "2mmC"),  # NB Standard setting is in A, not C
    SpaceGroupInfo(40, "C2cm", "2mmC"),  # NB Standard setting is in A, not C
    SpaceGroupInfo(41, "C2ce", "2mmC"),  # NB Standard setting is in A, not C
    SpaceGroupInfo(42, "Fmm2", "mm2F"),
    SpaceGroupInfo(43, "Fdd2", "mm2F"),
    SpaceGroupInfo(44, "Imm2", "mm2I"),
    SpaceGroupInfo(45, "Iba2", "mm2I"),
    SpaceGroupInfo(46, "Ima2", "mm2I"),
    SpaceGroupInfo(47, "Pmmm", "mmmP"),
    SpaceGroupInfo(48, "Pnnn", "mmmP"),
    SpaceGroupInfo(49, "Pccm", "mmmP"),
    SpaceGroupInfo(50, "Pban", "mmmP"),
    SpaceGroupInfo(51, "Pmma", "mmmP"),
    SpaceGroupInfo(52, "Pnna", "mmmP"),
    SpaceGroupInfo(53, "Pmna", "mmmP"),
    SpaceGroupInfo(54, "Pcca", "mmmP"),
    SpaceGroupInfo(55, "Pbam", "mmmP"),
    SpaceGroupInfo(56, "Pccn", "mmmP"),
    SpaceGroupInfo(57, "Pbcm", "mmmP"),
    SpaceGroupInfo(58, "Pnnm", "mmmP"),
    SpaceGroupInfo(59, "Pmmn", "mmmP"),
    SpaceGroupInfo(60, "Pbcn", "mmmP"),
    SpaceGroupInfo(61, "Pbca", "mmmP"),
    SpaceGroupInfo(62, "Pnma", "mmmP"),
    SpaceGroupInfo(63, "Cmcm", "mmmC"),
    SpaceGroupInfo(64, "Cmce", "mmmC"),
    SpaceGroupInfo(65, "Cmmm", "mmmC"),
    SpaceGroupInfo(66, "Cccm", "mmmC"),
    SpaceGroupInfo(67, "Cmme", "mmmC"),
    SpaceGroupInfo(68, "Ccce", "mmmC"),
    SpaceGroupInfo(69, "Fmmm", "mmmF"),
    SpaceGroupInfo(70, "Fddd", "mmmF"),
    SpaceGroupInfo(71, "Immm", "mmmI"),
    SpaceGroupInfo(72, "Ibam", "mmmI"),
    SpaceGroupInfo(73, "Ibca", "mmmI"),
    SpaceGroupInfo(74, "Imma", "mmmI"),
    SpaceGroupInfo(75, "P4", "4P"),
    SpaceGroupInfo(76, "P41", "4P"),
    SpaceGroupInfo(77, "P42", "4P"),
    SpaceGroupInfo(78, "P43", "4P"),
    SpaceGroupInfo(79, "I4", "4I"),
    SpaceGroupInfo(80, "I41", "4I"),
    SpaceGroupInfo(81, "P-4", "-4P"),
    SpaceGroupInfo(82, "I-4", "-4I"),
    SpaceGroupInfo(83, "P4/m", "4/mP"),
    SpaceGroupInfo(84, "P42/m", "4/mP"),
    SpaceGroupInfo(85, "P4/n", "4/mP"),
    SpaceGroupInfo(86, "P42/n", "4/mP"),
    SpaceGroupInfo(87, "I4/m", "4/mI"),
    SpaceGroupInfo(88, "I41/a", "4/mI"),
    SpaceGroupInfo(89, "P422", "422P"),
    SpaceGroupInfo(90, "P4212", "422P"),
    SpaceGroupInfo(91, "P4122", "422P"),
    SpaceGroupInfo(92, "P41212", "422P"),
    SpaceGroupInfo(93, "P4222", "422P"),
    SpaceGroupInfo(94, "P42212", "422P"),
    SpaceGroupInfo(95, "P4322", "422P"),
    SpaceGroupInfo(96, "P43212", "422P"),
    SpaceGroupInfo(97, "I422", "422I"),
    SpaceGroupInfo(98, "I4122", "422I"),
    SpaceGroupInfo(99, "P4mm", "4mmP"),
    SpaceGroupInfo(100, "P4bm", "4mmP"),
    SpaceGroupInfo(101, "P42cm", "4mmP"),
    SpaceGroupInfo(102, "P42nm", "4mmP"),
    SpaceGroupInfo(103, "P4cc", "4mmP"),
    SpaceGroupInfo(104, "P4nc", "4mmP"),
    SpaceGroupInfo(105, "P42mc", "4mmP"),
    SpaceGroupInfo(106, "P42bc", "4mmP"),
    SpaceGroupInfo(107, "I4mm", "4mmI"),
    SpaceGroupInfo(108, "I4cm", "4mmI"),
    SpaceGroupInfo(109, "I41md", "4mmI"),
    SpaceGroupInfo(110, "I41cd", "4mmI"),
    SpaceGroupInfo(111, "P-42m", "-42mP"),
    SpaceGroupInfo(112, "P-42c", "-42mP"),
    SpaceGroupInfo(113, "P-421m", "-42mP"),
    SpaceGroupInfo(114, "P-421c", "-42mP"),
    SpaceGroupInfo(115, "P-4m2", "-4m2P"),
    SpaceGroupInfo(116, "P-4c2", "-4m2P"),
    SpaceGroupInfo(117, "P-4b2", "-4m2P"),
    SpaceGroupInfo(118, "P-4n2", "-4m2P"),
    SpaceGroupInfo(119, "I-4m2", "-4m2I"),
    SpaceGroupInfo(120, "I-4c2", "-4m2I"),
    SpaceGroupInfo(121, "I-42m", "-42mI"),
    SpaceGroupInfo(122, "I-42d", "-42mI"),
    SpaceGroupInfo(123, "P4/mmm", "4/mmmP"),
    SpaceGroupInfo(124, "P4/mcc", "4/mmmP"),
    SpaceGroupInfo(125, "P4/nbm", "4/mmmP"),
    SpaceGroupInfo(126, "P4/nnc", "4/mmmP"),
    SpaceGroupInfo(127, "P4/mbm", "4/mmmP"),
    SpaceGroupInfo(128, "P4/mnc", "4/mmmP"),
    SpaceGroupInfo(129, "P4/nmm", "4/mmmP"),
    SpaceGroupInfo(130, "P4/ncc", "4/mmmP"),
    SpaceGroupInfo(131, "P42/mmc", "4/mmmP"),
    SpaceGroupInfo(132, "P42/mcm", "4/mmmP"),
    SpaceGroupInfo(133, "P42/nbc", "4/mmmP"),
    SpaceGroupInfo(134, "P42/nnm", "4/mmmP"),
    SpaceGroupInfo(135, "P42/mbc", "4/mmmP"),
    SpaceGroupInfo(136, "P42/mnm", "4/mmmP"),
    SpaceGroupInfo(137, "P42/nmc", "4/mmmP"),
    SpaceGroupInfo(138, "P42/ncm", "4/mmmP"),
    SpaceGroupInfo(139, "I4/mmm", "4/mmmI"),
    SpaceGroupInfo(140, "I4/mcm", "4/mmmI"),
    SpaceGroupInfo(141, "I41/amd", "4/mmmI"),
    SpaceGroupInfo(142, "I41/acd", "4/mmmI"),
    SpaceGroupInfo(143, "P3", "3P"),
    SpaceGroupInfo(144, "P31", "3P"),
    SpaceGroupInfo(145, "P32", "3P"),
    SpaceGroupInfo(146, "R3", "3R"),
    SpaceGroupInfo(147, "P-3", "-3P"),
    SpaceGroupInfo(148, "R-3", "-3R"),
    SpaceGroupInfo(149, "P312", "312P"),
    SpaceGroupInfo(150, "P321", "321P"),
    SpaceGroupInfo(151, "P3112", "312P"),
    SpaceGroupInfo(152, "P3121", "321P"),
    SpaceGroupInfo(153, "P3212", "312P"),
    SpaceGroupInfo(154, "P3221", "321P"),
    SpaceGroupInfo(155, "R32", "32R"),
    SpaceGroupInfo(156, "P3m1", "3m1P"),
    SpaceGroupInfo(157, "P31m", "31mP"),
    SpaceGroupInfo(158, "P3c1", "3m1P"),
    SpaceGroupInfo(159, "P31c", "31mP"),
    SpaceGroupInfo(160, "R3m", "3mR"),
    SpaceGroupInfo(161, "R3c", "3mR"),
    SpaceGroupInfo(162, "P-31m", "-31mP"),
    SpaceGroupInfo(163, "P-31c", "-31mP"),
    SpaceGroupInfo(164, "P-3m1", "-3m1P"),
    SpaceGroupInfo(165, "P-3c1", "-3m1P"),
    SpaceGroupInfo(166, "R-3m", "-3mR"),
    SpaceGroupInfo(167, "R-3c", "-3mR"),
    SpaceGroupInfo(168, "P6", "6P"),
    SpaceGroupInfo(169, "P61", "6P"),
    SpaceGroupInfo(170, "P65", "6P"),
    SpaceGroupInfo(171, "P62", "6P"),
    SpaceGroupInfo(172, "P64", "6P"),
    SpaceGroupInfo(173, "P63", "6P"),
    SpaceGroupInfo(174, "P-6", "-6P"),
    SpaceGroupInfo(175, "P6/m", "6/mP"),
    SpaceGroupInfo(176, "P63/m", "6/mP"),
    SpaceGroupInfo(177, "P622", "622P"),
    SpaceGroupInfo(178, "P6122", "622P"),
    SpaceGroupInfo(179, "P6522", "622P"),
    SpaceGroupInfo(180, "P6222", "622P"),
    SpaceGroupInfo(181, "P6422", "622P"),
    SpaceGroupInfo(182, "P6322", "622P"),
    SpaceGroupInfo(183, "P6mm", "6mmP"),
    SpaceGroupInfo(184, "P6cc", "6mmP"),
    SpaceGroupInfo(185, "P63cm", "6mmP"),
    SpaceGroupInfo(186, "P63mc", "6mmP"),
    SpaceGroupInfo(187, "P-6m2", "-6m2P"),
    SpaceGroupInfo(188, "P-6c2", "-6m2P"),
    SpaceGroupInfo(189, "P-62m", "-62mP"),
    SpaceGroupInfo(190, "P-62c", "-62mP"),
    SpaceGroupInfo(191, "P6/mmm", "6/mmmP"),
    SpaceGroupInfo(192, "P6/mmc", "6/mmmP"),
    SpaceGroupInfo(193, "P63/mcm", "6/mmmP"),
    SpaceGroupInfo(194, "P63/mmc", "6/mmmP"),
    SpaceGroupInfo(195, "P23", "23P"),
    SpaceGroupInfo(196, "F23", "23F"),
    SpaceGroupInfo(197, "I23", "23I"),
    SpaceGroupInfo(198, "P213", "23P"),
    SpaceGroupInfo(199, "I213", "23I"),
    SpaceGroupInfo(200, "Pm-3", "m-3P"),
    SpaceGroupInfo(201, "Pn-3", "m-3P"),
    SpaceGroupInfo(202, "Fm-3", "m-3F"),
    SpaceGroupInfo(203, "Fd-3", "m-3F"),
    SpaceGroupInfo(204, "Im-3", "m-3I"),
    SpaceGroupInfo(205, "Pa-3", "m-3P"),
    SpaceGroupInfo(206, "Ia-3", "m-3I"),
    SpaceGroupInfo(207, "P432", "432P"),
    SpaceGroupInfo(208, "P4232", "432P"),
    SpaceGroupInfo(209, "F432", "432F"),
    SpaceGroupInfo(210, "F4132", "432F"),
    SpaceGroupInfo(211, "I432", "432I"),
    SpaceGroupInfo(212, "P4332", "432P"),
    SpaceGroupInfo(213, "P4132", "432P"),
    SpaceGroupInfo(214, "I4132", "432I"),
    SpaceGroupInfo(215, "P-43m", "-43mP"),
    SpaceGroupInfo(216, "F-43m", "-43mF"),
    SpaceGroupInfo(217, "I-43m", "-43mI"),
    SpaceGroupInfo(218, "P-43n", "-43mP"),
    SpaceGroupInfo(219, "F-43c", "-43mF"),
    SpaceGroupInfo(220, "I-43d", "-43mI"),
    SpaceGroupInfo(221, "Pm-3m", "m-3mP"),
    SpaceGroupInfo(222, "Pn-3n", "m-3mP"),
    SpaceGroupInfo(223, "Pm-3n", "m-3mP"),
    SpaceGroupInfo(224, "Pn-3m", "m-3mP"),
    SpaceGroupInfo(225, "Fm-3m", "m-3mF"),
    SpaceGroupInfo(226, "Fm-3c", "m-3mF"),
    SpaceGroupInfo(227, "Fd-3m", "m-3mF"),
    SpaceGroupInfo(228, "Fd-3c", "m-3mF"),
    SpaceGroupInfo(229, "Im-3m", "m-3mI"),
    SpaceGroupInfo(230, "Ia-3d", "m-3mI"),
]
SPACEGROUP_MAP = OrderedDict((info.name, info) for info in SPACEGROUP_DATA)

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


def space_groups_from_params(lattices=(), point_groups=(), chiral_only=True):
    """list of names of space groups compatible with lattices and point groups
    Given in space group number order

    Args:
        lattices:
        point_groups:

    Returns:

    """
    if chiral_only:
        space_groups = XTAL_SPACEGROUPS[1:]
    else:
        space_groups = list(SPACEGROUP_MAP)
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


def regularise_space_group(sgname:str):
    """Convert finput (ISPyB) space gorup name to officlalspace group name"""

    if sgname in SPACEGROUP_MAP:
        return sgname
    else:
        return None
