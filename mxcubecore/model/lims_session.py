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
    """Proposal with key identifying details.

    Parameters:
        proposal_id: Unique identifier for the proposal.
        person_id: Identifier of the person associated.
        type: Type/category of the proposal (e.g., "MX").
        code: Specific code associated with the proposal e.g., "IH-LS".
        number: Proposal number; may be sequential or unique
            (uniqueness may depend on the combination of code and number)
        title:  Title of the proposal
    """

    proposal_id: str = ""
    person_id: str = ""
    type: str = ""
    code: str = ""
    number: str = ""
    title: str = ""


class Lims(BaseModel):
    """Represents a LIMS system.

    Parameters:
        name: Unique identifier for the LIMS (e.g., "ispyb", "icat").
        description: Free text providing a short description of the LIMS.
    """

    name: str = ""
    description: str = ""


class Session(BaseModel):
    """Represents an experiment in a specific time slot on a beamline for a proposal.

    This class is maintained for legacy purposes because ISPyB relies on it.

    Parameters:
        session_id: Unique identifier for the experiment, dependent on the LIMS.
        beamline_name: Name of the beamline where the experiment is scheduled.
        start_date: Official start date (format: YYYYMMDD).
        start_time: Official start time.
        end_date: Official end date (format: YYYYMMDD).
        end_time: Official end time.
        title: Title of the proposal associated with the session.
        code: Code associated with the proposal.
        number: Proposal number.
        proposal_id: Unique identifier of the proposal.
        proposal_name: Name of the proposal.
        comments: Optional comments about the session.
        start_datetime: Start datetime of the session.
        end_datetime: End datetime of the session
        actual_start_date: Start date if the session was rescheduled.
        actual_start_time: Start time if the session was rescheduled.
        actual_end_date: End date if the session was rescheduled.
        actual_end_time: End time if the session was rescheduled.
        nb_shifts: Number of shifts allocated to the session (typically 8h)
        scheduled: if the session is officially scheduled and approved.
        is_rescheduled: if the session was rescheduled in time or beamline.
        is_scheduled_beamline: if the session is scheduled on the current bm
        is_scheduled_time: if the session is currently active.
        user_portal_URL: Optional link to the session page in the User Portal.
        data_portal_URL: link to the data portal or LIMS.
        logbook_URL: Optional link to the session page in the  logbook.
        volume: Optional volume (in bytes) of data produced.
        dataset_count: Optional number of datasets collected.
        sample_count: Optional number of samples collected.
    """

    session_id: str = ""
    beamline_name: str = ""
    start_date: str = ""
    start_time: str = ""
    end_date: str = ""
    end_time: str = ""
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
    actual_start_date: str = ""
    actual_start_time: str = ""
    actual_end_date: str = ""
    actual_end_time: str = ""
    nb_shifts: str = ""
    scheduled: str = ""
    is_rescheduled: bool = False
    is_scheduled_beamline: bool = False
    is_scheduled_time: bool = False
    user_portal_URL: Optional[str] = None
    data_portal_URL: Optional[str] = None
    logbook_URL: Optional[str] = None
    volume: Optional[str] = None
    dataset_count: Optional[str] = None
    sample_count: Optional[str] = None


class Instrument(BaseModel):
    """Represents a beamline.

    Parameters:
        name: Name of the beamline.
        id: Unique identifier of the beamline.
        instrumentScientists: List of scientists associated with the instrument.
    """

    name: str
    id: int
    instrumentScientists: List[Any]


class Investigation(BaseModel):
    """Represents an investigation and serves as a proposal to replace
    the Session class.

    Parameters:
        name: Name of the investigation.
        startDate: Start date of the investigation.
        endDate: End date of the investigation.
        id: Unique identifier of the investigation.
        title: Title of the investigation.
        visitId: Identifier for the visit associated with the investigation.
        summary: Summary description of the investigation.
        parameters: Dictionary of investigation-specific parameters.
        instrument: Associated instrument for the investigation.
        investigationUsers: List of users involved in the investigation.
    """

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
    """Represents a generic parameter attached to entities like investigations,
    samples, or datasets.

    Parameters:
        name: Name of the parameter.
        value: Value assigned to the parameter.
        id: Unique identifier of the parameter.
        units: Measurement units, if applicable.
    """

    name: str
    value: str
    id: int
    units: str


class MetaPage(BaseModel):
    """Pagination metadata.

    Parameters:
        totalWithoutFilters: Total count of items without filters applied.
        total: Total count of items with filters applied.
        totalPages: Total number of pages available.
        currentPage: Current page number.
    """

    totalWithoutFilters: int
    total: int
    totalPages: int
    currentPage: int


class Meta(BaseModel):
    """Metadata containing pagination details.

    Parameters:
        page: Pagination details.
    """

    page: MetaPage


class LimsUser(BaseModel):
    """Represents a user connected to MXCuBE.

    Parameters:
        user_name: Identifier for the user, typically their login name.
        sessions: List of sessions the user is allowed to collect data from.
    """

    user_name: str = ""
    sessions: Optional[List[Session]] = []


class LimsSessionManager(BaseModel):
    """Manages LIMS sessions and connected users.

    Parameters:
        active_session: The current active session, if any.
        sessions: List of selectable sessions determined based on connected users.
        users: Dictionary of currently connected users.
    """

    active_session: Optional[Session] = None
    sessions: Optional[List[Session]] = []
    users: Optional[Dict[str, LimsUser]] = {}


class SampleSheet(BaseModel):
    """Represents a description of a sample sheet as defined in user portals.

    Parameters:
        id: Unique identifier for the sample sheet.
        name: Name of the sample sheet, often corresponding to the protein's name.
        investigation: Investigation associated with the sample sheet.
        modTime: Last modification time of the sample sheet.
        parameters: Generic list of parameters, dependent on the user portal.
        datasets: List of datasets collected for this sample.
        meta: Pagination metadata.
    """

    id: int
    name: str
    investigation: Investigation
    modTime: datetime
    parameters: List[Parameter]
    datasets: List[Any]
    meta: Meta
