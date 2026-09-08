# ruff: noqa: TD003, FIX002, ERA001
try:
    # duo is a part of sdm package that lives at MaxIV private repository
    from duo.UO import RestDuo
    from sdm.config import DUOPASSWORD, DUOUSER
except ImportError:
    RestDuo = None
    DUOPASSWORD = None
    DUOUSER = None

from mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter import PyISPyBDataAdapter
from mxcubecore.model.lims_session import Proposal, Session

DUO_API_URL = "https://duo-api.maxiv.lu.se"
LAZY_SESSION_PREFIX = "lazy"


class MAXIVPyISPyBDataAdapter(PyISPyBDataAdapter):
    """Extend the standard ISPyB data adapter with MAXIV specific logic."""

    def __init__(self, duo_api_url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duo_api_url = duo_api_url

    def get_proposals(self):
        """Override method to filter proposals by the type, state and beamline name.

        Include proposals: of type ``MX`` or ``MB`` in ``Open`` state and assigned
        to the current beamline. The last is checked via DUO API.
        """
        duo = RestDuo(self.duo_api_url)
        duo.login(DUOUSER, DUOPASSWORD)
        beamline_proposals_ids = set(duo.get_beamline_proposals(self.beamline_name))
        return [
            self._PyISPyBDataAdapter__to_proposal(proposal)
            for proposal in self.client.get("proposals")
            if proposal.get("proposalCode").upper() in ["MX", "MB"]
            and proposal.get("state", "").capitalize() == "Open"
            and int(proposal.get("proposalNumber")) in beamline_proposals_ids
        ]

    def create_session(self, proposal: Proposal) -> Session:
        """Create a new Session object for the given proposal and beamline.

        This is a lazy session creation, done automatically on the fly in case
        no appropriate session is found for the user, proposal and current day.
        This session is labelled with ``lazy`` prefix and is not posted to
        Py-ISPYB service until it is selected.

        Args:
            proposal: Proposal object to create session for

        Returns:
            Session: Created session object
        """
        return Session(
            code=proposal.code,
            number=proposal.number,
            proposal_name=proposal.code + proposal.number,
            proposal_id=proposal.proposal_id,
            session_id=f"{LAZY_SESSION_PREFIX}{proposal.proposal_id}",
            beamline_name=self.beamline_name,
            title=proposal.title,
            # At MAXIV we don't care if a session is scheduled, set True as default
            is_scheduled_time=True,
            is_scheduled_beamline=True,
            # TODO@dominikatrojanowska: check if we should set start and end time
            #  for the session created on fly, and if so, what time should be set.
            #  For now, we just set empty string, and let ISPyB handle it.
            # "startDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            # "endDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
