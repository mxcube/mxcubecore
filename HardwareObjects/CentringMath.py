from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import Procedure
import math
import numpy
import logging


class CentringMath(Procedure):
    """
    CentringMath procedure
    """

    def init(self):
        """
        Ggonio axes definitions are static
        motorHO is expected to have get_value() that returns coordinate in mm
        """
        self.motorConstraints = []
        self.gonioAxes = []
        for axis in self["gonioAxes"]:
            self.gonioAxes.append(
                {
                    "type": axis.type,
                    "direction": eval(axis.direction),
                    "motor_name": axis.motorname,
                    "motor_HO": HWR.get_hardware_repository().get_hardware_object(
                        axis.motorHO
                    ),
                }
            )

        """
        This version is lacking video microscope object. Therefore we model only
        static camera axes directions, but no camera axes scaling or center - which
        are dynamic. Therefore, camera coordinates are relative, in mm.
        """
        self.cameraAxes = []
        for axis in self["cameraAxes"]:
            self.cameraAxes.append(
                {"axis_name": axis.axisname, "direction": eval(axis.direction)}
            )

        self.mI = numpy.diag([1.0, 1.0, 1.0])  # identity matrix
        self.calibrate()

    def centringToScreen(self, centring_dict, factorized=False):
        if not factorized:
            self.factorize()
        """
        One _must_ self.factorize() before!!!
        Input positions are indexed by motor name as in original MiniDiff.
        For symmetry, output camera coordinates are indexed by camera axis name, like {'X':<float>,'Y':<float>},
        but not just x,y as in original MiniDiff.
        """
        tau_cntrd = self.centred_positions_to_vector(centring_dict)
        if self.tau is not None and tau_cntrd is not None:
            dum = self.tau - tau_cntrd
            return self.vector_to_camera_coordinates(numpy.dot(self.F.T, dum))

    def listOfCentringsToScreen(self, list_of_centring_dicts):
        self.factorize()
        lst = []
        logging.getLogger("HWR").debug(
            " in listOfCentringToScreen - %s points in list "
            % len(list_of_centring_dicts)
        )
        for centring in list_of_centring_dicts:
            lst.append(self.centringToScreen(centring, factorized=True))
        return lst

    def factorize(self):
        # this should be automatic, on the gonio both rot and trans datum update
        self.F = self.factor_matrix()
        self.tau = self.translation_datum()

    def initCentringProcedure(self):
        # call before starting rotate-click sequence
        self.centringDataTensor = []
        self.centringDataMatrix = []
        self.motorConstraints = []

    def appendCentringDataPoint(self, camera_coordinates):
        # call after each click and send click points - but relative in mm
        self.centringDataTensor.append(self.factor_matrix())
        self.centringDataMatrix.append(
            self.camera_coordinates_to_vector(camera_coordinates)
        )

    def centeredPosition(self, return_by_name=False):
        # call after appending the last click. Returns a {motorHO:position} dictionary.
        M = numpy.zeros(shape=(self.translationAxesCount, self.translationAxesCount))
        V = numpy.zeros(shape=(self.translationAxesCount))

        for l in range(0, self.translationAxesCount):
            for i in range(0, len(self.centringDataMatrix)):
                for k in range(0, len(self.cameraAxes)):
                    V[l] += (
                        self.centringDataTensor[i][l][k] * self.centringDataMatrix[i][k]
                    )
            for m in range(0, self.translationAxesCount):
                for i in range(0, len(self.centringDataMatrix)):
                    for k in range(0, len(self.cameraAxes)):
                        M[l][m] += (
                            self.centringDataTensor[i][l][k]
                            * self.centringDataTensor[i][m][k]
                        )
        tau_cntrd = numpy.dot(numpy.linalg.pinv(M, rcond=1e-6), V)

        # print tau_cntrd
        tau_cntrd = self.apply_constraints(M, tau_cntrd)
        # print tau_cntrd

        return self.vector_to_centred_positions(
            -tau_cntrd + self.translation_datum(), return_by_name
        )

    def apply_constraints(self, M, tau):
        V = numpy.zeros(shape=(self.translationAxesCount))
        for c in self.motorConstraints:
            for i in range(0, self.translationAxesCount):
                V[i] = M[i][c["index"]]
                M[i][c["index"]] = 0.0
                M[c["index"]][i] = 0.0
            tau = tau - (c["position"] - tau[c["index"]]) * numpy.dot(
                numpy.linalg.pinv(M, rcond=1e-6), V
            )
            tau[c["index"]] = c["position"]
        return tau

    def factor_matrix(self):
        # This should be connected to goniostat rotation datum update, with F globalized
        F = numpy.zeros(shape=(self.translationAxesCount, len(self.cameraAxes)))
        R = self.mI
        j = 0
        for axis in self.gonioAxes:  # skip base gonio axis
            if axis["type"] == "rotation":
                Ra = self.rotation_matrix(
                    axis["direction"], axis["motor_HO"].get_value()
                )
                R = numpy.dot(Ra, R)
            elif axis["type"] == "translation":
                f = numpy.dot(R, axis["direction"])
                k = 0
                for camera_axis in self.cameraAxes:
                    F[j][k] = numpy.dot(f, camera_axis["direction"])
                    k += 1
                j += 1
        return F

    def calibrate(self):
        count = 0
        for axis in self.gonioAxes:  # make first gonio rotation matrix for base axis
            if axis["type"] == "rotation":
                d = axis["direction"]
                axis["mT"] = numpy.outer(d, d)
                axis["mC"] = numpy.array(
                    [[0.0, -d[2], d[1]], [d[2], 0.0, -d[0]], [-d[1], d[0], 0.0]]
                )
            elif axis["type"] == "translation":
                axis["index"] = count
                count += 1
        self.translationAxesCount = count
        count = 0
        for axis in self.cameraAxes:
            axis["index"] = count
            count += 1

    def rotation_matrix(self, dir, angle):
        rads = angle * math.pi / 180.0
        cosa = math.cos(rads)
        sina = math.sin(rads)
        mT = numpy.outer(dir, dir)
        mC = numpy.array(
            [[0.0, -dir[2], dir[1]], [dir[2], 0.0, -dir[0]], [-dir[1], dir[0], 0.0]]
        )
        return self.mI * cosa + mT * (1.0 - cosa) + mC * sina

    def translation_datum(self):
        vector = []
        for axis in self.gonioAxes:
            if axis["type"] == "translation":
                vector.append(axis["motor_HO"].get_value())
        return vector

    def centred_positions_to_vector(self, centrings_dictionary):
        vector = numpy.zeros(shape=(self.translationAxesCount))
        index = 0
        for axis in self.gonioAxes:
            if axis["type"] == "translation":
                motname = axis["motor_name"]
                if centrings_dictionary[motname] is not None:
                    vector[index] = float(centrings_dictionary[axis["motor_name"]])
                else:
                    return None
                index += 1
        return vector

    def vector_to_centred_positions(self, vector, return_by_name=False):
        dic = {}
        index = 0
        for axis in self.gonioAxes:
            if axis["type"] == "translation":
                if return_by_name:
                    dic[axis["motor_name"]] = vector[index]
                else:
                    dic[axis["motor_HO"]] = vector[index]
                index += 1
        return dic

    def camera_coordinates_to_vector(self, camera_coordinates_dictionary):
        vector = []
        for index in range(0, len(self.cameraAxes)):
            vector.append(
                camera_coordinates_dictionary[self.cameraAxes[index]["axis_name"]]
            )
        return vector

    def vector_to_camera_coordinates(self, vector):
        dic = {}
        index = 0
        for axis in self.cameraAxes:
            dic[axis["axis_name"]] = vector[index]
            index += 1
        return dic

    def appendMotorConstraint(self, motor_HO, position):
        index = 0
        self.motorConstraints = []
        for axis in self.gonioAxes:
            if axis["type"] == "translation" and motor_HO is axis["motor_HO"]:
                index += 1
                self.motorConstraints.append(
                    {"index": index, "position": motor_HO.get_value() - position}
                )
                return

    def camera2alignmentMotor(self, motor_HO, camxy):
        # motor_HO must reference an ALIGNMENT motor!
        # finds a projection of camera vector {"X":x,"Y":y} onto a motor axis of a
        # motor_HO
        for axis in self.gonioAxes:
            if axis["type"] == "translation" and motor_HO is axis["motor_HO"]:
                res = 0.0
                for camaxis in self.cameraAxes:
                    res = (
                        res
                        + numpy.dot(axis["direction"], camaxis["direction"])
                        * camxy[camaxis["axis_name"]]
                    )
                return res
