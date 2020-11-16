import gevent
import tempfile
import logging
import math
import os
import time
import copy
import numpy
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects import sample_centring
from HardwareRepository.HardwareObjects import queue_model_objects as qmo
from HardwareRepository import HardwareRepository as HWR

try:
    from Qub.Tools import QubImageSave
except ImportError:
    pass


class myimage:
    def __init__(self, drawing):
        self.drawing = drawing
        matrix = self.drawing.matrix()
        self.zoom = 1
        if matrix is not None:
            self.zoom = matrix.m11()

    def save(self, filename=None):
        self.img = self.drawing.getPPP()

        if filename is None:
            fd, name = tempfile.mkstemp()
            os.close(fd)
        else:
            name = filename

        QubImageSave.save(name, self.img, self.drawing.canvas(), self.zoom, "JPEG")

        if filename is None:
            f = open(name, "r")
            self.imgcopy = f.read()
            f.close()
            os.unlink(name)

    def __str__(self):
        self.save()
        return self.imgcopy


def set_light_in(light, light_motor, zoom):
    with gevent.Timeout(5, RuntimeError("Could not set light in")):
        light_level = None

        if light is not None:
            light.wagoIn()

        # No light level, choose default
        if light_motor.get_value() == 0:
            zoom_level = int(zoom.get_value())
            light_level = None

            try:
                light_level = zoom["positions"][0][zoom_level].getProperty("lightLevel")
            except IndexError:
                logging.getLogger("HWR").info("Could not get default light level")
                light_level = 1

        if light_level:
            light_motor.set_value(light_level)

        while light.getWagoState() != "in":
            time.sleep(0.5)


def take_snapshots(number_of_snapshots, light, light_motor, phi, zoom, drawing):
    if number_of_snapshots <= 0:
        return

    centredImages = []

    set_light_in(light, light_motor, zoom)

    for i, angle in enumerate([0] + [-90] * (number_of_snapshots - 1)):
        phi.set_value_relative(angle)
        logging.getLogger("HWR").info("MiniDiff: taking snapshot #%d", i + 1)
        centredImages.append((phi.get_value(), str(myimage(drawing))))

    centredImages.reverse()  # snapshot order must be according to positive rotation direction

    return centredImages


