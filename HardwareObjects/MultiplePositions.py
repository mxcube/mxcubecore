"""
TITLE
MultiplePositions Hardware Object

DESCRIPTION
This object manages the movement of several motors to predefined positions.

<username> : name of the multiplepositions object
<mode>     : there is two ways of managing the change of predefined positions
              absolute: change the value of a predefined position by another
                        absolute position
              relative: do not change the absolute value of the predefined
                        position but the user value of the motors concerned

<motors>
    <device role="role1" ... :list of motors to be moved to reach a predefined
    <device role="role2" ...  position. the "role" will be used to referenced
        ...                   the motors in the definitions of the predefined
<motors>                      positions

<deltas>                    : for each motor you define the windows used to
    <role1>val1</role1>       determine that a motor as reach a position
    <role2>val2</role2>
    ...
</deltas>

<positions>
    <poisition>
        <name>      : name of a predefined position. Must be unique in the file
        <role1>val1 : position of the motor "role1" for the predefined position
                     "name"
        <role2>val2 : position of the motor "role2" for the predefined position
                     "name"
        <resoy>8.69565217391e-07</resoy> : for all the position, independant
        <beamx>100</beamx>                 value with keyword can be added,
                                           saved, read ...
    </position>
    ...
</position>


METHOD
    name:           get_state
    input par.:     None
    output par.:    state
    description:    return an and on the state of all the  motor used in the
                    object

    name:           moveToPosition
    input par.:     name
    output par.:    None
    description:    move all motors to the predefined position "position"

    name:           get_value
    input par.:     None
    output par.:    position
    description:    return the name of the current predefined position.
                    return None if all motors are not in their psotion

    name:           setNewPositions
    input par.:     name, newPositions
    output par.:    None
    description:    For the position "name", change the motors positions set
                    in "newPositions", a dictionary with motor role as keys
                    and new motor position as values.
                    Save the new values in the xml file

    name:           getPositionKeyValue
    input par.:     name, key
    output par.:    value
    description:    return the value of the independant "key" field of
                    the predefined position "name"

    name:           setPositionKeyValue
    input par.:     name, key, value
    output par.:    None
    description:    Change in the object and in the xml file the value of the
                    independant field "key" in the predefined position "name"

    name:           getRoles
    input par.:     None
    output par.:    roles[]
    description:    return the list of motor's role used in the objects


SIGNAL
    name:           stateChanged
    parameter:      state
    description:    send the new state of the object when it changes

    name:           noPosition
    parameter:      None
    description:    sent when after a position change of any of the motor
                    the object is not in any of the predefined positions

    name:           positionReached
    parameter:      positionName
    description:    sent when after a position change of any of the motor
                    the object has reach a predefined position.
                    The parameter is the name of this position.

TEMPLATE
<equipment class="MultiplePositions">
    <username>VLM Zoom</username>
    <mode>absolute</mode>
    <motors>
        <device role="zoom" hwrid="/berru/zoom"></device>
    </motors>

    <deltas>
        <zoom>0.1</zoom>
    </deltas>

    <positions>
        <position>
            <name>1X</name>
            <zoom>0</zoom>
            <resox>-4.16666666667e-07</resox>
            <resoy>7.35294117647e-07</resoy>
            <beamx>537</beamx>
            <beamy>313</beamy>
        </position>
        <position>
            <name>6X</name>
            <zoom>1</zoom>
            <resox>-5.52486187845e-07</resox>
            <resoy>8.69565217391e-07</resoy>
            <beamx>100</beamx>
            <beamy>100</beamy>
        </position>
        <position>
            <name>12X</name>
            <zoom>2</zoom>
            <resox>0.0000004</resox>
            <resoy>0.0000004</resoy>
            <beamx>200</beamx>
            <beamy>200</beamy>
        </position>
    </positions>
</equipment>"""

try:
    from xml.etree import cElementTree  # python2.5
except ImportError:
    import cElementTree

