from mxcubecore.BaseHardwareObjects import HardwareObject
import os
import sys


class ObjectsController(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self, *args):
        sys.path.insert(0, self.get_property("source"))
        config = __import__("config", globals(), locals(), [])

        cfg_file = os.path.join(
            self.get_property("source"), self.get_property("config_file")
        )
        config.load(cfg_file)
        objects = config.get_context_objects("default")

        for obj_name, obj in objects.items():
            setattr(self, obj_name, obj)

    def centrebeam(self):
        self.robot.centrebeam()
