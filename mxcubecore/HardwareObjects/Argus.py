import json
import logging
from atexit import register
from os import kill
from signal import SIGTERM
from subprocess import Popen
from threading import Thread
from time import sleep
from uuid import uuid1

try:
    import argussight.grpc.argus_service_pb2 as pb2
    import argussight.grpc.argus_service_pb2_grpc as pb2_grpc
    import grpc
    from argussight.grpc.helper_functions import (
        pack_to_any,
        unpack_from_any,
    )
except ImportError:
    logging.getLogger("HWR").warning(
        "Argussight package is not installed.",
    )
    pass

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


# This function is needed o ensure that multi_views is correctly loaded
# from xml and yml files
def ensure_list(value):
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return [value]


class Argus(HardwareObject):
    def __init__(self, name, retry_delay=1):
        super().__init__(name)
        channel = grpc.insecure_channel(
            self.get_property("grpc_url", "localhost:50051")
        )
        self.stub = pb2_grpc.SpawnerServiceStub(channel)
        self.running_processes = {}
        self.available_classes = {}
        self.last_response = {}
        self.streams = []
        self.closable_running = (
            False  # keep track if there are any closable processes running
        )
        self.retry_delay = retry_delay
        self._video_stream_processes: list[Popen] = []
        self._streams_to_run = []
        self._argus_pid: Popen | None = None
        self._main_stream = None
        self._multi_views = {}
        thread = Thread(target=self.emit_process_change)
        thread.daemon = True
        thread.start()

    def init(self):
        # start the argus server
        self._argus_pid = Popen(["argussight"], close_fds=True, shell=False)

        streams_to_run = []
        streams_to_run = self.get_property("streams", [])
        for stream in streams_to_run.get("stream", []):
            stream["id"] = str(uuid1())

            if stream.get("create"):
                logging.getLogger("HWR").info("Creating %s stream", stream["name"])
                stream_options = [
                    "video-streamer",
                    "-uri",
                    stream["uri"],
                    "-hs",
                    "localhost",
                    "-p",
                    str(stream["port"]),
                    "-of",
                    "MPEG1",
                    "-q",
                    "4",
                    "-s",
                    ", ".join(map(str, (659, 493))),
                    "-id",
                    stream["id"],
                ]
                if stream.get("auth"):
                    stream_options.extend(
                        [
                            "-auth",
                            stream["auth"],
                            "-user",
                            stream["user"],
                            "-pass",
                            stream["pass"],
                        ],
                    )
                self._video_stream_processes.append(
                    Popen(
                        stream_options,
                        close_fds=True,
                        shell=False,
                    ),
                )

            if stream.get("main"):
                logging.getLogger("HWR").info(
                    "Setting %s as main stream",
                    stream["name"],
                )
                self._main_stream = stream["name"]
                # Set the main camera stream size, so that the front-end and sampleview
                # can rely on it being set when the stream is added through Argus
                main_camera = HWR.beamline.sample_view.camera
                main_camera.set_stream_size(
                    main_camera.get_width(), main_camera.get_height()
                )

        self._streams_to_run = streams_to_run.get("stream", [])

        multi_views = self.get_property("multi_views", {}).get("view", [])
        multi_views = multi_views if isinstance(multi_views, list) else [multi_views]

        self._multi_views = {
            view["name"]: ensure_list(view.get("streams")) for view in multi_views
        }

        register(self.cleanup)

        super().init()

    def cleanup(self):
        logging.getLogger("HWR").info("Shutting down streams connected to Argus...")
        for streaming_process in self._video_stream_processes:
            if not streaming_process.poll():
                kill(streaming_process.pid, SIGTERM)
        logging.getLogger("HWR").info("Shutting down Argus server...")
        kill(self._argus_pid.pid, SIGTERM)

    def get_main_camera_stream(self):
        return self._main_stream

    def get_processes_from_server(self) -> dict:
        try:
            response = self.stub.GetProcesses(
                pb2.GetProcessesRequest(),
                wait_for_ready=True,
            )
            if response.status == "success":
                if self.last_response == {} or self.last_response["status"] == "error":
                    self.last_response = {}

                running_processes = {}
                for key, process in response.running_processes.items():
                    settings = {}
                    for setting, value in process.settings.items():
                        settings[setting] = unpack_from_any(value)
                    running_processes[key] = {
                        "type": process.type,
                        "commands": list(process.commands),
                        "settings": settings,
                    }
                return (
                    running_processes,
                    list(response.available_process_types),
                    # A dict is used to match web expectations
                    dict.fromkeys(response.streams),
                )
        except grpc.RpcError:
            logging.getLogger("HWR").exception(
                "GRPC Connection error occured during Argussight server connection",
            )
            self.emit_last_response_change("error", "Cannot connect to the server")
            return {"Error": {"state": "UNKNOWN", "type": "Server-Connection"}}, {}, []
        except Exception:
            logging.getLogger("HWR").exception(
                "Error occured during Argussight server connection",
            )
            self.emit_last_response_change("error", "Unknown error occured")
            return {"Error": {"state": "UNKNOWN", "type": "Server-Connection"}}, {}, []

    def emit_process_change(self):
        while True:
            current_running, classes, streams = self.get_processes_from_server()
            if (
                current_running != self.running_processes
                or classes != self.available_classes
            ):
                self.running_processes = current_running
                self.available_classes = classes

                # check if any process started by user is running
                self.closable_running = False
                for process in current_running:
                    if current_running[process]["type"] in classes:
                        self.closable_running = True
                        break
                self.emit("processesChanged")
                self.emit("lastResponseChanged")
            if streams != self.streams:
                self.streams = streams
                self.emit("streamsChanged")
            for stream in self._streams_to_run:
                if stream["name"] not in self.streams:
                    logging.getLogger("HWR").info("Trying to add %s", stream["name"])
                    self._add_stream(stream["name"], stream["port"], stream["id"])

            sleep(self.retry_delay)

    def get_processes(self) -> dict:
        return {
            "running": self.running_processes,
            "available": self.available_classes,
            "closable_running": self.closable_running,
        }

    def get_last_response(self) -> dict:
        return self.last_response

    def stop_process(self, name: str):
        logging.getLogger("HWR").info("Sending termination request for %s", name)
        response = self.stub.TerminateProcesses(
            pb2.TerminateProcessesRequest(names=[name]),
        )
        self.emit_last_response_change(response.status, response.error_message)

    def start_process(self, name: str, process_type: str):
        logging.getLogger("HWR").info("Sending start process request for %s", name)
        response = self.stub.StartProcesses(
            pb2.StartProcessesRequest(name=name, type=process_type),
        )
        self.emit_last_response_change(response.status, response.error_message)

    def manage_process(self, name: str, command: str):
        logging.getLogger("HWR").info(
            "Sending manage request for command %s of process %s",
            command,
            name,
        )
        request = pb2.ManageProcessesRequest(
            name=name,
            command=command,
        )
        response = self.stub.ManageProcesses(request)
        self.emit_last_response_change(response.status, response.error_message)

    def emit_last_response_change(self, status, error_message):
        self.last_response = {
            "status": status,
            "error_message": error_message,
        }
        self.emit("lastResponseChanged")

    def get_streams(self):
        return self.streams

    def get_multi_views(self):
        return self._multi_views

    def change_settings(self, name: str, settings: dict) -> None:
        converted_settings = {}
        for key, setting in settings.items():
            converted_settings[key] = pack_to_any(setting)
        request = pb2.ChangeSettingsRequest(name=name, settings=converted_settings)
        response = self.stub.ChangeSettings(request)
        self.emit_last_response_change(response.status, response.error_message)

    def _add_stream(self, name, port, stream_id):
        try:
            self.stub.AddStream(
                pb2.AddStreamRequest(
                    name=name,
                    port=str(port),
                    stream_id=stream_id,
                ),
            )
        except Exception:
            logging.getLogger("HWR").exception(
                "Couldn't add camera stream to argussight server",
            )
