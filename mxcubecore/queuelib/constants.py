# encoding: utf-8
#
#  Project name: MXCuBE
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""Constants for the queue client JSON format.

The state bit flags mirror the reference mxcubeweb frontend's constants.js.
See JSON_FORMAT.md in this package for the full JSON format these belong to
"""

ORIGIN_MX3 = "MX3"

# Version of the queue JSON format (see JSON_FORMAT.md), reported
# under "format_version" in queue_to_dict()'s root response.
QUEUE_FORMAT_VERSION = "0.0.1"

# Queue node/task state, encoded as bit flags.
UNCOLLECTED = 0x0
READY = 0
RUNNING = 0x1
FAILED = 0x2
COLLECTED = 0x4
SAMPLE_MOUNTED = 0x8
WARNING = 0x10