class MiniDiff(Equipment):
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    # MOVE_TO_BEAM_MODE = "Move to Beam"

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        qmo.CentredPosition.set_diffractometer_motor_names(
            "phi",
            "focus",
            "phiz",
            "phiy",
            "zoom",
            "sampx",
            "sampy",
            "kappa",
            "kappa_phi",
        )

        self.phiMotor = None
        self.kappaMotor = None
        self.kappaPhiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.lightWago = None
        self.currentSampleInfo = None
        self.aperture = None
        self.cryostream = None
        self.beamstop = None
        self.capillary = None

        self.pixelsPerMmY = None
        self.pixelsPerMmZ = None
        self.centredTime = 0
        self.user_confirms_centring = True
        self.do_centring = True
        self.chiAngle = 0.0

        self.connect(self, "equipmentReady", self.equipmentReady)
        self.connect(self, "equipmentNotReady", self.equipmentNotReady)

    def if_role_set_attr(self, role_name):
        obj = self.getObjectByRole(role_name)

        if obj is not None:
            setattr(self, role_name, obj)

    def init(self):
        self.centringMethods = {
            MiniDiff.MANUAL3CLICK_MODE: self.start_manual_centring,
            MiniDiff.C3D_MODE: self.start_auto_centring,
        }

        self.cancel_centring_methods = {}

        self.current_centring_procedure = None
        self.currentCentringMethod = None

        self.centringStatus = {"valid": False}

        self.chiAngle = self.getProperty("chi", 0)

        try:
            phiz_ref = self["centringReferencePosition"].getProperty("phiz")
        except:
            phiz_ref = None

        try:
            phiy_ref = self["centringReferencePosition"].getProperty("phiy")
        except:
            phiy_ref = None

        self.phiMotor = self.getObjectByRole("phi")
        self.phizMotor = self.getObjectByRole("phiz")
        self.phiyMotor = self.getObjectByRole("phiy")
        self.zoomMotor = self.getObjectByRole("zoom")
        self.lightMotor = self.getObjectByRole("light")
        self.focusMotor = self.getObjectByRole("focus")
        self.sampleXMotor = self.getObjectByRole("sampx")
        self.sampleYMotor = self.getObjectByRole("sampy")
        self.kappaMotor = self.getObjectByRole("kappa")
        self.kappaPhiMotor = self.getObjectByRole("kappa_phi")

        # mh 2013-11-05:why is the channel read directly? disabled for the moment
        # HWR.beamline.sample_view.camera.add_channel({ 'type': 'tango', 'name': 'jpegImage' }, "JpegImage")

        self.centringPhi = sample_centring.CentringMotor(self.phiMotor, direction=-1)
        self.centringPhiz = sample_centring.CentringMotor(
            self.phizMotor, reference_position=phiz_ref
        )
        self.centringPhiy = sample_centring.CentringMotor(
            self.phiyMotor, reference_position=phiy_ref
        )
        self.centringSamplex = sample_centring.CentringMotor(self.sampleXMotor)
        self.centringSampley = sample_centring.CentringMotor(self.sampleYMotor)

        roles_to_add = ["aperture", "beamstop", "cryostream", "capillary"]

        for role in roles_to_add:
            self.if_role_set_attr(role)

        hwr = HWR.getHardwareRepository()
        wl_prop = self.getProperty("wagolight")
        if wl_prop is not None:
            try:
                self.lightWago = hwr.getHardwareObject(wl_prop)
            except Exception:
                pass

        if self.phiMotor is not None:
            self.connect(self.phiMotor, "stateChanged", self.phiMotorStateChanged)
            self.connect(self.phiMotor, "valueChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: phi motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.phizMotor is not None:
            self.connect(self.phizMotor, "stateChanged", self.phizMotorStateChanged)
            self.connect(self.phizMotor, "valueChanged", self.phizMotorMoved)
            self.connect(self.phizMotor, "valueChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: phiz motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.phiyMotor is not None:
            self.connect(self.phiyMotor, "stateChanged", self.phiyMotorStateChanged)
            self.connect(self.phiyMotor, "valueChanged", self.phiyMotorMoved)
            self.connect(self.phiyMotor, "valueChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: phiy motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.zoomMotor is not None:
            self.connect(
                self.zoomMotor, "valueChanged", self.zoomMotorPredefinedPositionChanged
            )

            self.connect(
                self.zoomMotor,
                "predefinedPositionChanged",
                self.zoomMotorPredefinedPositionChanged,
            )
            self.connect(self.zoomMotor, "stateChanged", self.zoomMotorStateChanged)
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: zoom motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.sampleXMotor is not None:
            self.connect(
                self.sampleXMotor, "stateChanged", self.sampleXMotorStateChanged
            )
            self.connect(self.sampleXMotor, "valueChanged", self.sampleXMotorMoved)
            self.connect(
                self.sampleXMotor, "valueChanged", self.emitDiffractometerMoved
            )
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: sampx motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.sampleYMotor is not None:
            self.connect(
                self.sampleYMotor, "stateChanged", self.sampleYMotorStateChanged
            )
            self.connect(self.sampleYMotor, "valueChanged", self.sampleYMotorMoved)
            self.connect(
                self.sampleYMotor, "valueChanged", self.emitDiffractometerMoved
            )
        else:
            logging.getLogger("HWR").error(
                "MiniDiff: sampx motor is not defined in minidiff equipment %s",
                str(self.name()),
            )
        # if HWR.beamline.sample_view.camera is None:
        #     logging.getLogger("HWR").error(
        #         "MiniDiff: camera is not defined in minidiff equipment %s",
        #         str(self.name()),
        #     )
        # else:
        #     self.imgWidth, self.imgHeight = (
        #         HWR.beamline.sample_view.camera.getWidth(),
        #         HWR.beamline.sample_view.camera.getHeight(),
        #     )
        if HWR.beamline.sample_changer is None:
            logging.getLogger("HWR").warning(
                "MiniDiff: sample changer is not defined in minidiff equipment %s",
                str(self.name()),
            )
        else:
            try:
                self.connect(
                    HWR.beamline.sample_changer,
                    "sampleIsLoaded",
                    self.sampleChangerSampleIsLoaded,
                )
            except Exception:
                logging.getLogger("HWR").exception(
                    "MiniDiff: could not connect to sample changer smart magnet"
                )
        if self.lightWago is not None:
            self.connect(self.lightWago, "wagoStateChanged", self.wagoLightStateChanged)
        else:
            logging.getLogger("HWR").warning(
                "MiniDiff: wago light is not defined in minidiff equipment %s",
                str(self.name()),
            )
        if self.aperture is not None:
            self.connect(
                self.aperture, "predefinedPositionChanged", self.apertureChanged
            )
            self.connect(self.aperture, "positionReached", self.apertureChanged)

        # Agree on a correct method name, inconsistent arguments for move_to_beam, disabled temporarily
        # self.move_to_coord = self.move_to_beam()

    # Contained Objects
    # NBNB Temp[orary hack - should be cleaned up together with configuration
    @property
    def omega(self):
        """omega motor object

        Returns:
            AbstractActuator
        """
        return self.phiMotor

    @property
    def kappa(self):
        """kappa motor object

        Returns:
            AbstractActuator
        """
        return self.kappaMotor

    @property
    def kappa_phi(self):
        """kappa_phi motor object

        Returns:
            AbstractActuator
        """
        return self.kappaPhiMotor

    @property
    def centring_x(self):
        """centring_x motor object

        Returns:
            AbstractActuator
        """
        return self.sampleXMotor

    @property
    def centring_y(self):
        """centring_y motor object

        Returns:
            AbstractActuator
        """
        return self.sampleYMotor

    @property
    def alignment_x(self):
        """alignment_x motor object (also used as graphics.focus)

        Returns:
            AbstractActuator
        """
        return self.focusMotor

    @property
    def alignment_y(self):
        """alignment_y motor object

        Returns:
            AbstractActuator
        """
        return self.phiyMotor

    @property
    def alignment_z(self):
        """alignment_z motor object

        Returns:
            AbstractActuator
        """
        return self.phizMotor

    @property
    def zoom(self):
        """zoom motor object

        NBNB HACK TODO - ocnfigure this in graphics object
        (which now calls this property)

        Returns:
            AbstractActuator
        """
        return self.zoomMotor

    def save_snapshot(self, filename):
        set_light_in(self.lightWago, self.lightMotor, self.zoomMotor)
        img = myimage(self._drawing)
        img.save(filename)

    def set_light_in(self):
        set_light_in(self.lightWago, self.lightMotor, self.zoomMotor)

    def setSampleInfo(self, sample_info):
        self.currentSampleInfo = sample_info

    def emitDiffractometerMoved(self, *args):
        self.emit("diffractometerMoved", ())

    def is_ready(self):
        return self.is_valid() and not any(
            [
                m.motorIsMoving()
                for m in (
                    self.sampleXMotor,
                    self.sampleYMotor,
                    self.zoomMotor,
                    self.phiMotor,
                    self.phizMotor,
                    self.phiyMotor,
                )
            ]
        )

    def is_valid(self):
        return (
            self.sampleXMotor is not None
            and self.sampleYMotor is not None
            and self.zoomMotor is not None
            and self.phiMotor is not None
            and self.phizMotor is not None
            and self.phiyMotor is not None
            and HWR.beamline.sample_view.camera is not None
        )

    def in_plate_mode(self):
        return False

    def apertureChanged(self, *args):
        # will trigger minidiffReady signal for update of beam size in video
        self.equipmentReady()

    def equipmentReady(self):
        self.emit("minidiffReady", ())

    def equipmentNotReady(self):
        self.emit("minidiffNotReady", ())

    def wagoLightStateChanged(self, state):
        pass

    def phiMotorStateChanged(self, state):
        self.emit("phiMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def phizMotorStateChanged(self, state):
        self.emit("phizMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def phiyMotorStateChanged(self, state):
        self.emit("phiyMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def getCalibrationData(self, offset):
        if self.zoomMotor is not None:
            if self.zoomMotor.hasObject("positions"):
                for position in self.zoomMotor["positions"]:
                    if abs(position.offset - offset) <= self.zoomMotor.delta:
                        calibrationData = position["calibrationData"]
                        return (
                            float(calibrationData.pixelsPerMmY) or 0,
                            float(calibrationData.pixelsPerMmZ) or 0,
                        )
        return (None, None)

    def get_pixels_per_mm(self):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(None)
        return self.pixelsPerMmY, self.pixelsPerMmZ

    def getBeamInfo(self, callback=None):
        beam_info = HWR.beamline.beam.get_beam_info()
        if callable(callback):
            callback(beam_info)
        return beam_info

    def zoomMotorPredefinedPositionChanged(self, positionName, offset=None):
        if not positionName:
            return
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(offset)
        self.emit("zoomMotorPredefinedPositionChanged", (positionName, offset))

    def zoomMotorStateChanged(self, state):
        self.emit("zoomMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def sampleXMotorStateChanged(self, state):
        self.emit("sampxMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def sampleYMotorStateChanged(self, state):
        self.emit("sampyMotorStateChanged", (state,))
        self.emit("minidiffStateChanged", (state,))

    def invalidateCentring(self):
        if self.current_centring_procedure is None and self.centringStatus["valid"]:
            self.centringStatus = {"valid": False}
            self.emitProgressMessage("")
            self.emit("centringInvalid", ())

    def phizMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
            self.invalidateCentring()

    def phiyMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
            self.invalidateCentring()

    def sampleXMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
            self.invalidateCentring()

    def sampleYMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
            self.invalidateCentring()

    def sampleChangerSampleIsLoaded(self, state):
        if time.time() - self.centredTime > 1.0:
            self.invalidateCentring()

    # def getBeamPosX(self):
    #     return self.imgWidth / 2
    #
    # def getBeamPosY(self):
    #     return self.imgHeight / 2

    def move_to_beam(self, x, y):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        dx = (x - beam_pos_x) / self.pixelsPerMmY
        dy = (y - beam_pos_y) / self.pixelsPerMmZ

        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )

        sampx = -self.centringSamplex.direction * self.centringSamplex.get_value()
        sampy = self.centringSampley.direction * self.centringSampley.get_value()

        phiy = self.centringPhiy.direction * self.centringPhiy.get_value()
        phiz = self.centringPhiz.direction * self.centringPhiz.get_value()

        rotMatrix = numpy.matrix(
            [
                [math.cos(phi_angle), -math.sin(phi_angle)],
                [math.sin(phi_angle), math.cos(phi_angle)],
            ]
        )
        invRotMatrix = numpy.array(rotMatrix.I)

        dsampx, dsampy = numpy.dot(numpy.array([0, dy]), invRotMatrix)

        chi_angle = math.radians(self.chiAngle)
        chiRot = numpy.matrix(
            [
                [math.cos(chi_angle), -math.sin(chi_angle)],
                [math.sin(chi_angle), math.cos(chi_angle)],
            ]
        )

        sx, sy = numpy.dot(numpy.array([dsampx, dsampy]), numpy.array(chiRot))

        sampx = sampx + sx
        sampy = sampy + sy
        phiy = phiy + dx

        try:
            self.centringSamplex.set_value(-sampx)
            self.centringSampley.set_value(sampy)
            self.centringPhiy.set_value(-phiy)
        except Exception:
            logging.getLogger("HWR").exception(
                "MiniDiff: could not center to beam, aborting"
            )

    def getAvailableCentringMethods(self):
        return self.centringMethods.keys()

    def start_centring_method(self, method, sample_info=None):
        if not self.do_centring:
            self.emitCentringStarted(method)

            def fake_centring_procedure():
                return {"motors": {}, "method": method, "valid": True}

            self.current_centring_procedure = gevent.spawn(fake_centring_procedure)
            self.emitCentringSuccessful()
            return

        if self.currentCentringMethod is not None:
            logging.getLogger("HWR").error(
                "MiniDiff: already in centring method %s" % self.currentCentringMethod
            )
            return

        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centringStatus = {"valid": False, "startTime": curr_time}

        self.emitCentringStarted(method)

        try:
            #self.wait_ready()
            fun = self.centringMethods[method]
        except KeyError as diag:
            logging.getLogger("HWR").error(
                "MiniDiff: unknown centring method (%s)" % str(diag)
            )
            self.emitCentringFailed()
        else:
            try:
                fun(sample_info)
            except Exception:
                logging.getLogger("HWR").exception("MiniDiff: problem while centring")
                self.emitCentringFailed()

    def cancel_centring_method(self, reject=False):
        if self.current_centring_procedure is not None:
            try:
                self.current_centring_procedure.kill()
            except Exception:
                logging.getLogger("HWR").exception(
                    "MiniDiff: problem aborting the centring method"
                )
            try:
                fun = self.cancel_centring_methods[self.currentCentringMethod]
            except KeyError as diag:
                self.emitCentringFailed()
            else:
                try:
                    fun()
                except Exception:
                    self.emitCentringFailed()
        else:
            self.emitCentringFailed()

        self.emitProgressMessage("")

        if reject:
            self.rejectCentring()

    def currentCentringMethod(self):
        return self.currentCentringMethod

    def saveCurrentPos(self):
        self.centringStatus["motors"] = self.get_positions()
        self.accept_centring()

    def start_manual_centring(self, sample_info=None):
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        self.wait_ready(5)
        logging.getLogger("HWR").info("Starting centring procedure ...")

        self.current_centring_procedure = sample_centring.start(
            {
                "phi": self.centringPhi,
                "phiy": self.centringPhiy,
                "sampx": self.centringSamplex,
                "sampy": self.centringSampley,
                "phiz": self.centringPhiz,
            },
            self.pixelsPerMmY,
            self.pixelsPerMmZ,
            beam_pos_x,
            beam_pos_y,
            chi_angle=self.chiAngle,
        )

        self.current_centring_procedure.link(self.manualCentringDone)

    def motor_positions_to_screen(self, centred_positions_dict):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )
        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0
        phi_angle = math.radians(
            self.centringPhi.direction * self.centringPhi.get_value()
        )
        sampx = self.centringSamplex.direction * (
            centred_positions_dict["sampx"] - self.centringSamplex.get_value()
        )
        sampy = self.centringSampley.direction * (
            centred_positions_dict["sampy"] - self.centringSampley.get_value()
        )
        phiy = self.centringPhiy.direction * (
            centred_positions_dict["phiy"] - self.centringPhiy.get_value()
        )
        phiz = self.centringPhiz.direction * (
            centred_positions_dict["phiz"] - self.centringPhiz.get_value()
        )
        rotMatrix = numpy.matrix(
            [
                math.cos(phi_angle),
                -math.sin(phi_angle),
                math.sin(phi_angle),
                math.cos(phi_angle),
            ]
        )
        rotMatrix.shape = (2, 2)
        invRotMatrix = numpy.array(rotMatrix.I)
        dsx, dsy = (
            numpy.dot(numpy.array([sampx, sampy]), invRotMatrix) * self.pixelsPerMmY
        )
        chi_angle = math.radians(self.chiAngle)
        chiRot = numpy.matrix(
            [
                math.cos(chi_angle),
                -math.sin(chi_angle),
                math.sin(chi_angle),
                math.cos(chi_angle),
            ]
        )
        chiRot.shape = (2, 2)
        sx, sy = numpy.dot(numpy.array([0, dsy]), numpy.array(chiRot))  # .I))
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()

        x = sx + (phiy * self.pixelsPerMmY) + beam_pos_x
        y = sy + (phiz * self.pixelsPerMmZ) + beam_pos_y

        return float(x), float(y)

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()
        dx = (x - beam_pos_x) / self.pixelsPerMmY
        dy = (y - beam_pos_y) / self.pixelsPerMmZ

        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(
            self.zoomMotor.get_value()
        )

        if None in (self.pixelsPerMmY, self.pixelsPerMmZ):
            return 0, 0

        phi_angle = math.radians(self.centringPhi.get_value())
        sampx = self.centringSamplex.get_value()
        sampy = self.centringSampley.get_value()
        phiy = self.centringPhiy.get_value()
        phiz = self.centringPhiz.get_value()

        rotMatrix = numpy.matrix(
            [
                math.cos(phi_angle),
                -math.sin(phi_angle),
                math.sin(phi_angle),
                math.cos(phi_angle),
            ]
        )
        rotMatrix.shape = (2, 2)
        invRotMatrix = numpy.array(rotMatrix.I)

        dsampx, dsampy = numpy.dot(numpy.array([0, dy]), invRotMatrix)
        sampx = sampx + dsampx
        sampy = sampy + dsampy
        phiy = phiy - dx

        #        chi_angle = math.radians(self.chiAngle)
        #        chiRot = numpy.matrix([math.cos(chi_angle), -math.sin(chi_angle),
        #                               math.sin(chi_angle), math.cos(chi_angle)])
        #        chiRot.shape = (2,2)
        #        sx, sy = numpy.dot(numpy.array([0, dsy]),
        #                           numpy.array(chiRot)) ))

        return {
            "phi": self.centringPhi.get_value(),
            "phiz": float(phiz),
            "phiy": float(phiy),
            "sampx": float(sampx),
            "sampy": float(sampy),
        }

    def manualCentringDone(self, manual_centring_procedure):
        try:
            motor_pos = manual_centring_procedure.get()
            if isinstance(motor_pos, gevent.GreenletExit):
                raise motor_pos
        except Exception:
            logging.exception("Could not complete manual centring")
            self.emitCentringFailed()
        else:
            self.emitProgressMessage("Moving sample to centred position...")
            self.emitCentringMoving()
            try:
                sample_centring.end()
            except Exception:
                logging.exception("Could not move to centred position")
                self.emitCentringFailed()

            # logging.info("EMITTING CENTRING SUCCESSFUL")
            self.centredTime = time.time()
            self.emitCentringSuccessful()
            self.emitProgressMessage("")

    def autoCentringDone(self, auto_centring_procedure):
        self.emitProgressMessage("")
        self.emit("newAutomaticCentringPoint", (-1, -1))

        try:
            res = auto_centring_procedure.get()
        except Exception:
            logging.error("Could not complete automatic centring")
            logging.getLogger("user_level_log").info("Automatic loop centring failed")
            self.emitCentringFailed()
            self.rejectCentring()
        else:
            if res is None:
                logging.error("Could not complete automatic centring")
                logging.getLogger("user_level_log").info("Automatic loop centring failed")
                self.emitCentringFailed()
                self.rejectCentring()
            else:
                self.emitCentringSuccessful()
                if not self.user_confirms_centring:
                    self.accept_centring()
                logging.getLogger("user_level_log").info("Automatic loop centring successful")

    def start_auto_centring(self, sample_info=None, loop_only=False):
        beam_pos_x, beam_pos_y = HWR.beamline.beam.get_beam_position_on_screen()

        self.set_phase("centring", wait=True)

        self.wait_ready(30)

        self.current_centring_procedure = sample_centring.start_auto(
            HWR.beamline.sample_view.camera,
            {
                "phi": self.centringPhi,
                "phiy": self.centringPhiy,
                "sampx": self.centringSamplex,
                "sampy": self.centringSampley,
                "phiz": self.centringPhiz,
            },
            self.pixelsPerMmY,
            self.pixelsPerMmZ,
            beam_pos_x,
            beam_pos_y,
            chi_angle=float(self.chiAngle),
            msg_cb=self.emitProgressMessage,
            new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", point),
        )

        self.current_centring_procedure.link(self.autoCentringDone)

        self.emitProgressMessage("Starting automatic centring procedure...")

    @task
    def moveToCentredPosition(self, centred_position):
        return self.move_motors(centred_position.as_dict())

    def imageClicked(self, x, y, xi, yi):
        logging.getLogger("user_level_log").info("Centring click at, x: %s, y: %s" % (int(x), int(y)))
        sample_centring.user_click(x, y, False)

    def emitCentringStarted(self, method):
        self.currentCentringMethod = method
        self.emit("centringStarted", (method, False))
        logging.getLogger("user_level_log").info("Starting centring")

    def accept_centring(self):
        self.centringStatus["valid"] = True
        self.centringStatus["accepted"] = True
        self.emit("centringAccepted", (True, self.get_centring_status()))
        logging.getLogger("user_level_log").info("Centring successful")

    def rejectCentring(self):
        if self.current_centring_procedure:
            self.current_centring_procedure.kill()
        self.centringStatus = {"valid": False}
        self.emitProgressMessage("")
        self.emit("centringAccepted", (False, self.get_centring_status()))
        logging.getLogger("user_level_log").info("Centring cancelled")

    def emitCentringMoving(self):
        self.emit("centringMoving", ())

    def emitCentringFailed(self):
        self.centringStatus = {"valid": False}
        method = self.currentCentringMethod
        self.currentCentringMethod = None
        self.current_centring_procedure = None
        self.emit("centringFailed", (method, self.get_centring_status()))
        logging.getLogger("user_level_log").info("Centring Failed")

    def emitCentringSuccessful(self):
        if self.current_centring_procedure is not None:
            curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.centringStatus["endTime"] = curr_time
            self.centringStatus["motors"] = self.get_positions()
            centred_pos = self.current_centring_procedure.get()
            for role in self.centringStatus["motors"]:
                motor = self.getObjectByRole(role)
                try:
                    self.centringStatus["motors"][role] = centred_pos[motor]
                except KeyError:
                    continue

            self.centringStatus["method"] = self.currentCentringMethod
            self.centringStatus["valid"] = True

            method = self.currentCentringMethod
            self.emit("centringSuccessful", (method, self.get_centring_status()))
            self.currentCentringMethod = None
            self.current_centring_procedure = None
        else:
            logging.getLogger("HWR").debug(
                "MiniDiff: trying to emit centringSuccessful outside of a centring"
            )

    def emitProgressMessage(self, msg=None):
        # logging.getLogger("HWR").debug("%s: %s", self.name(), msg)
        self.emit("progressMessage", (msg,))

    def get_centring_status(self):
        return copy.deepcopy(self.centringStatus)

    def get_positions(self):
        return {
            "phi": float(self.phiMotor.get_value()),
            "focus": float(self.focusMotor.get_value()),
            "phiy": float(self.phiyMotor.get_value()),
            "phiz": float(self.phizMotor.get_value()),
            "sampx": float(self.sampleXMotor.get_value()),
            "sampy": float(self.sampleYMotor.get_value()),
            "kappa": float(self.kappaMotor.get_value()) if self.kappaMotor else None,
            "kappa_phi": float(self.kappaPhiMotor.get_value())
            if self.kappaPhiMotor
            else None,
            "zoom": float(self.zoomMotor.get_value()),
        }

    def move_motors(self, roles_positions_dict):
        motor = {
            "phi": self.phiMotor,
            "focus": self.focusMotor,
            "phiy": self.phiyMotor,
            "phiz": self.phizMotor,
            "sampx": self.sampleXMotor,
            "sampy": self.sampleYMotor,
            "kappa": self.kappaMotor,
            "kappa_phi": self.kappaPhiMotor,
            "zoom": self.zoomMotor,
        }

        for role, pos in roles_positions_dict.items():
            m = motor.get(role)
            if None not in (m, pos):
                m.set_value(pos)

        # TODO: remove this sleep, the motors states should
        # be MOVING since the beginning (or READY if move is
        # already finished)
        time.sleep(1)

        while not all(
            [m.get_state() == m.READY for m in motor.values() if m is not None]
        ):
            time.sleep(0.1)

    def take_snapshots(self, image_count, wait=False):
        HWR.beamline.sample_view.camera.forceUpdate = True

        snapshotsProcedure = gevent.spawn(
            take_snapshots,
            image_count,
            self.lightWago,
            self.lightMotor,
            self.phiMotor,
            self.zoomMotor,
            self._drawing,
        )
        self.emit("centringSnapshots", (None,))
        self.emitProgressMessage("Taking snapshots")
        self.centringStatus["images"] = []
        snapshotsProcedure.link(self.snapshotsDone)

        if wait:
            self.centringStatus["images"] = snapshotsProcedure.get()

    def snapshotsDone(self, snapshotsProcedure):
        HWR.beamline.sample_view.camera.forceUpdate = False

        try:
            self.centringStatus["images"] = snapshotsProcedure.get()
        except Exception:
            logging.getLogger("HWR").exception(
                "MiniDiff: could not take crystal snapshots"
            )
            self.emit("centringSnapshots", (False,))
            self.emitProgressMessage("")
        else:
            self.emit("centringSnapshots", (True,))
            self.emitProgressMessage("")
        self.emitProgressMessage("Sample is centred!")
        # self.emit('centringAccepted', (True,self.get_centring_status()))

    def simulateAutoCentring(self, sample_info=None):
        pass

    def wait_ready(self, timeout=None):
        pass
