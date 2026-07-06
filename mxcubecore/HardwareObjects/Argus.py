import json
import logging
from atexit import register
from enum import Enum
from os import kill
from signal import SIGTERM
from subprocess import DEVNULL, Popen
from threading import Event, Thread
from time import sleep
from uuid import uuid1

from pydantic import ValidationError

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
        "Please install mxcube with the Argus extra to use the Argus hardware object",
    )
    pass

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.model.argus_model import (
    ArgusTrigger,
    HiddenInitially,
    HideAction,
    InitialVisibilityCondition,
)


# This function is needed o ensure that multi_views is correctly loaded
# from xml and yml files
def ensure_list(value):
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return [value]


stop_event = Event()


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
        self._argus_pid = Popen(
            ["argussight", "--config", self.get_property("config_path")],
            stdout=DEVNULL,
            stderr=DEVNULL,
            close_fds=True,
            shell=False,
        )

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
        self._init_triggers()

        super().init()

    def _make_trigger_callback(self, trigger: ArgusTrigger):
        def callback(value):
            for case in trigger.cases:
                if (
                    case.value == value.value
                    if isinstance(value, Enum)
                    else case.value == value
                ):
                    for action in case.actions:
                        for stream in trigger.streams:
                            action.make_request(self.stub, stream)

        return callback

    def _init_triggers(self):
        self._trigger_callbacks = []
        triggers = []

        for trigger in self.get_property("triggers", {}).get("trigger", []):
            try:
                triggers.append(ArgusTrigger.parse_obj(trigger))
            except ValidationError as val_error:
                logging.getLogger("HWR").warning(
                    "Error parsing Argus trigger, %s will not be initialized\n%s",
                    trigger.get("name", "unnamed trigger"),
                    val_error,
                )

        for trigger in triggers:
            callback = self._make_trigger_callback(trigger)

            # we need to keep a reference to the callback
            # to avoid it being garbage collected
            self._trigger_callbacks.append(callback)

            for event in trigger.on:
                ho = HWR.beamline.get_object_by_role(event.hwobj_role)
                if ho is None:
                    logging.getLogger("HWR").warning(
                        "Cannot find hardware object with role %s for Argus trigger %s",
                        event.hwobj_role,
                        trigger.name,
                    )
                    continue

                ho.connect(event.event, callback)

    def cleanup(self):
        stop_event.set()
        logging.getLogger("HWR").info("Shutting down Argus server...")
        kill(self._argus_pid.pid, SIGTERM)

        sleep(1)  # give the server some time to shutdown before killing the streams
        logging.getLogger("HWR").info("Shutting down streams connected to Argus...")
        for streaming_process in self._video_stream_processes:
            if streaming_process.poll() is None:
                kill(streaming_process.pid, SIGTERM)

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
        while not stop_event.is_set():
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
                    hidden_initially = (
                        HiddenInitially.parse_obj(stream["hidden_initially"])
                        if stream.get("hidden_initially", None)
                        else None
                    )
                    self._add_stream(
                        stream["name"], stream["port"], stream["id"], hidden_initially
                    )

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

    def _check_hidden_condition(
        self, condition: InitialVisibilityCondition, stream_name: str
    ):
        ho = HWR.beamline.get_object_by_role(condition.hwobj_role)
        if not ho:
            logging.getLogger("HWR").warning(
                "Hardware object with role %s not found, hidding %s provisionally",
                condition.hwobj_role,
                stream_name,
            )
            return True
        attribute = getattr(ho, condition.attribute)
        return (
            attribute.value == condition.equals
            if isinstance(attribute, Enum)
            else attribute == condition.equals
        )

    def _add_stream(self, name, port, stream_id, hidden_initially: HiddenInitially):
        if stop_event.is_set():
            return
        try:
            self.stub.AddStream(
                pb2.AddStreamRequest(
                    name=name,
                    port=str(port),
                    stream_id=stream_id,
                ),
            )
            if hidden_initially:
                if hidden_initially.always or self._check_hidden_condition(
                    hidden_initially.when, name
                ):
                    action = HideAction(type="Hide", reason=hidden_initially.reason)
                    action.make_request(self.stub, name)
        except Exception:
            logging.getLogger("HWR").exception(
                "Couldn't add camera stream to argussight server",
            )
