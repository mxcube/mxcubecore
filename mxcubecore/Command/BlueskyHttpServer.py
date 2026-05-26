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

import json
import logging
import os
import time

import gevent
import requests

from mxcubecore import Poller
from mxcubecore.CommandContainer import CommandObject

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class BlueskyHttpServerCommand(CommandObject):
    """Interface for communicating with the Bluesky Http Server API."""

    _default_timeout = 5
    _status_path = "api/status"
    _execute_path = "api/queue/item/execute"
    _pause_path = "api/re/pause"
    _resume_path = "api/re/resume"
    _abort_path = "api/re/abort"
    _console_uid_path = "api/console_output/uid"
    _console_path = "api/console_output_update"

    def __init__(self, name, url, timeout=5, **kwargs):
        CommandObject.__init__(self, name, **kwargs)
        self.username = ""
        self._default_timeout = timeout
        self._url = f"{url}/" if url[-1] != "/" else url
        self._headers = {"Authorization": f"ApiKey {os.environ['AUTH_KEY']}"}
        self.console_output_uid = self.get_console_uid()
        self.last_msg_uid = ""
        self.user_level_log = logging.getLogger("user_level_log")
        self.output_poller = Poller.poll(
            polled_call=self.update_console_output,
            polling_period=500,
            value_changed_callback=self.show_console_output,
            error_callback=self.poll_failed,
        )

    def poll_failed(self, exception, poller_id):
        self.user_level_log.error(exception)
        poller = Poller.get_poller(poller_id)
        if poller is not None:
            poller.restart(1000)

    def format_response(self, response):
        if response:
            response.raise_for_status()
            return json.loads(response.text)
        return response

    def status(self):
        response = requests.get(
            self._url + self._status_path,
            headers=self._headers,
            timeout=self._default_timeout,
        )
        return self.format_response(response)

    def monitor_manager_state(self, stop_state, timeout=86400):
        with gevent.Timeout(timeout, exception=TimeoutError):
            while self.status()["manager_state"] != stop_state:
                time.sleep(0.1)

    def execute_plan(self, plan_name, kwargs=None):
        if not kwargs:
            kwargs = {}
        return requests.post(
            self._url + self._execute_path,
            headers=self._headers,
            json={
                "user": self.username,
                "item": {"name": plan_name, "item_type": "plan", "kwargs": kwargs},
            },
            timeout=self._default_timeout,
        )

    def pause_plan(self, option="deferred"):
        return requests.post(
            self._url + self._pause_path,
            headers=self._headers,
            json={
                "option": option,
            },
            timeout=self._default_timeout,
        )

    def resume_plan(self):
        return requests.post(
            self._url + self._resume_path,
            headers=self._headers,
            timeout=self._default_timeout,
        )

    def abort_plan(self):
        return requests.post(
            self._url + self._abort_path,
            headers=self._headers,
            timeout=self._default_timeout,
        )

    def is_connected(self):
        http_server_status = self.status()
        re_environment_open = http_server_status["worker_environment_exists"]
        re_running = http_server_status["re_state"] is not None
        return re_environment_open and re_running

    def get_console_uid(self):
        response = requests.get(
            self._url + self._console_uid_path,
            headers=self._headers,
            timeout=self._default_timeout,
        )
        return self.format_response(response)["console_output_uid"]

    def show_console_output(self, value=None):
        if value is None:
            value = []
        for console_msg in value:
            new_console_line = console_msg["msg"]
            new_console_line = new_console_line.strip()
            if new_console_line != "":
                is_error = "[E " in new_console_line
                is_warning = "[W " in new_console_line
                is_debug = ("[I " in new_console_line) or ("[D " in new_console_line)
                if is_error:
                    self.user_level_log.error(new_console_line)
                elif is_warning:
                    self.user_level_log.warning(new_console_line)
                elif not is_debug:
                    self.user_level_log.info(new_console_line)

    def update_console_output(self):
        current_uid = self.get_console_uid()
        if self.console_output_uid != current_uid:
            response = requests.get(
                self._url + self._console_path,
                headers=self._headers,
                json={"last_msg_uid": self.last_msg_uid},
                timeout=self._default_timeout,
            )
            output = self.format_response(response)
            self.last_msg_uid = output["last_msg_uid"]
            self.console_output_uid = current_uid
            return output["console_output_msgs"]
        return []
