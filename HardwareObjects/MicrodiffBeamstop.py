from HardwareRepository.BaseHardwareObjects import Equipment

"""
Move the beamstop or the capillary, using the exporter protocol
Example xml file:
<equipment class="MicrodiffBeamstop">
  <username>Beamstop</username>
  <device role="beamstop" hwrid="/udiff_beamstop"></device>
  <save_cmd_name>saveBeamstopBeamPosition</save_cmd_name>
  <motors>
    <device role="horizontal" hwrid="/bstopy"></device>
    <device role="vertical" hwrid="/bstopz"></device>
  </motors>
</equipment>

Example udiff_beamstop.xml
<device class="MicrodiffInOut">
  <username>Beamstop</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <cmd_name>BeamstopPosition</cmd_name>
  <private_state>{"OFF":"out", "BEAM":"in"}</private_state>
  <timeout>100</timeout>
</device>

Example bstopy.xml (for bstopz only the motor name changes)
<device class="MD2Motor">
  <username>bstopy</username>
  <exporter_address>wid30bmd2s:9001</exporter_address>
  <actuator_name>BeamstopY</actuator_name>
  <GUIstep>0.01</GUIstep>
   <unit>1e-3</unit>
</device>

When used with capillary, only the command and motor names change.
Example capillary xml file:
<equipment class="MicrodiffBeamstop">
  <username>Capillary</username>
  <device role="beamstop" hwrid="/udiff_capillary"></device>
  <save_cmd_name>saveCapillaryBeamPosition</save_cmd_name>
  <motors>
    <device role="horizontal" hwrid="/capy"></device>
    <device role="vertical" hwrid="/capz"></device>
  </motors>
</equipment>
"""


class MicrodiffBeamstop(Equipment):
    def init(self):
        self.beamstop = self.get_object_by_role("beamstop")
        self.beamstop.state_attr.connect_signal("update", self.checkPosition)

        self.motors = self["motors"]
        self.roles = self.motors.get_roles()

        save_cmd_name = self.get_property("save_cmd_name")
        self.beamstopSetInPosition = self.beamstop.add_command(
            {
                "type": "exporter",
                "name": "bs_set_in",
                "address": self.beamstop.get_property("exporter_address"),
            },
            save_cmd_name,
        )

        # next two lines - just to make the beamstop brick happy
        self.amplitude = 0
        self.positions = self.beamstop.moves

    def moveToPosition(self, name):
        if name == "in":
            self.beamstop.actuatorIn(wait=True)
        elif name == "out":
            self.beamstop.actuatorOut(wait=True)
        self.checkPosition()

    def connect_notify(self, signal):
        self.checkPosition()

    def is_ready(self):
        return True

    def get_state(self):
        return "READY"

    def get_value(self):
        return self.checkPosition(noEmit=True)

    def checkPosition(self, pos=None, noEmit=False):
        if pos is None:
            pos = self.beamstop.get_actuator_state()
        try:
            pos = self.beamstop.states[pos]
        except Exception:
            pass

        if not noEmit:
            if pos:
                self.emit("positionReached", pos)
            else:
                self.emit("noPosition", ())
        return pos

    def setNewPositions(self, name, newPositions):
        if name == "in":
            self.beamstopSetInPosition()

    def getRoles(self):
        return self.roles
