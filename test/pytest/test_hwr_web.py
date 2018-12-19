from HardwareRepository.HardwareRepository import getHardwareRepository
def test_hwr_qt(hwr_web):
    hwr = getHardwareRepository(hwr_web)
    hwr.connect()

    blsetup_hwobj = hwr.getHardwareObject("beamline-setup")
