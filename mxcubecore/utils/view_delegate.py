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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging


class ViewDelegate:
    """
    View item proxy/delegate, used to decouple the QueueEntry object from
    the UI attached. Can replace the Qt View item

    Implements methods queue entries call on their view and emits a singal
    with the node id and method called so client (mxcubeweb/qt) can react
    to whatever the entry intended to show, without mxcubecore depending on
    any UI toolkit.
    """

    def __init__(self, queue_model, node_id):
        self.queue_model = queue_model
        self.node_id = node_id
        self._data_model = None

    def _notify(self, method_name):
        self.queue_model.emit("view_delegate_called", (self.node_id, method_name))

    def setText(self, column, text):
        self._notify("setText")

    def setOn(self, state):
        self._notify("setOn")

    def setHighlighted(self, state):
        self._notify("setHighlighted")

    def set_checkable(self, state):
        self._notify("set_checkable")

    def set_background_color(self, color_index):
        self._notify("set_background_color")

    def update_tool_tip(self):
        self._notify("update_tool_tip")

    def __getattr__(self, name):
        """Guards against view methods this class hasn't been taught yet.

        Reached only for names not defined above (normal attribute lookup
        always wins first), so a queue entry calling an unmodelled view
        method logs it instead of raising AttributeError or silently
        pretending the call was handled via an emit.
        """

        def _unhandled(*args, **kwargs):
            logging.getLogger("HWR").warning(
                "ViewDelegate: unhandled view method '%s' called with "
                "args=%s kwargs=%s (node_id=%s)",
                name,
                args,
                kwargs,
                self.node_id,
            )

        return _unhandled
