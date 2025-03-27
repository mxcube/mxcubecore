from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic.v1 import (
    BaseModel,
    Field,
)


class Proposal(BaseModel):
    """Represents a proposal with key identifying details."""

    proposal_id: str = ""  # Unique identifier for the proposal
    person_id: str = ""  # Identifier of the person associated
    type: str = ""  # Type/category of the proposal (e.g., "MX")
    code: str = ""  # Specific code associated with the proposal e.g., "IH-LS"
    # Proposal number; may be sequential or unique (uniqueness may depend on
    # the combination of `code` and `number`)
    number: str = ""
    title: str = ""  # Title of the proposal


class Lims(BaseModel):
    """Represents a LIMS system"""

    name: str = ""  # Unique identifier for the LIMS (e.g: ispyb, icat, ...)
    description: str = ""  # Free text with a short description


class Session(BaseModel):
    """Represents a experiment in a specific time slot in a beamline
    for a proposal
    This class has been kept more or less as-it-is for legacy purposes
    because ISPyB rely on it
    """

    session_id: str = (
        ""  # Unique identifier for the experiment (it's dependent of the LIMS)
    )
    beamline_name: str = ""  # Beamline where the experiment is scheduled
    start_date: str = ""  # The official start date. Format: YYYYMDD
    start_time: str = ""
    end_date: str = ""  # The official end date. Format: YYYYMDD
    end_time: str = ""

    # Proposal information. It is kept for legacy purpose but it
    # should be replaced by the Proposal object
    title: str = ""
    code: str = ""
    number: str = ""
    proposal_id: str = ""
    proposal_name: str = ""

    comments: Optional[str] = ""

    start_datetime: datetime = Field(default_factory=datetime.now)
    end_datetime: Optional[datetime] = Field(
        default_factory=lambda: datetime.now() + timedelta(days=1)
    )

    # Actual start and end date is used when a session is "moved" in time.
    # Example: data is collected before or after it was originally scheduled
    actual_start_date: str = (
        ""  # Start date of a session that has been rescheduled time-wise
    )
    actual_start_time: str = ""
    actual_end_date: str = ""
    actual_end_time: str = ""

    nb_shifts: str = (
        ""  # Number of shifts allocated to a session.
        # A shift is typically 8 hours, though this may vary.
    )
    scheduled: str = (
        ""  # True if the session has been officialiy scheduled and approved
    )

    is_rescheduled: bool = (
        False  # if the session has been rescheduled in terms of time/beamline.
    )
    is_scheduled_beamline: bool = (
        False  # if the session is scheduled in the current beamline
    )
    is_scheduled_time: bool = False  # True if the session is currently active

    # direct links to different services
    user_portal_URL: Optional[str] = None  # Link to the session page in the UP
    data_portal_URL: Optional[str] = (
        None  # Link to the session page in the data portal or lims
    )
    logbook_URL: Optional[str] = (
        None  # Link to the session page in the electronic logbook
    )

    volume: Optional[str] = None  # Volume (bytes) of data produced
    dataset_count: Optional[str] = None  # Number of datasets collected
    sample_count: Optional[str] = None  # Number of samples collected


class Instrument(BaseModel):
    """This class represents a beamline"""

    name: str
    id: int
    instrumentScientists: List[Any]


class Investigation(BaseModel):
    """This class represents a investigation and is a proposal
    to replace the session class"""

    name: str
    startDate: datetime
    endDate: datetime
    id: int
    title: str
    visitId: str
    summary: str
    parameters: Dict[str, Any]
    instrument: Instrument
    investigationUsers: List[Any]


class Parameter(BaseModel):
    """Generic reprentation of a parameter atached to any entity like
    investigation, sample, dataset."""

    name: str  # name of the parameter
    value: str  # its value
    id: int  # identifier of the parameter
    units: str  # units if any


class MetaPage(BaseModel):
    totalWithoutFilters: int
    total: int
    totalPages: int
    currentPage: int


class Meta(BaseModel):
    page: MetaPage


class LimsUser(BaseModel):
    """Represents and users that is connected to MXCuBE"""

    user_name: str = ""  # identifier of the users, most likely login name
    sessions: Optional[
        List[Session]
    ] = []  # The sessions that the user is allowed to collect data from.


class LimsSessionManager(BaseModel):
    active_session: Optional[Session] = None  # the current active sessions
    sessions: Optional[
        List[Session]
    ] = []  # Selectable sessions that are calculated based on the connected users
    users: Optional[
        Dict[str, LimsUser]
    ] = {}  # the list of users that are currently connected


class SampleSheet(BaseModel):
    """Represents a description of the sample sheet as defined on
    some user portals"""

    id: int
    name: str  # Name of the samplesheet that use to correspond to the protein's name
    investigation: Investigation
    modTime: datetime
    parameters: List[
        Parameter
    ]  # Generic list of parameters that will depend on the user portal
    datasets: List[Any]  # datasets collected for this sample
    meta: Meta  # pagination parameters
