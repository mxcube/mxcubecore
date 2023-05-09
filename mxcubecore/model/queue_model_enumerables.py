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
