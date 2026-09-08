import os
import time

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.Session import Session


class LNLSSession(Session):
    def get_proposal(self):
        proposal = super().get_proposal()
        return proposal.replace("sc", "").replace("rap", "").replace("industrial", "")

    def get_base_image_directory(self):
        start_time = time.strftime("%Y%m%d")
        proposal = self.get_proposal()
        directory = os.path.join(
            self.base_directory,
            proposal,
            "data",
            start_time,
        )
        return directory

    def clear_session(self):
        HWR.beamline.session.session_id = None
        HWR.beamline.session.proposal_number = None
        HWR.beamline.session.proposal_code = None
        HWR.beamline.session.proposal_id = None
