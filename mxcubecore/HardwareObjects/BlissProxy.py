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

Typical YAML configuration::

    class: BlissProxy.BlissProxy
    configuration:
      blissapi_url: http://mxcube-test-1:5000
"""

import asyncio
import os
import time
import urllib.request

import gevent

try:
    from blissclient import BlissClient, Hardware, HardwareObject, Session

    HAS_BLISSCLIENT = True
except (ImportError, ModuleNotFoundError):
    BlissClient = None  # type: ignore[assignment,misc]
    Hardware = None  # type: ignore[assignment,misc]
    HardwareObject = None  # type: ignore[assignment,misc]
    Session = None  # type: ignore[assignment,misc]
    HAS_BLISSCLIENT = False

from mxcubecore.BaseHardwareObjects import HardwareObject as MXHardwareObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class BlissProxy(MXHardwareObject):
    """Client for the BLISS REST API."""

    _SESSION_READY_TIMEOUT = 300
    _INIT_EVENT_TIMEOUT = (
        _SESSION_READY_TIMEOUT + 10
    )  # get_object() waits slightly longer than init()

    def __init__(self, name):
        super().__init__(name)
        self._client: BlissClient | None = None
        self._objects: dict[str, HardwareObject] = {}
        self._init_event = (
            gevent.event.Event()
        )  # unblocks get_object() callers waiting on init()

    def init(self):
        try:
            if not HAS_BLISSCLIENT:
                raise ImportError("blissclient is not installed.")

            url = self.get_property("blissapi_url") or os.environ.get(
                "BLISSAPI_URL", "http://localhost:5000"
            )

            # BlissClient() raises if the API is not reachable — wait first.
            self._wait_for_session_ready(url)

            try:
                self._client = BlissClient(url)
                self.log.info("BlissProxy: BlissClient created for %s", url)
            except Exception:
                self.log.error(
                    "BlissProxy: failed to create BlissClient for %s",
                    url,
                    exc_info=True,
                )
                raise

            self._client.register_callback("connect", self._on_connect)
            self._client.register_callback("disconnect", self._on_disconnect)

            try:
                self._load_known_objects()
            except Exception:
                self.log.error(
                    "BlissProxy: _load_known_objects() failed — falling back to "
                    "on-demand fetch",
                    exc_info=True,
                )

            self.run_asyncio(self._client.create_connect(async_client=True)())
            self.log.info(
                "BlissProxy ready — %d known object(s) loaded", len(self._objects)
            )
        finally:
            self._init_event.set()

    def _wait_for_session_ready(
        self,
        base_url: str,
        timeout: int = _SESSION_READY_TIMEOUT,
        poll_interval: int = 2,
    ) -> None:
        """Poll GET /api/object until the BLISS REST service reports ready.

        The service only flips to ready once its session objects are fully registered.
        """
        endpoint = f"{base_url.rstrip('/')}/api/object"
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError(
                f"BlissProxy: unsupported URL scheme in '{endpoint}' — "
                "only http/https allowed"
            )
        deadline = time.monotonic() + timeout
        self.log.info("BlissProxy: waiting for BLISS session ready (%s) ...", endpoint)
        while time.monotonic() < deadline:
            try:
                # nosec B310 / noqa: S310 — scheme validated above
                with urllib.request.urlopen(endpoint, timeout=5) as resp:  # noqa: S310
                    if resp.status == 200:
                        self.log.info("BlissProxy: BLISS session ready")
                        return
            except Exception as exc:
                self.log.debug("BlissProxy: waiting for BLISS (%s)", exc)
            time.sleep(poll_interval)
        self.log.warning(
            "BlissProxy: BLISS session not ready after %ds — proceeding anyway", timeout
        )

    def run_asyncio(self, future: asyncio.Future):
        def _await_future():
            return asyncio.run(future)

        return gevent.spawn(_await_future)

    def _load_known_objects(self) -> None:
        if self._client is None:
            raise RuntimeError("BlissProxy._client is not initialised.")
        hw = self._client.hardware
        hw._get_initial_status()
        hw.refresh_object_types()
        known_types = hw.types
        total = len(hw.available)
        loaded = skipped = 0
        self._objects = {}
        for name, initial_state in hw._cached_initial_statuses.items():
            if initial_state.type not in known_types:
                self.log.debug(
                    "Skipping '%s' — unknown type '%s'", name, initial_state.type
                )
                skipped += 1
                continue
            try:
                self._objects[name] = hw.get(name)
                loaded += 1
                self.log.debug("Loaded '%s' [%s]", name, initial_state.type)
            except Exception:
                self.log.warning(
                    "Could not instantiate object '%s'", name, exc_info=True
                )
                skipped += 1
        self.log.info(
            "Object discovery: %d loaded, %d skipped out of %d total",
            loaded,
            skipped,
            total,
        )

    def _on_connect(self) -> None:
        self.log.info("Connected to BLISS API")
        self.emit("connected")

    def _on_disconnect(self) -> None:
        self.log.warning("Disconnected from BLISS API")
        self.emit("disconnected")

    def refresh(self) -> None:
        self.log.info("Refreshing BlissProxy object cache")
        self._load_known_objects()

    @property
    def session(self) -> Session:
        return self._client.session

    @property
    def hardware(self) -> Hardware:
        return self._client.hardware

    def get_object(self, name: str) -> HardwareObject:
        """Return a hardware object by its BLISS name.

        Args:
            name: Beacon address / BLISS object name.

        Raises:
            KeyError: If *name* is not registered in the session at all.
        """
        if name in self._objects:
            return self._objects[name]

        if not self._init_event.is_set():
            self.log.info("BlissProxy: get_object('%s') waiting for init() ...", name)
            self._init_event.wait(timeout=self._INIT_EVENT_TIMEOUT)
            if not self._init_event.is_set():
                raise KeyError(
                    f"BlissProxy: init() timed out — cannot retrieve object '{name}'"
                )

        if not self._objects:
            try:
                self.log.info(
                    "BlissProxy: cache empty, retrying _load_known_objects() for '%s'",
                    name,
                )
                self._load_known_objects()
            except Exception:
                self.log.warning(
                    "BlissProxy: _load_known_objects() retry failed", exc_info=True
                )
            if name in self._objects:
                return self._objects[name]

        not_found_msg = (
            f"Object '{name}' not found. "
            f"Available: {', '.join(self.list_objects()) or '<none>'}"
        )
        if self._client is None:
            raise KeyError(not_found_msg)

        # Fallback: fetch directly, bypassing the type registry — useful for devices
        # whose type is not yet registered in blissclient (e.g. BlissRontecMCA).
        try:
            obj = self._client.hardware.get(name)
            self.log.warning("Object '%s' not pre-cached (unknown type).", name)
            return obj
        except Exception:
            raise KeyError(not_found_msg) from None

    def list_objects(self) -> list[str]:
        return sorted(self._objects)

    def objects_by_type(self) -> dict[str, list[str]]:
        """Return objects grouped by BLISS type.

        Example::

            {"Axis": ["dtox", "omega"], "SoftAxis": ["energy"]}
        """
        groups: dict[str, list[str]] = {}
        for name, obj in self._objects.items():
            groups.setdefault(obj.type, []).append(name)
        return {t: sorted(names) for t, names in sorted(groups.items())}
