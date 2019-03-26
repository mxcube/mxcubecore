from HardwareRepository.HardwareObjects.MD2Motor import MD2Motor


class MicrodiffHolderlength(MD2Motor):
    def __init__(self, *args):
        MD2Motor.__init__(self, *args)

    def init(self):
        MD2Motor.init(self)
        offset_chan = self.addChannel(
            {"type": "exporter", "name": "offset"}, "SampleHolderLength"
        )
        # self.offset_chan.connectSignal("update", self.offsetChanged)
        self.offset = offset_chan.getValue()

    def offsetChanged(self, new_offset):
        self.offset = new_offset

    def motorPositionChanged(self, absolutePosition, private={}):
        MD2Motor.motorPositionChanged(self, self.offset - absolutePosition)

    def getPosition(self):
        return self.offset - self.position_attr.getValue()

    def getLimits(self):
        low_lim, hi_lim = MD2Motor.getLimits(self)
        return ((low_lim + self.offset), (hi_lim + self.offset))

    def move(self, absolutePosition):
        MD2Motor.move(self, self.offset - absolutePosition)
