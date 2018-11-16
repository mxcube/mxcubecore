import SpecScan


class Dscan(SpecScan.SpecScan):
    def __init__(self, *args):
        SpecScan.SpecScan.__init__(self, *args)

    def GUI(self, parent, equipmentMnemonic):
        from BlissFramework.Bricks import GenericScanBrick

        gui = GenericScanBrick.GenericScanBrick(parent)
        gui.setProcedure(self)
        gui.setEquipmentMnemonic(equipmentMnemonic)

        return gui

    def isAbsolute(self):
        return False
