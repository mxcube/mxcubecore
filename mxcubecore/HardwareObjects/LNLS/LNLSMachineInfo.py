import gevent

from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo


class LNLSMachineInfo(AbstractMachineInfo):
    """
    This class implements the beam current visualization for LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSMachineInfo.LNLSMachineInfo
    epics:
    "SI-Glob:AP-CurrInfo:Current-Mon":
        channels:
            current:
                suffix: ''
                polling_period: 200
    "SI-Glob:AP-CurrInfo:Lifetime-Mon":
        channels:
            lifetime:
                suffix: ''
                polling_period: 200
    "AS-Glob:AP-MachShift:Mode-Sts":
        channels:
            message:
                suffix: ''
                polling_period: 200
    "AS-Glob:AP-InjCtrl:Mode-Sel":
        channels:
            fill_mode:
                suffix: ''
                polling_period: 200
    configuration:
        parameters: '["current", "message", "lifetime", "fill_mode"]'
    """

    def init(self):
        super().init()
        gevent.spawn(self._update_me)

    def _update_me(self):
        while True:
            gevent.sleep(5)
            self.update_value()

    def get_current(self) -> float:
        return self.get_channel_value("current")

    def get_message(self) -> str:
        mode_ring = self.get_channel_value("message")
        if 0 <= mode_ring <= 9:
            mode_ring = str(mode_ring)
            values = {
                "0": "Users",
                "1": "Commissioning",
                "2": "Conditioning",
                "3": "Injection",
                "4": "Machine Study",
                "5": "Maintenance",
                "6": "Standby",
                "7": "Shutdown",
                "8": "MachineStartup",
                "9": "BLComissioning",
            }
            return values[mode_ring]
        return "UNKNOWN"

    def get_lifetime(self) -> str:
        hour = int(self.get_channel_value("lifetime") / 3600)
        minute = int(((hour * 60) % 60))
        return f"{hour}:{minute}"

    def get_fill_mode(self) -> str:
        return self.get_channel_value("fill_mode")
