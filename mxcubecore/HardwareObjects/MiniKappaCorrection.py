from mxcubecore.BaseHardwareObjects import Device
import math
import numpy as np


class MiniKappaCorrection(Device):
    """
    this will work on numbers only!
    """

    def init(self):
        self.align_direction = np.array(
            [0, 0, -1.0]
        )  # check this on MD2 - this equalled phi direction on md3!!!
        self.mI = np.diag([1.0, 1.0, 1.0])
        self.kappa = self.calibrate(self["kappa"])
        self.phi = self.calibrate(self["phi"])
        self.cos2a = pow(np.dot(self.kappa["direction"], self.align_direction), 2)

    def shift(self, kappa1, phi1, x, kappa2, phi2):

        tk = self.kappa["position"]
        tp = self.phi["position"]

        Rk2 = self.rotation_matrix(self.kappa, kappa2)
        Rk1 = self.rotation_matrix(self.kappa, -kappa1)
        Rp = self.rotation_matrix(self.phi, phi2 - phi1)

        a = tk - np.dot(Rk1, (tk - x))
        b = tp - np.dot(Rp, (tp - a))
        return tk - np.dot(Rk2, (tk - b))

    def calibrate(self, ax):
        axis = {}
        d = np.array(eval(ax.direction))
        axis["direction"] = d
        axis["position"] = np.array(eval(ax.position))
        axis["mT"] = np.outer(d, d)
        axis["mC"] = np.array(
            [[0.0, -d[2], d[1]], [d[2], 0.0, -d[0]], [-d[1], d[0], 0.0]]
        )
        return axis

    def rotation_matrix(self, axis, angle):
        rads = angle * math.pi / 180.0
        cosa = math.cos(rads)
        sina = math.sin(rads)
        return self.mI * cosa + axis["mT"] * (1.0 - cosa) + axis["mC"] * sina

    def alignVector(self, t1, t2, kappa, phi):
        x = np.array(t1) - np.array(t2)  # rotating vector
        Rk = self.rotation_matrix(self.kappa, -kappa)  #
        Rp = self.rotation_matrix(self.phi, -phi)  #
        x = np.dot(Rp, np.dot(Rk, x)) / np.linalg.norm(
            x
        )  # rotate backwards and normalize
        c = np.dot(self.phi["direction"], x)  # cosine to the phi axis
        if c < 0.0:  # change the direction if necessary
            c = -c
            x = -x
        d = (c - self.cos2a) / (1.0 - self.cos2a)
        if abs(d) > 1.0:
            new_kappa = 180.0
        else:
            new_kappa = math.acos(d) * 180.0 / np.pi
        Rk = self.rotation_matrix(self.kappa, new_kappa)
        pp = np.dot(
            Rk, self.phi["direction"]
        )  # project on plane normal to phi at new_kappa
        xp = np.dot(Rk, x)
        d1 = self.align_direction - c * pp
        d2 = xp - c * pp
        nd1 = np.linalg.norm(d1)
        nd2 = np.linalg.norm(d2)
        if nd1 * nd2 <= 0.0000000001:
            new_phi = phi
        else:
            new_phi = (
                math.acos(np.dot(d1, d2) / nd1 / nd2) * 180.0 / np.pi
            )  # is the angle between projections
        newaxis = {}
        newaxis["mT"] = np.outer(pp, pp)
        newaxis["mC"] = np.array(
            [[0.0, -pp[2], pp[1]], [pp[2], 0.0, -pp[0]], [-pp[1], pp[0], 0.0]]
        )
        Rp = self.rotation_matrix(newaxis, new_phi)
        d = abs(np.dot(self.align_direction, np.dot(Rp, xp)))
        if (
            abs(np.dot(self.align_direction, np.dot(xp, Rp))) > d
        ):  # choose the correct direction of rotation
            new_phi = -new_phi

        return (
            new_kappa,
            new_phi,
            self.shift(
                kappa, phi, 0.5 * (np.array(t1) + np.array(t2)), new_kappa, new_phi
            ),
        )
