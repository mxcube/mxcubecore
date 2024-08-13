import grpc
import gevent
from google.protobuf.json_format import MessageToDict
from typing import List

import argussight.grpc.argus_service_pb2 as pb2
import argussight.grpc.argus_service_pb2_grpc as pb2_grpc

from mxcubecore.BaseHardwareObjects import HardwareObject


class Argus(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        channel = grpc.insecure_channel("localhost:50051")
        self.stub = pb2_grpc.SpawnerServiceStub(channel)
        self.running_processes = {}
        self.available_classes = {}
        self.last_response = {}
        self.server_communication_error = False
        gevent.spawn(self.emit_process_change)

    def init(self):
        super().init()

    def get_processes_from_server(self) -> dict:
        try:
            response = self.stub.GetProcesses(pb2.GetProcessesRequest())
            if response.status == "success":
                if self.last_response == {} or self.last_response["status"] == "error":
                    self.last_response = {}
                response_dict = MessageToDict(response)
                return (
                    response_dict["runningProcesses"],
                    response_dict["availableProcessTypes"],
                )
        except Exception as e:
            self.server_communication_error = True
            self.last_response = {"status": "error", "error_message": str(e)}
            self.emit("lastResponseChanged")
            return {"Error": {"state": "UNKNOWN", "type": "Server-Connection"}}, {}

    def emit_process_change(self):
        while True:
            current_running, classes = self.get_processes_from_server()
            if (
                current_running != self.running_processes
                or classes != self.available_classes
            ):
                self.running_processes = current_running
                self.available_classes = classes
                self.emit("processesChanged")
                self.emit("lastResponseChanged")
            gevent.sleep(2)

    def get_processes(self) -> dict:
        return {"running": self.running_processes, "available": self.available_classes}

    def get_last_response(self) -> dict:
        return self.last_response

    def stop_process(self, name: List[str]):
        print(f"Sending termination request for {name}")
        response = self.stub.TerminateProcesses(
            pb2.TerminateProcessesRequest(names=name)
        )
        self.emit_last_response_change(response)
        return True

    def start_process(self, name: List[str]):
        print(f"Sending start process request for {name}")
        response = self.stub.StartProcesses(pb2.StartProcessesRequest(names=name))
        self.emit_last_response_change(response)

    def emit_last_response_change(self, response: any):
        self.last_response = {
            "status": response.status,
            "error_message": response.error_message,
        }
        self.emit("lastResponseChanged")
