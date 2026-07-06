from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.BeamlineActions import BeamlineActions


class LNLSBaseAction:
    """
    Base class for both LNLSBeamlineActions and LNLSSampleChangerAction
    """

    def __init__(self):
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.diffractometer = HWR.beamline.get_object_by_role("diffractometer")
        self.STATES = HardwareObjectState
        self.ROBOT_READY = AbstractSampleChanger.SampleChangerState.Ready
        self.ROBOT_MOVING = AbstractSampleChanger.SampleChangerState.Moving

    def update_diffractometer_states(self, state_value):
        """
        Turn off all motors while robot is moving
        Make them ready again if robot is ready
        """
        d = self.diffractometer

        if not d.kappa.check_is_absent():
            d.kappa.update_state(state_value)

        if not d.kappa_phi.check_is_absent():
            d.kappa_phi.update_state(state_value)

        d.omega.update_state(state_value)
        d.phiy.update_state(state_value)
        d.phiz.update_state(state_value)
        d.sampx.update_state(state_value)
        d.sampy.update_state(state_value)
        d.sampz.update_state(state_value)

    def change_robot_state(self, robot_state, motor_state):
        self.sc._set_state(robot_state)
        self.update_diffractometer_states(motor_state)


class LNLSBeamlineActions(LNLSBaseAction, BeamlineActions):
    """
    This class allows sample changer actions to be accessible from other classes
    of mxcubecore or from the 'Beamline Ations' options at frontend. To use it
    at mxcubecore code:

    from mxcubecore.HardwareObjects.LNLS.LNLSBeamlineActions import Mount
    mount = Mount()
    mount.mount(1)

    To implement a button that performs these actions at 'Beamline Actions',
    implement the command at the yaml file.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSBeamlineActions.LNLSBeamlineActions
    configuration:
    commands: [{
                "type": "controller",
                "name": "Soak",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Soak"
                },
                {
                "type": "controller",
                "name": "Dry",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Dry"
                },
                {
                "type": "controller",
                "name": "Home",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Home"
                },
                ]
    """

    def __init__(self, name):
        BeamlineActions.__init__(self, name)
        LNLSBaseAction.__init__(self)

    def abort_command(self, cmd_name):
        """
        For the cases of Dry, Home and Soak, if robot
        movement gets aborted, call the bluesky API and
        allow motor movement after.
        There is no abort option for mount/unmount in the UI.
        """
        self._bluesky_api.abort()
        self.change_robot_state(self.ROBOT_READY, self.STATES.READY)


class LNLSSampleChangerAction(LNLSBaseAction):
    def __init__(self, movement_option):
        super().__init__()
        self.movement_option = movement_option

    def __call__(self, *args, **kwargs):
        """
        Turn off all motors while robot is moving
        Wait for bluesky plan to end
        Make motors ready when bluesky plan finishes
        """
        self.change_robot_state(self.ROBOT_MOVING, self.STATES.OFF)
        self._bluesky_api.execute_plan(
            plan_name="run_sample_changer_command",
            kwargs={"movement_option": self.movement_option, **kwargs},
        )
        self.change_robot_state(self.ROBOT_READY, self.STATES.READY)
        return args


class Soak(LNLSSampleChangerAction):
    def __init__(self):
        super().__init__("soak")


class Home(LNLSSampleChangerAction):
    def __init__(self):
        super().__init__("home")


class Dry(LNLSSampleChangerAction):
    def __init__(self):
        super().__init__("dry")


class MountAction(LNLSSampleChangerAction):
    def __init__(self):
        super().__init__("mount")

    def mount(self, sample_value):
        return self(sample_value=sample_value)

    def unmount(self):
        self.movement_option = "unmount"
        return self()
