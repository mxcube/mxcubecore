import sys
from HardwareRepository import QtImport

print(QtImport)
from HardwareRepository.HardwareRepository import getHardwareRepository

def test_hwr_qt(hwr_qt):
    app = QtImport.QApplication([])

    hwr = getHardwareRepository(hwr_qt)
    hwr.connect()

    blsetup_hwobj = hwr.getHardwareObject("beamline-setup")
    role_list = ("transmission", "diffractometer", "omega_axis", "kappa_axis",
                 "kappa_phi_axis", "sample_changer", "plate_manipulator",
                 "resolution", "energy", "flux", "beam_info", "shape_history",
                 "session", "lims_client", "data_analysis", "energyscan",
                 "collect", "parallel_processing", "xrf_spectrum", "detector")
    for role in role_list:
        assert hasattr(blsetup_hwobj, "%s_hwobj" % role)
