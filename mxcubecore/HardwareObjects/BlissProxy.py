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

"""BLISS API Client - Access BLISS session and devices via BlissClient

This module provides the **client-side** interface to a running BLISS REST API.
The server side (``bliss.rest_service``) is responsible for registering objects
into the REST API; this module queries that API via the ``blissclient`` library
and keeps a local cache of every object whose type is fully known.

Only objects that have a type listed in the server's type registry are kept.
Objects with an unresolved / *unknown* type are silently discarded so that
callers always receive fully-typed, usable :class:`~blissclient.HardwareObject`
instances.

Typical YAML configuration::

    class: BlissProxy.BlissProxy
    configuration:
      blissapi_url: http://mxcube-test-1:5000
"""

import asyncio
import os
import logging
import gevent

try:
    from blissclient import BlissClient, Hardware, HardwareObject, Session
    HAS_BLISSCLIENT = True
except ImportError:
    HAS_BLISSCLIENT = False

from mxcubecore.BaseHardwareObjects import HardwareObject as MXHardwareObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"

class BlissProxy(MXHardwareObject):
    """Client for the BLISS REST API. """

    def __init__(self, name):
        super().__init__(name)
        self._client: BlissClient | None = None
        self._objects: dict[str, HardwareObject] = {}

    def init(self):
        """Initialise the BLISS API client and populate the object cache."""
        if not HAS_BLISSCLIENT:
            raise ImportError(
                "blissclient is not installed. "
            )
        url = self.get_property("blissapi_url") or os.environ.get(
            "BLISSAPI_URL", "http://localhost:5000"
        )

        try:
            self._client = BlissClient(url)
            self.log.info("BlissProxy: BlissClient created for %s", url)
        except Exception:
            self.log.error("BlissProxy: failed to create BlissClient for %s", url, exc_info=True)
            raise

        self._client.register_callback("connect", self._on_connect)
        self._client.register_callback("disconnect", self._on_disconnect)

        try:
            self._load_known_objects()
            self.log.info("BlissProxy: loaded %d objects from BLISS session", len(self._objects))
        except Exception:
            self.log.error(
                "BlissProxy: _load_known_objects() failed — object pre-cache is empty, "
                "falling back to on-demand fetch via get_object()",
                exc_info=True,
            )

        connect = self._client.create_connect(async_client=True)
        self.run_asyncio(connect())

        self.log.info(
            "BlissProxy ready — %d known object(s) loaded",
            len(self._objects),
        )

    def run_asyncio(self, future: asyncio.Future):
        def _await_future():
            asyncio.run(future)
            return future.get()

        return gevent.spawn(_await_future)

    def _load_known_objects(self) -> None:
        """Fetch available hardware objects and cache those with a known type.

        Calls the REST API to refresh both the object list and the type
        registry, then instantiates every object whose type is known.  Objects
        with an unresolved type are skipped with a DEBUG-level log entry.
        """
        hw = self._client.hardware
        hw._get_initial_status()
        hw.refresh_object_types() # list of properties and methods

        known_types = hw.types  # dict[str, ObjectTypeSchema]
        total = len(hw._cached_initial_statuses)
        loaded = skipped = 0
        self._objects = {}

        for name, initial_state in hw._cached_initial_statuses.items():
            if initial_state.type not in known_types:
                self.log.debug("Skipping '%s' unknown type '%s'", name, initial_state.type)
                skipped += 1
                continue
            try:
                self._objects[name] = hw.get(name) # build python object
                loaded += 1
                self.log.debug("Loaded '%s' [%s]", name, initial_state.type)
            except Exception:
                self.log.warning("Could not instantiate object '%s'", name, exc_info=True)
                skipped += 1

        self.log.info(
            "Object discovery: %d loaded, %d skipped (unknown type) out of %d total",
            loaded, skipped, total,
        )

    def _on_connect(self) -> None:
        self.log.info("Connected to BLISS API")
        self.emit("connected")

    def _on_disconnect(self) -> None:
        self.log.warning("Disconnected from BLISS API")
        self.emit("disconnected")

    def refresh(self) -> None:
        """Re-fetch all hardware objects from the server and rebuild the cache.

        Useful after a reconnect or when new objects have been registered in
        the BLISS session at runtime.
        """
        self.log.info("Refreshing BlissProxy object cache")
        self._load_known_objects()

    @property
    def session(self) -> Session:
        """The BLISS :class:`~blissclient.Session` accessor."""
        return self._client.session

    @property
    def hardware(self) -> Hardware:
        """The BLISS :class:`~blissclient.Hardware` accessor."""
        return self._client.hardware

    def get_object(self, name: str) -> HardwareObject:
        """Return a hardware object by its BLISS name.

        First looks in the pre-cached known-type objects.  If not found there,
        falls back to a direct fetch from the hardware client so that objects
        with unregistered types (e.g. MCA devices) can still be used.  A
        warning is emitted in that case since attribute availability depends on
        the server's type definition.

        Args:
            name: Beacon address / BLISS object name.

        Raises:
            KeyError: If *name* is not registered in the session at all.
        """
        if name in self._objects:
            return self._objects[name]

        if not self._objects:
            try:
                self.log.info("BlissProxy: cache is empty, retrying _load_known_objects() for '%s'", name)
                self._load_known_objects()
            except Exception:
                self.log.warning("BlissProxy: _load_known_objects() retry failed", exc_info=True)
            if name in self._objects:
                return self._objects[name]

        # Fallback: fetch directly, bypassing the type registry check.
        # Useful for devices whose type is not yet registered in blissclient
        # (e.g. BlissRontecMCA).
        try:
            obj = self._client.hardware.get(name)
            self.log.warning(
                "Object '%s' was not pre-cached (unknown type). "
                "Fetching directly — attribute availability depends on the "
                "server type definition.",
                name,
            )
            return obj
        except Exception:
            available = ", ".join(self.list_objects()) or "<none>"
            raise KeyError(
                f"Object '{name}' not found in the BLISS session. "
                f"Available pre-cached objects: {available}"
            ) from None

    def list_objects(self) -> list[str]:
        """Return a sorted list of all cached hardware object names."""
        return sorted(self._objects)

    def objects_by_type(self) -> dict[str, list[str]]:
        """Return objects grouped by their BLISS type.

        Returns:
            A dict mapping each type name to the sorted list of object names
            that share that type.  The dict is sorted by type name.

        Example::

            {
                "Axis": ["dtox", "omega", "phi"],
                "SoftAxis": ["energy"],
            }
        """
        groups: dict[str, list[str]] = {}
        for name, obj in self._objects.items():
            groups.setdefault(obj.type, []).append(name)
        return {t: sorted(names) for t, names in sorted(groups.items())}

    def get_scan_saving(self):
        """Convenience accessor for the ``SCAN_SAVING`` session object."""
        return self._client.session.scan_saving

    def session_name(self) -> str:
        """Return the BLISS session name."""
        return self._client.session.name