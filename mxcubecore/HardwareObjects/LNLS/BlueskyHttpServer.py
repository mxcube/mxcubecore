from mxcubecore.BaseHardwareObjects import HardwareObject


class BlueskyHttpServer(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

    def init(self):
        super().init()
        self.api = self.get_command_object("bluesky_http_server")
        self.api.username = "mnc-data"

    def execute_plan(self, plan_name, kwargs=None):
        response = self.api.execute_plan(plan_name=plan_name, kwargs=kwargs)
        response_content = response.json()
        if response_content["success"]:
            try:
                self.api.monitor_manager_state("executing_queue")
                self.api.monitor_manager_state("idle")
            except TimeoutError:
                self.log.exception("The Bluesky plan has timed out!")
        else:
            self.log.exception(response_content["msg"])

    def monitor_bluesky_state(self, response, state):
        response_content = response.json()
        if response_content["success"]:
            try:
                self.api.monitor_manager_state(state)
            except TimeoutError:
                self.log.exception("The Bluesky action has timed out!")
        else:
            self.log.exception(response_content["msg"])

    def pause(self, option="deferred"):
        response = self.api.pause_plan(option)
        self.monitor_bluesky_state(response, state="paused")

    def abort(self):
        if self.api.status()["manager_state"] == "executing_queue":
            self.pause(option="immediate")
        response = self.api.abort_plan()
        self.monitor_bluesky_state(response, state="idle")

    def resume(self):
        response = self.api.resume_plan()
        self.monitor_bluesky_state(response, state="executing_queue")
