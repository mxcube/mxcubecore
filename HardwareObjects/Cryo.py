import TacoDevice

CRYO_STATUS = ["OFF", "SATURATED", "READY", "WARNING", "FROZEN", "UNKNOWN"]


class Cryo(TacoDevice.TacoDevice):
    def __init__(self, *args, **kwargs):
        TacoDevice.TacoDevice.__init__(self, *args, **kwargs)

        self.n2level = None
        self.temp = None
        self.temp_error = None
        self.cryo_status = None
        self.dry_status = None
        self.sdry_status = None

    def init(self):
        if self.device.imported:
            self.setPollCommand("DevRead")

            self.setIsReady(True)

    def valueChanged(self, deviceName, values):
        n2level = values[0]
        temp = float(values[1])
        temp_error = values[2]
        cryo_status = int(values[3])
        temp_evap = values[4]
        gas_heater = values[5]
        dry_status = int(values[6])
        sdry_status = int(values[7])
        minlevel = values[8]
        maxlevel = values[9]
        version = values[10]

        if n2level != self.n2level:
            self.n2level = n2level
            self.emit("levelChanged", (n2level,))
        if temp != self.temp or temp_error != self.temp_error:
            self.temp = temp
            self.temp_error = temp_error
            self.emit("temperatureChanged", (temp, temp_error))
        if cryo_status != self.cryo_status:
            self.cryo_status = cryo_status
            self.emit("cryoStatusChanged", (CRYO_STATUS[cryo_status],))
        if dry_status != self.dry_status:
            self.dry_status = dry_status
            if dry_status != 9999:
                self.emit("dryStatusChanged", (CRYO_STATUS[dry_status],))
        if sdry_status != self.sdry_status:
            self.sdry_status = sdry_status
            if sdry_status != 9999:
                self.emit("sdryStatusChanged", (CRYO_STATUS[sdry_status],))

    def setN2Level(self, newLevel):
        if self.device and self.device.imported:
            self.device.DevSetLevel(newLevel)

    def getTemperature(self):
        return self.temp
