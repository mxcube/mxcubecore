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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Bridges HardwareObject signals (mxcubecore.dispatcher, as used by
HardwareObjectMixin.emit/.connect) into IPCEvent notifications pushed to
the connected IPC client.
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

from mxcubecore.dispatcher import dispatcher
from mxcubecore.ipc.constants import logger


class DispatcherBridge:
    """Owns the dispatcher.connect() subscriptions for one IPCServer and
    turns each signal emission into a call to `on_event(method, params)`.
    """

    def __init__(self, on_event: Callable[[str, Dict[str, Any]], None]) -> None:
        self._on_event = on_event
        self._connections: List[Tuple[Any, str, Callable]] = []

    def subscribe(
        self,
        sender: Any,
        signal_name: str,
        event_method: str,
        check_args: Optional[Callable[[Tuple[Any, ...]], None]] = None,
    ) -> None:
        """Forward every `signal_name` emitted by `sender` as an IPCEvent
        whose `method` is `event_method`. `check_args`, if given, is called
        with each emission's positional args before it's forwarded (see
        EventEntry.check_args - it only warns, never blocks the event).
        """

        def _handler(*args: Any) -> None:
            logger.debug(
                "IPC signal received: %s.%s%s -> event %s",
                sender,
                signal_name,
                args,
                event_method,
            )
            if check_args is not None:
                check_args(args)
            self._on_event(event_method, {"args": list(args)})

        dispatcher.connect(_handler, signal_name, sender)
        self._connections.append((sender, signal_name, _handler))

    def unsubscribe_all(self) -> None:
        for sender, signal_name, handler in self._connections:
            dispatcher.disconnect(handler, signal_name, sender)
            logger.debug("IPC signal unsubscribed: %s.%s", sender, signal_name)
        self._connections = []
