import math
import os
import time
import logging

import MiniDiff


class MaxLabMicrodiff(MiniDiff.MiniDiff):
    def init(self):
        self.phiMotor = self.getDeviceByRole("phi")
        self.x_calib = self.addChannel(
            {
                "type": "exporter",
                "exporter_address": self.phiMotor.exporter_address,
                "name": "x_calib",
            },
            "CoaxCamScaleX",
        )
        self.y_calib = self.addChannel(
            {
                "type": "exporter",
                "exporter_address": self.phiMotor.exporter_address,
                "name": "y_calib",
            },
            "CoaxCamScaleY",
        )
        self.moveMultipleMotors = self.addCommand(
            {
                "type": "exporter",
                "exporter_address": self.phiMotor.exporter_address,
                "name": "move_multiple_motors",
            },
            "SyncMoveMotors",
        )

        MiniDiff.MiniDiff.init(self)

        self.centringPhiy.direction = -1

    def getCalibrationData(self, offset):
        return (1.0 / self.x_calib.getValue(), 1.0 / self.y_calib.getValue())

    def emitCentringSuccessful(self):
        # save position in MD2 software
        self.getCommandObject("save_centring_position")()

        # do normal stuff
        return MiniDiff.MiniDiff.emitCentringSuccessful(self)

    def backLightOut(self):
        logging.getLogger("HWR").info(
            "taking light out before data collection (light object is %s) "
            % str(self.lightWago)
        )
        if self.lightWago is not None:
            self.lightWago.wagoOut()

    def getBeamInfo(self, update_beam_callback):
        if self.aperture is not None:
            curpos = self.aperture.getCurrentPositionName()
            logging.getLogger("HWR").info(" Aperture is %s \n" % curpos)
            size_x = size_y = eval(str(curpos)) / 1000.0
            ret = {"size_x": size_x, "size_y": size_y, "shape": "circular"}
            update_beam_callback(ret)

        # get_beam_info = self.getCommandObject("getBeamInfo")
        # get_beam_info(callback=update_beam_callback, error_callback=None, wait=True)
