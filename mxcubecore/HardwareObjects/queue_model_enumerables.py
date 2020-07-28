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

"""
Enumerables and other constants used by the queue model.
"""

from collections import namedtuple
from collections import OrderedDict

import enum

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

SpaceGroupInfo = namedtuple(
    "SpaceGroupInfo", ("number", "name", "point_group", "laue_group")
)
# Complete list of 230 crystallographic space groups
# Direct source: GPhL stratcal source code. RHFogh.
SPACEGROUP_DATA = [
    SpaceGroupInfo(0, "", "", ""),
    SpaceGroupInfo(1, "P1", "1", "-1"),
    SpaceGroupInfo(2, "P-1", "-1", "-1"),
    SpaceGroupInfo(3, "P2", "2", "2/m"),
    SpaceGroupInfo(4, "P21", "2", "2/m"),
    SpaceGroupInfo(5, "C2", "2", "2/m"),
    SpaceGroupInfo(6, "Pm", "m", "2/m"),
    SpaceGroupInfo(7, "Pc", "m", "2/m"),
    SpaceGroupInfo(8, "Cm", "m", "2/m"),
    SpaceGroupInfo(9, "Cc", "m", "2/m"),
    SpaceGroupInfo(10, "P2/m", "2/m", "2/m"),
    SpaceGroupInfo(11, "P21/m", "2/m", "2/m"),
    SpaceGroupInfo(12, "C2/m", "2/m", "2/m"),
    SpaceGroupInfo(13, "P2/c", "2/m", "2/m"),
    SpaceGroupInfo(14, "P21/c", "2/m", "2/m"),
    SpaceGroupInfo(15, "C2/c", "2/m", "2/m"),
    SpaceGroupInfo(16, "P222", "222", "mmm"),
    SpaceGroupInfo(17, "P2221", "222", "mmm"),
    SpaceGroupInfo(18, "P21212", "222", "mmm"),
    SpaceGroupInfo(19, "P212121", "222", "mmm"),
    SpaceGroupInfo(20, "C2221", "222", "mmm"),
    SpaceGroupInfo(21, "C222", "222", "mmm"),
    SpaceGroupInfo(22, "F222", "222", "mmm"),
    SpaceGroupInfo(23, "I222", "222", "mmm"),
    SpaceGroupInfo(24, "I212121", "222", "mmm"),
    SpaceGroupInfo(25, "Pmm2", "mm2", "mmm"),
    SpaceGroupInfo(26, "Pmc21", "mm2", "mmm"),
    SpaceGroupInfo(27, "Pcc2", "mm2", "mmm"),
    SpaceGroupInfo(28, "Pma2", "mm2", "mmm"),
    SpaceGroupInfo(29, "Pca21", "mm2", "mmm"),
    SpaceGroupInfo(30, "Pnc2", "mm2", "mmm"),
    SpaceGroupInfo(31, "Pmn21", "mm2", "mmm"),
    SpaceGroupInfo(32, "Pba2", "mm2", "mmm"),
    SpaceGroupInfo(33, "Pna21", "mm2", "mmm"),
    SpaceGroupInfo(34, "Pnn2", "mm2", "mmm"),
    SpaceGroupInfo(35, "Cmm2", "mm2", "mmm"),
    SpaceGroupInfo(36, "Cmc21", "mm2", "mmm"),
    SpaceGroupInfo(37, "Ccc2", "mm2", "mmm"),
    SpaceGroupInfo(38, "Amm2", "mm2", "mmm"),
    SpaceGroupInfo(39, "Abm2", "mm2", "mmm"),
    SpaceGroupInfo(40, "Ama2", "mm2", "mmm"),
    SpaceGroupInfo(41, "Aba2", "mm2", "mmm"),
    SpaceGroupInfo(42, "Fmm2", "mm2", "mmm"),
    SpaceGroupInfo(43, "Fdd2", "mm2", "mmm"),
    SpaceGroupInfo(44, "Imm2", "mm2", "mmm"),
    SpaceGroupInfo(45, "Iba2", "mm2", "mmm"),
    SpaceGroupInfo(46, "Ima2", "mm2", "mmm"),
    SpaceGroupInfo(47, "Pmmm", "mmm", "mmm"),
    SpaceGroupInfo(48, "Pnnn", "mmm", "mmm"),
    SpaceGroupInfo(49, "Pccm", "mmm", "mmm"),
    SpaceGroupInfo(50, "Pban", "mmm", "mmm"),
    SpaceGroupInfo(51, "Pmma", "mmm", "mmm"),
    SpaceGroupInfo(52, "Pnna", "mmm", "mmm"),
    SpaceGroupInfo(53, "Pmna", "mmm", "mmm"),
    SpaceGroupInfo(54, "Pcca", "mmm", "mmm"),
    SpaceGroupInfo(55, "Pbam", "mmm", "mmm"),
    SpaceGroupInfo(56, "Pccn", "mmm", "mmm"),
    SpaceGroupInfo(57, "Pbcm", "mmm", "mmm"),
    SpaceGroupInfo(58, "Pnnm", "mmm", "mmm"),
    SpaceGroupInfo(59, "Pmmn", "mmm", "mmm"),
    SpaceGroupInfo(60, "Pbcn", "mmm", "mmm"),
    SpaceGroupInfo(61, "Pbca", "mmm", "mmm"),
    SpaceGroupInfo(62, "Pnma", "mmm", "mmm"),
    SpaceGroupInfo(63, "Cmcm", "mmm", "mmm"),
    SpaceGroupInfo(64, "Cmca", "mmm", "mmm"),
    SpaceGroupInfo(65, "Cmmm", "mmm", "mmm"),
    SpaceGroupInfo(66, "Cccm", "mmm", "mmm"),
    SpaceGroupInfo(67, "Cmma", "mmm", "mmm"),
    SpaceGroupInfo(68, "Ccca", "mmm", "mmm"),
    SpaceGroupInfo(69, "Fmmm", "mmm", "mmm"),
    SpaceGroupInfo(70, "Fddd", "mmm", "mmm"),
    SpaceGroupInfo(71, "Immm", "mmm", "mmm"),
    SpaceGroupInfo(72, "Ibam", "mmm", "mmm"),
    SpaceGroupInfo(73, "Ibca", "mmm", "mmm"),
    SpaceGroupInfo(74, "Imma", "mmm", "mmm"),
    SpaceGroupInfo(75, "P4", "4", "4/m"),
    SpaceGroupInfo(76, "P41", "4", "4/m"),
    SpaceGroupInfo(77, "P42", "4", "4/m"),
    SpaceGroupInfo(78, "P43", "4", "4/m"),
    SpaceGroupInfo(79, "I4", "4", "4/m"),
    SpaceGroupInfo(80, "I41", "4", "4/m"),
    SpaceGroupInfo(81, "P-4", "-4", "4/m"),
    SpaceGroupInfo(82, "I-4", "-4", "4/m"),
    SpaceGroupInfo(83, "P4/m", "4/m", "4/m"),
    SpaceGroupInfo(84, "P42/m", "4/m", "4/m"),
    SpaceGroupInfo(85, "P4/n", "4/m", "4/m"),
    SpaceGroupInfo(86, "P42/n", "4/m", "4/m"),
    SpaceGroupInfo(87, "I4/m", "4/m", "4/m"),
    SpaceGroupInfo(88, "I41/a", "4/m", "4/m"),
    SpaceGroupInfo(89, "P422", "422", "4/mmm"),
    SpaceGroupInfo(90, "P4212", "422", "4/mmm"),
    SpaceGroupInfo(91, "P4122", "422", "4/mmm"),
    SpaceGroupInfo(92, "P41212", "422", "4/mmm"),
    SpaceGroupInfo(93, "P4222", "422", "4/mmm"),
    SpaceGroupInfo(94, "P42212", "422", "4/mmm"),
    SpaceGroupInfo(95, "P4322", "422", "4/mmm"),
    SpaceGroupInfo(96, "P43212", "422", "4/mmm"),
    SpaceGroupInfo(97, "I422", "422", "4/mmm"),
    SpaceGroupInfo(98, "I4122", "422", "4/mmm"),
    SpaceGroupInfo(99, "P4mm", "4mm", "4/mmm"),
    SpaceGroupInfo(100, "P4bm", "4mm", "4/mmm"),
    SpaceGroupInfo(101, "P42cm", "4mm", "4/mmm"),
    SpaceGroupInfo(102, "P42nm", "4mm", "4/mmm"),
    SpaceGroupInfo(103, "P4cc", "4mm", "4/mmm"),
    SpaceGroupInfo(104, "P4nc", "4mm", "4/mmm"),
    SpaceGroupInfo(105, "P42mc", "4mm", "4/mmm"),
    SpaceGroupInfo(106, "P42bc", "4mm", "4/mmm"),
    SpaceGroupInfo(107, "I4mm", "4mm", "4/mmm"),
    SpaceGroupInfo(108, "I4cm", "4mm", "4/mmm"),
    SpaceGroupInfo(109, "I41md", "4mm", "4/mmm"),
    SpaceGroupInfo(110, "I41cd", "4mm", "4/mmm"),
    SpaceGroupInfo(111, "P-42m", "-42m", "4/mmm"),
    SpaceGroupInfo(112, "P-42c", "-42m", "4/mmm"),
    SpaceGroupInfo(113, "P-421m", "-42m", "4/mmm"),
    SpaceGroupInfo(114, "P-421c", "-42m", "4/mmm"),
    SpaceGroupInfo(115, "P-4m2", "-4m2", "4/mmm"),
    SpaceGroupInfo(116, "P-4c2", "-4m2", "4/mmm"),
    SpaceGroupInfo(117, "P-4b2", "-4m2", "4/mmm"),
    SpaceGroupInfo(118, "P-4n2", "-4m2", "4/mmm"),
    SpaceGroupInfo(119, "I-4m2", "-4m2", "4/mmm"),
    SpaceGroupInfo(120, "I-4c2", "-4m2", "4/mmm"),
    SpaceGroupInfo(121, "I-42m", "-42m", "4/mmm"),
    SpaceGroupInfo(122, "I-42d", "-42m", "4/mmm"),
    SpaceGroupInfo(123, "P4/mmm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(124, "P4/mcc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(125, "P4/nbm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(126, "P4/nnc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(127, "P4/mbm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(128, "P4/mnc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(129, "P4/nmm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(130, "P4/ncc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(131, "P42/mmc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(132, "P42/mcm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(133, "P42/nbc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(134, "P42/nnm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(135, "P42/mbc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(136, "P42/mnm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(137, "P42/nmc", "4/mmm", "4/mmm"),
    SpaceGroupInfo(138, "P42/ncm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(139, "I4/mmm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(140, "I4/mcm", "4/mmm", "4/mmm"),
    SpaceGroupInfo(141, "I41/amd", "4/mmm", "4/mmm"),
    SpaceGroupInfo(142, "I41/acd", "4/mmm", "4/mmm"),
    SpaceGroupInfo(143, "P3", "3", "-3"),
    SpaceGroupInfo(144, "P31", "3", "-3"),
    SpaceGroupInfo(145, "P32", "3", "-3"),
    SpaceGroupInfo(146, "R3", "3", "-3"),
    SpaceGroupInfo(147, "P-3", "-3", "-3"),
    SpaceGroupInfo(148, "R-3", "-3", "-3"),
    SpaceGroupInfo(149, "P312", "312", "-3m"),
    SpaceGroupInfo(150, "P321", "321", "-3m"),
    SpaceGroupInfo(151, "P3112", "312", "-3m"),
    SpaceGroupInfo(152, "P3121", "321", "-3m"),
    SpaceGroupInfo(153, "P3212", "312", "-3m"),
    SpaceGroupInfo(154, "P3221", "321", "-3m"),
    SpaceGroupInfo(155, "R32", "32", "-3m"),
    SpaceGroupInfo(156, "P3m1", "3m1", "-3m"),
    SpaceGroupInfo(157, "P31m", "31m", "-3m"),
    SpaceGroupInfo(158, "P3c1", "3m1", "-3m"),
    SpaceGroupInfo(159, "P31c", "31m", "-3m"),
    SpaceGroupInfo(160, "R3m", "3m", "-3m"),
    SpaceGroupInfo(161, "R3c", "3m", "-3m"),
    SpaceGroupInfo(162, "P-31m", "-31m", "-3m"),
    SpaceGroupInfo(163, "P-31c", "-31m", "-3m"),
    SpaceGroupInfo(164, "P-3m1", "-3m1", "-3m"),
    SpaceGroupInfo(165, "P-3c1", "-3m1", "-3m"),
    SpaceGroupInfo(166, "R-3m", "-3m", "-3m"),
    SpaceGroupInfo(167, "R-3c", "-3m", "-3m"),
    SpaceGroupInfo(168, "P6", "6", "6/m"),
    SpaceGroupInfo(169, "P61", "6", "6/m"),
    SpaceGroupInfo(170, "P65", "6", "6/m"),
    SpaceGroupInfo(171, "P62", "6", "6/m"),
    SpaceGroupInfo(172, "P64", "6", "6/m"),
    SpaceGroupInfo(173, "P63", "6", "6/m"),
    SpaceGroupInfo(174, "P-6", "-6", "6/m"),
    SpaceGroupInfo(175, "P6/m", "6/m", "6/m"),
    SpaceGroupInfo(176, "P63/m", "6/m", "6/m"),
    SpaceGroupInfo(177, "P622", "622", "6/mmm"),
    SpaceGroupInfo(178, "P6122", "622", "6/mmm"),
    SpaceGroupInfo(179, "P6522", "622", "6/mmm"),
    SpaceGroupInfo(180, "P6222", "622", "6/mmm"),
    SpaceGroupInfo(181, "P6422", "622", "6/mmm"),
    SpaceGroupInfo(182, "P6322", "622", "6/mmm"),
    SpaceGroupInfo(183, "P6mm", "6mm", "6/mmm"),
    SpaceGroupInfo(184, "P6cc", "6mm", "6/mmm"),
    SpaceGroupInfo(185, "P63cm", "6mm", "6/mmm"),
    SpaceGroupInfo(186, "P63mc", "6mm", "6/mmm"),
    SpaceGroupInfo(187, "P-6m2", "-6m2", "6/mmm"),
    SpaceGroupInfo(188, "P-6c2", "-6m2", "6/mmm"),
    SpaceGroupInfo(189, "P-62m", "-62m", "6/mmm"),
    SpaceGroupInfo(190, "P-62c", "-62m", "6/mmm"),
    SpaceGroupInfo(191, "P6/mmm", "6/mmm", "6/mmm"),
    SpaceGroupInfo(192, "P6/mcc", "6/mmm", "6/mmm"),
    SpaceGroupInfo(193, "P63/mcm", "6/mmm", "6/mmm"),
    SpaceGroupInfo(194, "P63/mmc", "6/mmm", "6/mmm"),
    SpaceGroupInfo(195, "P23", "23", "m-3"),
    SpaceGroupInfo(196, "F23", "23", "m-3"),
    SpaceGroupInfo(197, "I23", "23", "m-3"),
    SpaceGroupInfo(198, "P213", "23", "m-3"),
    SpaceGroupInfo(199, "I213", "23", "m-3"),
    SpaceGroupInfo(200, "Pm-3", "m-3", "m-3"),
    SpaceGroupInfo(201, "Pn-3", "m-3", "m-3"),
    SpaceGroupInfo(202, "Fm-3", "m-3", "m-3"),
    SpaceGroupInfo(203, "Fd-3", "m-3", "m-3"),
    SpaceGroupInfo(204, "Im-3", "m-3", "m-3"),
    SpaceGroupInfo(205, "Pa-3", "m-3", "m-3"),
    SpaceGroupInfo(206, "Ia-3", "m-3", "m-3"),
    SpaceGroupInfo(207, "P432", "432", "m-3m"),
    SpaceGroupInfo(208, "P4232", "432", "m-3m"),
    SpaceGroupInfo(209, "F432", "432", "m-3m"),
    SpaceGroupInfo(210, "F4132", "432", "m-3m"),
    SpaceGroupInfo(211, "I432", "432", "m-3m"),
    SpaceGroupInfo(212, "P4332", "432", "m-3m"),
    SpaceGroupInfo(213, "P4132", "432", "m-3m"),
    SpaceGroupInfo(214, "I4132", "432", "m-3m"),
    SpaceGroupInfo(215, "P-43m", "-43m", "m-3m"),
    SpaceGroupInfo(216, "F-43m", "-43m", "m-3m"),
    SpaceGroupInfo(217, "I-43m", "-43m", "m-3m"),
    SpaceGroupInfo(218, "P-43n", "-43m", "m-3m"),
    SpaceGroupInfo(219, "F-43c", "-43m", "m-3m"),
    SpaceGroupInfo(220, "I-43d", "-43m", "m-3m"),
    SpaceGroupInfo(221, "Pm-3m", "m-3m", "m-3m"),
    SpaceGroupInfo(222, "Pn-3n", "m-3m", "m-3m"),
    SpaceGroupInfo(223, "Pm-3n", "m-3m", "m-3m"),
    SpaceGroupInfo(224, "Pn-3m", "m-3m", "m-3m"),
    SpaceGroupInfo(225, "Fm-3m", "m-3m", "m-3m"),
    SpaceGroupInfo(226, "Fm-3c", "m-3m", "m-3m"),
    SpaceGroupInfo(227, "Fd-3m", "m-3m", "m-3m"),
    SpaceGroupInfo(228, "Fd-3c", "m-3m", "m-3m"),
    SpaceGroupInfo(229, "Im-3m", "m-3m", "m-3m"),
    SpaceGroupInfo(230, "Ia-3d", "m-3m", "m-3m"),
]
SPACEGROUP_MAP = OrderedDict((info.name, info) for info in SPACEGROUP_DATA)

# Space group names for space groups compatible with chiral molecules,
# i.e. that do not contain mirror planes or centres of symmetry,
# in order of space group number
XTAL_SPACEGROUPS = [""] + [
    info.name for info in SPACEGROUP_DATA if info.point_group.isdigit()
]

# @enum.unique


class States(enum.Enum):
    """Standard device states, based on TangoShutter states.
    SardanaMotor.state_map, and DiffractometerState,
    for general use across HardwareObjects.

    Limited to a common set of states.

    Grammar of tags corrected ('CLOSE->CLOSED, DISABLE->DISABLED) relative
    to Tango states, so you can echo them to the UI without misunderstanding"""

    CLOSED = 0
    OPEN = 1  # Also used for workflow 'Expecting input'
    ON = 2  # Could be used to mean 'Connected'.
    OFF = 3  # Could be used to mean 'Disconnected'
    INSERT = 4
    EXTRACT = 5
    MOVING = 6
    STANDBY = 7  # Could be used to mean 'Ready'
    FAULT = 8
    INIT = 9
    RUNNING = 10
    ALARM = 11
    DISABLED = 12
    UNKNOWN = 13