from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class MultiplePositions(Equipment):
    def init(self):
        try:
            self.mode
        except AttributeError:
            self.mode = "absolute"

        motors = self["motors"]
        self.roles = motors.getRoles()

        self.deltas = {}
        try:
            # WARNING self.deltas is a LINK to the INTERNAL properties dictionary
            # modifying it modifies the GLOBAL properties, not just the local copy
            # Maybe do self["deltas"].getProperties().copy()?
            self.deltas = self["deltas"].getProperties()
        except BaseException:
            logging.getLogger().error("No deltas.")

        self.positions = {}
        self.positionsIndex = []
        try:
            positions = self["positions"]
        except BaseException:
            logging.getLogger().error("No positions.")
        else:
            for position in positions:
                name = position.getProperty("name")
                if name is not None:
                    self.positionsIndex.append(name)
                    self.positions[name] = {}

                    motpos = position.getProperties()
                    motroles = list(motpos.keys())

                    for role in self.roles:
                        self.positions[name][role] = motpos[role]
                else:
                    logging.getLogger().error("No name for position.")

        self.motors = {}
        for mot in self["motors"]:
            self.motors[mot.getMotorMnemonic()] = mot
            self.connect(mot, "moveDone", self.checkPosition)
            self.connect(mot, "valueChanged", self.checkPosition)
            self.connect(mot, "stateChanged", self.stateChanged)

    def get_state(self):
        if not self.is_ready():
            return ""

        state = "READY"
        for mot in self.motors.values():
            if mot.get_state() == mot.MOVING:
                state = "MOVING"
            elif mot.get_state() == mot.UNUSABLE:
                return "UNUSABLE"

        return state

    def stateChanged(self, state):
        self.emit("stateChanged", (self.get_state(),))
        self.checkPosition()

    def moveToPosition(self, name, wait=False):
        move_list = []
        for role in self.roles:
            device = self.getDeviceByRole(role)
            pos = self.positions[name][role]
            move_list.append((device, pos))

        for mot, pos in move_list:
            if mot is not None:
                mot.set_value(pos)

        if wait:
            [mot.waitEndOfMove() for mot, pos in move_list if mot is not None]
        """
        for mne,pos in self.positions[name].items():
        self.motors[mne].set_value(pos)
        """

    def get_value(self):
        if not self.is_ready():
            return None

        for posName, position in self.positions.items():
            findPosition = 0

            for role in self.roles:
                pos = position[role]
                mot = self.getDeviceByRole(role)

                if mot is not None:
                    motpos = mot.get_value()
                    try:
                        if (
                            motpos < pos + self.deltas[role]
                            and motpos > pos - self.deltas[role]
                        ):
                            findPosition += 1
                    except BaseException:
                        continue

            if findPosition == len(self.roles):
                return posName

        return None

    def checkPosition(self, *args):
        if not self.is_ready():
            return None

        posName = self.get_value()

        if posName is None:
            self.emit("noPosition", ())
            return None
        else:
            self.emit("positionReached", (posName,))
            return posName

    def setNewPositions(self, name, newPositions):
        position = self.__getPositionObject(name)

        if position is None:
            self.checkPosition()
            return

        for role, pos in list(newPositions.items()):
            self.positions[name][role] = pos
            position.setProperty(role, pos)

        self.checkPosition()
        self.commit_changes()

    def getPositionKeyValue(self, name, key):
        position = self.__getPositionObject(name)

        if position is None:
            return None

        return position.getProperty(key)

    def setPositionKeyValue(self, name, key, value):
        xml_tree = cElementTree.fromstring(self.xml_source())
        positions = xml_tree.find("positions")

        pos_list = positions.findall("position")
        for pos in pos_list:
            if pos.find("name").text == name:
                if pos.find(key) is not None:
                    position = self.__getPositionObject(name)
                    position.setProperty(key, str(value))
                    self.commit_changes()
                    return True
                else:
                    key_el = cElementTree.SubElement(pos, key)
                    key_el.text = value
                    print((cElementTree.tostring(xml_tree)))
                    self.rewrite_xml(cElementTree.tostring(xml_tree))
                    return True

        return False

    def __getPositionObject(self, name):
        for position in self["positions"]:
            if position.getProperty("name") == name:
                return position

        return None

    def getRoles(self):
        return self.roles

    def addPosition(self, el_dict):
        xml_tree = cElementTree.fromstring(self.xml_source())
        positions = xml_tree.find("positions")

        pos = cElementTree.SubElement(positions, "position")

        for key, val in el_dict.items():
            sel = cElementTree.SubElement(pos, key)
            sel.text = val

        self.rewrite_xml(cElementTree.tostring(xml_tree))

    def remPosition(self, name):
        xml_tree = cElementTree.fromstring(self.xml_source())
        positions = xml_tree.find("positions")

        pos_list = positions.findall("position")
        for pos in pos_list:
            if pos.find("name").text == name:
                positions.remove(pos)

        self.rewrite_xml(cElementTree.tostring(xml_tree))

    def addField(self, name, key, val):
        pass

    def remField(self, name, key):
        pass


"""
        xml_tree = cElementTree.fromstring(self.xml_source())
        for elt in xml_tree.findall(".//position"):
           if elt.find("name").text=="12X":
             new_elt = cElementTree.Element("bidule")
             new_elt.text = "HELLO"
             elt.append(new_elt)
        self.rewrite_xml(cElementTree.tostring(xml_tree))
"""
