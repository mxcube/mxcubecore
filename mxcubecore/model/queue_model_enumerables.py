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

"""
Enumerables and other constants used by the queue model.
"""

from collections import namedtuple
from collections import OrderedDict

StrategyComplexity = namedtuple("StrategyComplexity", ["SINGLE", "FEW", "MANY"])
STRATEGY_COMPLEXITY = StrategyComplexity("none", "min", "full")

ExperimentType = namedtuple(
    "ExperimentType",
    [
        "SAD",
        "SAD_INV",
        "MAD",
        "MAD_INV",
        "NATIVE",
        "HELICAL",
        "EDNA_REF",
        "OSC",
        "MESH",
        "COLLECT_MULTIWEDGE",
        "STILL",
        "IMAGING",
    ],
)
EXPERIMENT_TYPE = ExperimentType(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
EXPERIMENT_TYPE_STR = ExperimentType(
    "SAD",
    "SAD - Inverse Beam",
    "MAD",
    "MAD - Inverse Beam",
    "OSC",
    "Helical",
    "Characterization",
    "OSC",
    "Mesh",
    "Collect - Multiwedge",
    "Still",
    "Imaging",
)

StrategyOption = namedtuple("StrategyOption", ["AVG"])
STRATEGY_OPTION = StrategyOption(0)

CollectionOrigin = namedtuple("CollectionOrigin", ["MXCUBE", "EDNA", "WORKFLOW"])
COLLECTION_ORIGIN = CollectionOrigin(0, 1, 2)
COLLECTION_ORIGIN_STR = CollectionOrigin("mxcube", "edna", "workflow")

EDNARefImages = namedtuple("EDNARefImages", ["FOUR", "TWO", "ONE", "NONE"])
EDNA_NUM_REF_IMAGES = EDNARefImages(0, 1, 2, 3)

CentringMethod = namedtuple(
    "CentringMethod", ["MANUAL", "LOOP", "FULLY_AUTOMATIC", "XRAY"]
)
CENTRING_METHOD = CentringMethod(0, 1, 2, 3)

WorkflowType = namedtuple(
    "WorkflowType", ["BURN", "WF1", "WF2", "LineScan", "MeshScan", "XrayCentring"]
)
WORKFLOW_TYPE = WorkflowType(0, 1, 2, 3, 4, 5)

CrystalClassInfo = namedtuple(
    "CrystalClassInfo", ("number", "name", "bravais_lattice", "point_group", "family")
 )
# Data from https://onlinelibrary.wiley.com/iucr/itc/Cb/ch1o4v0001/
CRYSTAL_CLASS_DATA = [
    CrystalClassInfo(0, "", "", "", ""),  # Null member, so number == index
    CrystalClassInfo(1, "1P", "aP", "1", "Triclinic"),
    CrystalClassInfo(2, "-1P", "aP", "-1", "Triclinic"),
    CrystalClassInfo(3, "2P", "mP", "2", "Monoclinic"),
    CrystalClassInfo(4, "2C", "mC", "2", "Monoclinic"),
    CrystalClassInfo(5, "mP", "mP", "m", "Monoclinic"),
    CrystalClassInfo(6, "mC", "mC", "m", "Monoclinic"),
    CrystalClassInfo(7, "2/mP", "mP", "2/m", "Monoclinic"),
    CrystalClassInfo(8, "2/mC", "mC", "2/m", "Monoclinic"),
    CrystalClassInfo(9, "222P", "oP", "222", "Orthorhombic"),
    CrystalClassInfo(10, "222C", "oC", "222", "Orthorhombic"),
    CrystalClassInfo(11, "222F", "oF", "222", "Orthorhombic"),
    CrystalClassInfo(12, "222I", "oI", "222", "Orthorhombic"),
    CrystalClassInfo(13, "mm2P", "oP", "mm", "Orthorhombic"),
    CrystalClassInfo(14, "mm2C", "oC", "mm", "Orthorhombic"),
    CrystalClassInfo(15, "2mmC", "oC", "mm", "Orthorhombic"),  # NB was2mmC(Amm2)
    CrystalClassInfo(16, "mm2F", "oF", "mm", "Orthorhombic"),
    CrystalClassInfo(17, "mm2I", "oI", "mm", "Orthorhombic"),
    CrystalClassInfo(18, "mmmP", "oP", "mmm", "Orthorhombic"),
    CrystalClassInfo(19, "mmmC", "oC", "mmm", "Orthorhombic"),
    CrystalClassInfo(20, "mmmF", "oF", "mmm", "Orthorhombic"),
    CrystalClassInfo(21, "mmmI", "oI", "mmm", "Orthorhombic"),
    CrystalClassInfo(22, "4P", "tP", "4", "Tetragonal"),
    CrystalClassInfo(23, "4I", "tI", "4", "Tetragonal"),
    CrystalClassInfo(24, "-4P", "tP", "-4", "Tetragonal"),
    CrystalClassInfo(25, "-4I", "tI", "-4", "Tetragonal"),
    CrystalClassInfo(26, "4/mP", "tP", "4/m", "Tetragonal"),
    CrystalClassInfo(27, "4/mI", "tI", "4/m", "Tetragonal"),
    CrystalClassInfo(28, "422P", "tP", "422", "Tetragonal"),
    CrystalClassInfo(29, "422I", "tI", "422", "Tetragonal"),
    CrystalClassInfo(30, "4mmP", "tP", "4mm", "Tetragonal"),
    CrystalClassInfo(31, "4mmI", "tI", "4mm", "Tetragonal"),
    CrystalClassInfo(32, "-42mP", "tP", "-4m", "Tetragonal"),
    CrystalClassInfo(33, "-4m2P", "tP", "-4m", "Tetragonal"),
    CrystalClassInfo(34, "-4m2I", "tI", "-4m", "Tetragonal"),
    CrystalClassInfo(35, "-42mI", "tI", "-4m", "Tetragonal"),
    CrystalClassInfo(36, "4/mmmP", "tP", "4/mmm", "Tetragonal"),
    CrystalClassInfo(37, "4/mmmI", "tI", "4/mmm", "Tetragonal"),
    CrystalClassInfo(38, "3P", "hP", "3", "Trigonal"),
    CrystalClassInfo(39, "3R", "hR", "3", "Trigonal"),
    CrystalClassInfo(40, "-3P", "hP", "-3", "Trigonal"),
    CrystalClassInfo(41, "-3R", "hR", "-3", "Trigonal"),
    CrystalClassInfo(42, "312P", "hP", "32", "Trigonal"),
    CrystalClassInfo(43, "321P", "hP", "32", "Trigonal"),
    CrystalClassInfo(44, "32R", "hR", "32", "Trigonal"),
    CrystalClassInfo(45, "3m1P", "hP", "3m", "Trigonal"),
    CrystalClassInfo(46, "31mP", "hP", "3m", "Trigonal"),
    CrystalClassInfo(47, "3mR", "hR", "3m", "Trigonal"),
    CrystalClassInfo(48, "-31mP", "hP", "-3m", "Trigonal"),
    CrystalClassInfo(49, "-3m1P", "hP", "-3m", "Trigonal"),
    CrystalClassInfo(50, "-3mR", "hR", "-3m", "Trigonal"),
    CrystalClassInfo(51, "6P", "hP", "6", "Hexagonal"),
    CrystalClassInfo(52, "-6P", "hP", "-6", "Hexagonal"),
    CrystalClassInfo(53, "6/mP", "hP", "6/m", "Hexagonal"),
    CrystalClassInfo(54, "622P", "hP", "622", "Hexagonal"),
    CrystalClassInfo(55, "6mmP", "hP", "6mm", "Hexagonal"),
    CrystalClassInfo(56, "-6m2P", "hP", "-6m", "Hexagonal"),
    CrystalClassInfo(57, "-62mP", "hP", "-6m", "Hexagonal"),
    CrystalClassInfo(58, "6/mmmP", "hP", "6/mmm", "Hexagonal"),
    CrystalClassInfo(59, "23P", "cP", "23", "Cubic"),
    CrystalClassInfo(60, "23F", "cF", "23", "Cubic"),
    CrystalClassInfo(61, "23I", "cI", "23", "Cubic"),
    CrystalClassInfo(62, "m-3P", "cP", "m-3", "Cubic"),
    CrystalClassInfo(63, "m-3F", "cF", "m-3", "Cubic"),
    CrystalClassInfo(64, "m-3I", "cI", "m-3", "Cubic"),
    CrystalClassInfo(65, "432P", "cP", "432", "Cubic"),
    CrystalClassInfo(66, "432F", "cF", "432", "Cubic"),
    CrystalClassInfo(67, "432I", "cI", "432", "Cubic"),
    CrystalClassInfo(68, "-43mP", "cP", "-43m", "Cubic"),
    CrystalClassInfo(69, "-43mF", "cF", "-43m", "Cubic"),
    CrystalClassInfo(70, "-43mI", "cI", "-43m", "Cubic"),
    CrystalClassInfo(71, "m-3mP", "cP", "m-3m", "Cubic"),
    CrystalClassInfo(72, "m-3mF", "cF", "m-3m", "Cubic"),
    CrystalClassInfo(73, "m-3mI", "cI", "m-3m", "Cubic"),
]
CRYSTAL_CLASS_MAP = OrderedDict(
    (info.name, info) for info in CRYSTAL_CLASS_DATA
)

SpaceGroupInfo = namedtuple(
    "SpaceGroupInfo", ("number", "name", "crystal_class")
)
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
    SpaceGroupInfo(38, "C2mm", "2mmC"), # NB Standard setting is in A, not C
    SpaceGroupInfo(39, "C2me", "2mmC"), # NB Standard setting is in A, not C
    SpaceGroupInfo(40, "C2cm", "2mmC"), # NB Standard setting is in A, not C
    SpaceGroupInfo(41, "C2ce", "2mmC"), # NB Standard setting is in A, not C
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

# laue_group2lattices = {
#     "-1": "Triclinic",
#     "2/m": "Monoclinic",
#     "mmm": "Orthorhombic",
#     "4/m": "Tetragonal",
#     "4/mmm": "Tetragonal",
#     "-3": "Hexagonal",
#     "-3m": "Hexagonal",
#     "6/m": "Hexagonal",
#     "6/mmm": "Hexagonal",
#     "m-3": "Cubic",
#     "m-3m": "Cubic",
# }
#
# lattice2letters = {
#     "Triclinic": "a",
#     "Monoclinic": "m",
#     "Orthorhombic": "o",
#     "Tetragonal": "t",
#     "Hexagonal": "h",
#     "Cubic": "c",
# }
# lattice2point_groups = {
#     "Triclinic": [],
#     "Monoclinic": [],
#     "Orthorhombic": [],
#     "Tetragonal": [],
#     "Hexagonal": [],
#     "Cubic": [],
# }
# lattice2xtal_point_groups = {
#     "Triclinic": [],
#     "Monoclinic": [],
#     "Orthorhombic": [],
#     "Tetragonal": [],
#     "Hexagonal": [],
#     "Cubic": [],
# }
# point_groups = []
# xtal_point_groups = []
# for sg in SPACEGROUP_DATA:
#     point_group = sg.point_group
#     if point_group:
#         lattice = laue_group2lattices[sg.laue_group]
#         ll0 =  lattice2point_groups[lattice]
#         if point_group not in ll0:
#             ll0.append(point_group)
#             point_groups.append(point_group)
#             if point_group.isdigit():
#                 xtal_point_groups.append(point_group)
#                 lattice2xtal_point_groups[lattice].append(point_group)

# Space group names for space groups compatible with chiral molecules,
# i.e. that do not contain mirror planes or centres of symmetry,
# in order of space group number
XTAL_SPACEGROUPS = [""] + [
    info.name
    for info in SPACEGROUP_DATA
    if CRYSTAL_CLASS_MAP[info.crystal_class].point_group.isdigit()
]
