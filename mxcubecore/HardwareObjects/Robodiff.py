from HardwareRepository.TaskUtils import *
import MiniDiff
import os
import sys
import logging
import time

class Robodiff(MiniDiff.MiniDiff):      
    def __init__(self, name):
        MiniDiff.MiniDiff.__init__(self, name)

    def init(self): 
        self.controller = self.getObjectByRole("controller")
        MiniDiff.MiniDiff.init(self)

    def oscil(self, *args, **kwargs):
        self.controller.oscil(*args, **kwargs)

    def moveToCentredPosition(self,*args):
        return self._moveToCentredPosition(wait=False)

    @task
    def _moveToCentredPosition(self):
        return

    def takeSnapshots(self, wait=False):
        return

    def getPositions(self):
        return { "phi": self.controller.phi.position(),
                 "focus": 0,
                 "phiy": 0,
                 "phiz": 0,
                 "sampx": 0, 
                 "sampy": 0,
                 "kappa": 0,
                 "kappa_phi": 0,
                 "zoom": 0 }


 
