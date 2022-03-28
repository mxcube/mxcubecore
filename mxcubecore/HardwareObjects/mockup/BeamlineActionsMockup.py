import sys
import typing
import enum


from mxcubecore.TaskUtils import task
from mxcubecore.CommandContainer import CommandObject
from mxcubecore.HardwareObjects.BeamlineActions import BeamlineActions, ControllerCommand, AnnotatedCommand
from mxcubecore.utils.conversion import camel_to_snake

import gevent
import logging


class EnumArg(str, enum.Enum):
    centring = "Centring"
    data_collection = 'DataCollection'
    beam_location = 'BeamLocation'
    transfer = "Transfer"
    unknown = "Unknown"


class SimulatedAction:
    def __call__(self, *args, **kw):
        gevent.sleep(3)
        return args


class SimulatedActionError:
    def __call__(self, *args, **kw):
        raise RuntimeError("Simulated error")


class LongSimulatedAction:
    def __call__(self, *args, **kw):
        for i in range(10):
            gevent.sleep(1)
            logging.getLogger("user_level_log").info("%d, sleeping for 1 second", i + 1)

        return args


class Arg(typing.NamedTuple):
    name: str
    unit: str
    alias: str


class Anneal2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    #@argument(ArgMeta("time", "s", "time"))
    def anneal2(self, time: float) -> None:
        print("ANNEAL")
        gevent.sleep(float(time))


class QuickRealign2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def quick_realign2(self) -> None:
        print("REALIGN")


class ComboTest2(AnnotatedCommand):
    def __init__(self, *args):
        super().__init__(*args)

    def combo_test2(self, combo_arg: EnumArg) -> None:
        print("COMBO")


class BeamlineActionsMockup(BeamlineActions):
    def __init__(self, *args):
        super().__init__(*args)