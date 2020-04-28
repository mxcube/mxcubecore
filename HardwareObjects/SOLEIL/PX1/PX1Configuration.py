import os

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository.BaseHardwareObjects import Device


class PX1Configuration(Device):
    def init(self):
        self.use_edna_value = self.getProperty("use_edna")
        self.pin_length = self.getProperty("pin_length")

        self.centring_points = self.getProperty("centring_points")
        self.centring_phi_incr = self.getProperty("centring_phi_increment")
        self.centring_sample_type = self.getProperty("centring_sample_type")

        print("LocalConfiguration has value sample_type=%s" % self.centring_sample_type)

    def getUseEDNA(self):
        return self.use_edna_value

    def setUseEDNA(self, value):
        if value is True or value == "True":
            self.use_edna_value = True
            self.setProperty("use_edna", True)
        else:
            self.use_edna_value = False
        self.setProperty("use_edna", self.use_edna_value)

    def getPinLength(self):
        return self.pin_length

    def setPinLength(self, value):
        self.pin_length = value
        self.setProperty("pin_length", value)

    def getCentringPoints(self):
        return int(self.centring_points)

    def setCentringPoints(self, value):
        self.centring_points = int(value)
        self.setProperty("centring_points", value)

    def getCentringPhiIncrement(self):
        return float(self.centring_phi_incr)

    def setCentringPhiIncrement(self, value):
        self.centring_phi_incr = float(value)
        self.setProperty("centring_phi_increment", value)

    def getCentringSampleType(self):
        return self.centring_sample_type

    def setCentringSampleType(self, value):
        self.centring_sample_type = value
        self.setProperty("centring_sample_type", value)

    def save(self):
        self.commit_changes()


if __name__ == "__main__":
    hwr = HWR.getHardwareRepository()
    hwr.connect()

    env = hwr.getHardwareObject("/px1configuration")

    print("PX1 Configuration ")
    use_edna = env.getUseEDNA()
    print("    use_edna %s / (type: %s)" % (use_edna, type(use_edna)))
    print("    pin_length", env.getPinLength())
    print("    centring")
    print("       nb points", env.getCentringPoints())
    print("       phi incr", env.getCentringPhiIncrement())
    print("       sample type", env.getCentringSampleType())
    env.setUseEDNA("False")
    env.setPinLength("10")
    print("    use_edna %s " % env.getUseEDNA())
    print("    pin_length", env.getPinLength())
    # env.save()
