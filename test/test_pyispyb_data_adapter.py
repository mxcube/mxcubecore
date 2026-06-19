from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter import PyISPyBDataAdapter
from mxcubecore.HardwareObjects.abstract.PyISPyBRestClient import (
    PyISPyBRestClient,
    PyISPyBUnsuccessfulResponse,
)
from mxcubecore.model.lims_session import Session
from test.factories.pyispyb_factory import (
    current_user_response,
    default_bl_config,
    default_bl_sample,
    default_data_collection,
    default_detector,
    default_energy_scan,
    default_image_dict,
    default_proposal,
    default_session,
    default_xfe_spectrum,
    proposals_response,
    sample_response,
    session_response,
)


@pytest.fixture
def client():
    return Mock(spec=PyISPyBRestClient)


@pytest.fixture
def adapter(client):
    adapter = PyISPyBDataAdapter(client=client, beamline_name="PROXIMA1")
    adapter.logger = Mock()
    return adapter


def test_get_current_user_data(adapter, client):
    client.get.return_value = current_user_response()

    currrent_user = adapter.get_current_user_data()

    client.get.assert_called_once_with("user/current")
    assert currrent_user["login"] == "testusr"
    assert currrent_user["givenName"] == "Admin"
    assert currrent_user["personId"] == 123456


def test_get_proposals(adapter, client):
    client.get.return_value = proposals_response()

    proposals = adapter.get_proposals()

    client.get.assert_called_once_with("proposals")
    assert len(proposals) == 2
    assert proposals[0].proposal_id == "10"
    assert proposals[1].proposal_id == "11"


def test_find_proposal(adapter, client):
    client.get.return_value = proposals_response()

    proposal = adapter.find_proposal("mx", "20090662")

    client.get.assert_called_once_with("proposals?search=mx20090662")
    assert proposal.proposal_id == "10"
    assert proposal.code == "MX"
    assert proposal.number == "20090662"


def test_get_sessions_by_code_and_number(
    adapter,
    client,
):
    client.get.return_value = [
        session_response(
            session_id=1,
            proposal="mx20090662",
            proposal_id=10,
        ),
        session_response(
            session_id=2,
            proposal="mx20090662",
            proposal_id=10,
        ),
    ]

    result = adapter.get_sessions_by_code_and_number(
        code="mx",
        number="20090662",
        beamline="PROXIMA1",
    )

    client.get.assert_called_once_with(
        "sessions?proposal=mx20090662&beamLineName=PROXIMA1"
    )
    assert len(result.sessions) == 2
    session_1 = result.sessions[0]
    assert session_1.session_id == "1"
    assert session_1.proposal_id == "10"
    assert session_1.proposal_name == "mx20090662"
    session_2 = result.sessions[1]
    assert session_2.session_id == "2"
    assert session_2.proposal_name == "mx20090662"


def test_find_sessions_by_proposal_and_beamline_for_today(
    adapter,
    client,
):
    client.get.return_value = [
        session_response(session_id=1),
        session_response(session_id=2),
    ]
    frozen_now = datetime(2026, 6, 2, 14, 30, 45)

    with (
        patch(
            "mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter.datetime"
        ) as mock_datetime,
        patch.object(
            adapter,
            "_PyISPyBDataAdapter__is_time_between",
            side_effect=[True, True, False],
        ),
    ):
        mock_datetime.today.return_value = frozen_now

        result = adapter.find_sessions_by_proposal_and_beamline_for_today(
            code="mx",
            number="20090662",
            beamline="PROXIMA1",
        )

    client.get.assert_called_once_with(
        f"sessions?proposal=mx20090662"
        f"&beamLineName=PROXIMA1"
        f"&year={frozen_now.year}"
        f"&month={frozen_now.month}"
        f"&day={frozen_now.day}"
    )
    assert len(result) == 1
    session = result[0]
    assert session.session_id == "1"
    assert session.proposal_id == "10"
    assert session.proposal_name == "mx20090662"
    assert session.code == "mx"
    assert session.number == "20090662"


def test_get_sessions_by_username_when_sessions_exist(
    adapter,
):
    proposal = MagicMock(code="mx", number="20090662")
    session = MagicMock(spec=Session)

    with (
        patch.object(adapter, "get_proposals", return_value=[proposal]),
        patch.object(
            adapter,
            "find_sessions_by_proposal_and_beamline_for_today",
            return_value=[session],
        ) as find_sessions_mock,
        patch.object(
            adapter,
            "create_session",
        ) as create_session_mock,
    ):
        result = adapter.get_sessions_by_username()

    assert len(result.sessions) == 1
    assert result.sessions[0] is session
    find_sessions_mock.assert_called_once_with(
        "mx",
        "20090662",
        adapter.beamline_name,
    )
    create_session_mock.assert_not_called()


def test_get_sessions_by_username_creates_session_when_none_exists(
    adapter,
):
    proposal = default_proposal()
    session = default_session()

    with (
        patch.object(adapter, "get_proposals", return_value=[proposal]),
        patch.object(
            adapter, "find_sessions_by_proposal_and_beamline_for_today", return_value=[]
        ),
        patch.object(
            adapter, "create_session", return_value=session
        ) as create_session_mock,
    ):
        result = adapter.get_sessions_by_username()

    create_session_mock.assert_called_once_with(proposal)
    assert len(result.sessions) == 1
    assert result.sessions[0] is session


def test_creat_session(
    adapter,
    client,
):
    proposal = default_proposal()
    frozen_now = datetime(2026, 6, 2, 14, 30, 45)

    with patch(
        "mxcubecore.HardwareObjects.abstract.PyISPyBDataAdapter.datetime"
    ) as mock_datetime:
        mock_datetime.today.return_value = frozen_now
        client.post.return_value = session_response()

        adapter.create_session(proposal)

    client.post.assert_called_once()

    start_time = frozen_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(
        days=adapter.new_session_duration_days, hours=7, minutes=59, seconds=59
    )
    (endpoint,) = client.post.call_args.args
    payload = client.post.call_args.kwargs["json"]

    assert endpoint == "sessions"
    assert payload["proposalId"] == "10"
    assert payload["beamLineName"] == adapter.beamline_name
    assert payload["startDate"] == start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    assert payload["endDate"] == end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    assert payload["scheduled"] is False


def test_store_image_success(
    adapter,
    client,
):
    image_dict = default_image_dict()
    client.post.return_value = {
        "imageId": 123,
        "dataCollectionId": 2,
    }

    response = adapter.store_image(image_dict=image_dict)

    client.post.assert_called_once_with(
        "images/image",
        json=image_dict,
    )
    assert response == 123


def test_store_image_returns_zero_when_post_fails(
    adapter,
    client,
):
    image_dict = default_image_dict()
    client.post.side_effect = PyISPyBUnsuccessfulResponse("""Exception raised when a
    response from the server is unsuccessful (not 200).""")

    image_id = adapter.store_image(image_dict)

    client.post.assert_called_once_with(
        "images/image",
        json=image_dict,
    )
    assert image_id == 0


def test_store_image_returns_zero_when_data_collection_id_missing(
    adapter,
    client,
):
    image_dict = {
        "imageNumber": 0,
        "fileName": "test.cbf",
    }

    image_id = adapter.store_image(image_dict)

    client.post.assert_not_called()
    assert image_id == 0


def test_get_samples(
    adapter,
    client,
):
    proposal = default_proposal()
    samples = sample_response()

    with (
        patch.object(
            adapter,
            "_PyISPyBDataAdapter__find_proposal_by_id",
            return_value=proposal,
        ) as find_proposal_mock,
        patch.object(
            client,
            "get",
            return_value=samples,
        ) as get_mock,
    ):
        result = adapter.get_samples(proposal.proposal_id)

    find_proposal_mock.assert_called_once_with(proposal.proposal_id)
    get_mock.assert_called_once_with(
        "samples?proposal=mx20090662&beamLineName=PROXIMA1",
        timeout=10,
    )
    assert result == samples


def test_get_samples_returns_empty_list_on_error(
    adapter,
):
    with patch.object(
        adapter,
        "_PyISPyBDataAdapter__find_proposal_by_id",
        side_effect=PyISPyBUnsuccessfulResponse("boom"),
    ):
        result = adapter.get_samples(10)

    assert result == []


def test_store_robot_action_missing_sample_id(adapter, client):
    robot_action = {
        "startTime": "2026-03-16T12:59:07.737Z",
        "endTime": "2026-04-16T14:00:07.737Z",
    }

    robot_action_id = adapter.store_robot_action(robot_action)

    assert robot_action_id == 0
    client.post.assert_not_called()


def test_store_robot_action_post_failure(adapter, client):
    client.post.side_effect = PyISPyBUnsuccessfulResponse(
        "Failed to store robot action"
    )
    adapter.logger.exception = Mock()
    robot_action = {
        "sampleId": 12,
        "startTime": "2026-03-16T12:59:07.737Z",
        "endTime": "2026-04-16T14:00:07.737Z",
    }
    robot_action_id = adapter.store_robot_action(robot_action)

    assert robot_action_id == 0

    client.post.assert_called_once_with(
        "events/robot-action",
        json={
            "blSampleId": 12,
            "startTimestamp": "2026-03-16T12:59:07.737Z",
            "endTimestamp": "2026-04-16T14:00:07.737Z",
        },
    )
    adapter.logger.exception.assert_called_once_with("Exception in store_robot_action")


def test_store_robot_action_sucess(
    adapter,
    client,
):
    client.post.return_value = 77
    robot_action = {
        "sampleId": 12,
        "startTime": "2025-01-01",
        "endTime": "2025-01-02",
    }

    robot_action_id = adapter.store_robot_action(robot_action)

    assert robot_action_id == 77
    client.post.assert_called_once_with(
        "events/robot-action",
        json={
            "blSampleId": 12,
            "startTimestamp": "2025-01-01",
            "endTimestamp": "2025-01-02",
        },
    )


def test_associate_bl_sample_and_energy_scan(
    adapter,
    client,
):
    entry_dict = {"energyScanId": 125, "blSampleId": 1}
    client.patch.return_value = entry_dict

    result = adapter.associate_bl_sample_and_energy_scan(entry_dict)

    assert result["energyScanId"] == 125
    client.patch.assert_called_once_with(
        "events/energyscan/associate-bl-sample",
        json={
            "energyScanId": 125,
            "blSampleId": 1,
        },
    )


def test_associate_bl_sample_and_energy_scan_failure(
    adapter,
    client,
):
    client.patch.side_effect = Exception("Patch failed")
    entry_dict = {"energyScanId": 125, "blSampleId": 1}

    result = adapter.associate_bl_sample_and_energy_scan(entry_dict)

    assert result == -1
    client.patch.assert_called_once_with(
        "events/energyscan/associate-bl-sample",
        json={
            "energyScanId": 125,
            "blSampleId": 1,
        },
    )
    adapter.logger.exception.assert_called_once_with(
        "Failed to associate bl sample and energy scan in PyISPyB"
    )


def test_get_data_collection(
    adapter,
    client,
):
    client.get.return_value = default_data_collection()

    result = adapter.get_data_collection(1)

    client.get.assert_called_once_with("datacollections/1")
    assert result == {
        "dataCollectionId": 1,
        "dataCollectionGroupId": 99,
        "strategySubWedgeOrigId": None,
        "detectorId": None,
        "blSubSampleId": None,
        "startPositionId": 9,
        "endPositionId": None,
        "dataCollectionNumber": 1,
        "startTime": "2015-01-20 16:17:13",
        "endTime": "2015-01-20 16:17:13",
        "runStatus": "failed",
        "sessionId": 123,
    }


def test_get_data_collection_exception(
    adapter,
    client,
):
    client.get.side_effect = Exception("Request failed")

    result = adapter.get_data_collection(1)

    assert result == {}
    client.get.assert_called_once_with("datacollections/1")
    adapter.logger.exception.assert_called_once_with(
        "Failed to get data collection from PyISPyB"
    )


def test_get_data_collection_empty_response(
    adapter,
    client,
):
    client.get.return_value = []

    result = adapter.get_data_collection(999999)

    assert result == {}
    client.get.assert_called_once_with("datacollections/999999")


def test_get_data_collection_with_string_dates(
    adapter,
    client,
):
    client.get.return_value = {
        "startTime": "2015-01-20T16:17:13",
        "endTime": "2015-01-20T16:17:13",
    }

    result = adapter.get_data_collection(1)

    assert result == {
        "startTime": "2015-01-20 16:17:13",
        "endTime": "2015-01-20 16:17:13",
    }


def test_find_detector(
    adapter,
    client,
):
    client.get.return_value = default_detector()

    result = adapter.find_detector(
        manufacturer="ExampleManufacturer",
        model="ExampleModel",
        mode="Standard",
        type="PixelDetector",
    )

    client.get.assert_called_once_with(
        "detectors?manufacturer=ExampleManufacturer"
        "&model=ExampleModel"
        "&mode=Standard"
        "&type=PixelDetector"
    )
    assert result["detectorId"] == 1


def test_find_detector_without_type(
    adapter,
    client,
):
    detector = {"detectorId": 1}
    client.get.return_value = detector

    result = adapter.find_detector(
        manufacturer="ExampleManufacturer",
        model="ExampleModel",
        mode="Standard",
    )

    client.get.assert_called_once_with(
        "detectors?manufacturer=ExampleManufacturer"
        "&model=ExampleModel"
        "&mode=Standard"
        "&type="
    )
    assert result == detector


def test_update_session_success(
    adapter,
    client,
):
    session = {
        "sessionId": 46369,
        "BeamLineSetup": {
            "beamLineSetupId": 2,
        },
    }
    client.patch.return_value = {"sessionId": 46369, "beamLineSetupId": 2}

    result = adapter.update_session(session)

    assert result["sessionId"] == 46369
    client.patch.assert_called_once_with(
        "sessions/46369/associate-beamline-setup?beamLineSetupId=2",
    )


def test_update_session_null_beamline_setup(
    adapter,
    client,
):
    session = {
        "sessionId": 46369,
        "BeamLineSetup": None,
    }

    result = adapter.update_session(session)

    assert result == {}
    client.post.assert_not_called()
    adapter.logger.exception.assert_called_once_with(
        "Failed to store or update session"
    )


def test_get_sesssion(
    adapter,
    client,
):
    client.get.return_value = session_response()

    result = adapter.get_session(1)

    assert result["sessionId"] == 1
    client.get.assert_called_once_with("sessions/1")


def test_store_beamline_setup_success(
    adapter,
    client,
):
    session_id = 1
    session = {
        "sessionId": 1,
        "BeamLineSetup": {
            "beamLineSetupId": 2,
        },
    }
    client.get.return_value = session
    bl_config = default_bl_config()
    client.post.return_value = 101
    adapter.update_session = Mock()

    result = adapter.store_beamline_setup(session_id, bl_config)

    assert result == 101
    client.post.assert_called_once_with(
        "beamline-setups/beamline-setup",
        json=bl_config,
    )
    adapter.update_session.assert_called_once_with(session)


def test_store_data_collection_without_bl_config(adapter, client):
    mx_collection = default_data_collection()
    client.post.return_value = {"dataCollectionId": 10, "dataCollectionGroupId": 99}

    result = adapter.store_data_collection(mx_collection)

    assert result == (10, 0)
    client.post.assert_called_once_with(
        "datacollections/datacollection",
        json=mx_collection,
    )


def test_store_data_collection_with_detector(adapter, client):
    mx_collection = default_data_collection()
    bl_config = default_bl_config()
    client.post.return_value = {"dataCollectionId": 10, "dataCollectionGroupId": 99}
    adapter.store_beamline_setup = Mock()
    adapter.find_detector = Mock(return_value={"detectorId": 42})

    result = adapter.store_data_collection(mx_collection, bl_config)

    assert result == (10, 42)
    adapter.store_beamline_setup.assert_called_once_with(
        123,
        bl_config,
    )
    adapter.find_detector.assert_called_once_with(
        "ExampleManufacturer",
        "ExampleModel",
        "1x1",
        "PixelDetector",
    )
    client.post.assert_called_once_with(
        "datacollections/datacollection",
        json={**mx_collection, "detectorId": 42},
    )
    assert (
        mx_collection["detectorId"] is None
    )  # ensures input data was not modified within store_data_collection method


def test_store_data_collection_without_detector(adapter, client):
    mx_collection = default_data_collection()
    bl_config = default_bl_config()
    client.post.return_value = {"dataCollectionId": 10, "dataCollectionGroupId": 99}
    adapter.store_beamline_setup = Mock()
    adapter.find_detector = Mock(return_value=None)

    result = adapter.store_data_collection(mx_collection, bl_config)

    assert result == (10, 0)
    client.post.assert_called_once_with(
        "datacollections/datacollection", json=mx_collection
    )
    assert mx_collection["detectorId"] is None


def test_update_data_collection_missing_collection_id(adapter, client):
    mx_collection = {
        "other_key": 1,
    }

    result = adapter._update_data_collection(mx_collection)

    assert result == (0, 0)
    client.post.assert_not_called()


def test_update_data_collection_sets_group_id(adapter, client):
    mx_collection = {
        "collection_id": 123,
    }
    client.post.return_value = (1, 2)
    adapter._store_data_collection_group = Mock(
        return_value={"dataCollectionGroupId": 777}
    )

    adapter._update_data_collection(mx_collection)

    assert mx_collection["group_id"] == 777


def test_update_data_collection_success(
    adapter,
    client,
):
    mx_collection = {
        "collection_id": 1,
    }

    client.post.return_value = (1, 99)
    adapter._store_data_collection_group = Mock(
        return_value={"dataCollectionGroupId": 99}
    )

    result = adapter._update_data_collection(mx_collection)

    assert result == (1, 99)
    adapter._store_data_collection_group.assert_called_once_with(mx_collection)
    client.post.assert_called_once_with(
        "datacollections/datacollection",
        json=mx_collection,
    )


def test_store_energy_scan_success(
    adapter,
    client,
):
    energyscan = default_energy_scan()
    client.post.return_value = 123

    result = adapter.store_energy_scan(energyscan)

    assert result == {"energyScanId": 123}
    client.post.assert_called_once_with("events/energyscan", json=energyscan)


def test_store_energy_scan_failure(adapter, client):
    energyscan = default_energy_scan()
    client.post.side_effect = PyISPyBUnsuccessfulResponse("error")

    result = adapter.store_energy_scan(energyscan)

    assert result == {"energyScanId": -1}
    adapter.logger.exception.assert_called_once_with(
        "Failed to store energy scan in PyISPyB"
    )


def test_store_xfe_spectrum_success(
    adapter,
    client,
):
    xfe_spectrum = default_xfe_spectrum()
    client.post.return_value = 123

    result = adapter.store_xfe_spectrum(xfe_spectrum)

    assert result == {"xfeFluorescenceSpectrumId": 123}
    client.post.assert_called_once_with(
        "events/xfe-fluorescence-spectrum", json=xfe_spectrum
    )


def test_store_xfe_spectrum_failure(
    adapter,
    client,
):
    xfe_spectrum = default_xfe_spectrum()
    client.post.side_effect = PyISPyBUnsuccessfulResponse("error")

    result = adapter.store_xfe_spectrum(xfe_spectrum)

    assert result == {"xfeFluorescenceSpectrumId": -1}
    adapter.logger.exception.assert_called_once_with(
        "Failed to store XFE fluorescence spectrum in PyISPyB"
    )


def test_update_bl_sample_success(adapter, client):
    bl_sample = default_bl_sample()
    expected_response = default_bl_sample()
    client.patch.return_value = expected_response

    result = adapter.update_bl_sample(bl_sample)

    assert result == expected_response
    client.patch.assert_called_once_with(
        "samples/1115",
        json=bl_sample,
    )


def test_update_bl_sample_missing_bl_sample_id(adapter, client):
    bl_sample = {
        "name": "sample1",
    }

    result = adapter.update_bl_sample(bl_sample)

    assert result == {}
    client.patch.assert_not_called()
    adapter.logger.error.assert_called_once_with("Missing blSampleId")


def test_update_bl_sample_patch_failure(adapter, client):
    bl_sample = default_bl_sample()
    client.patch.side_effect = PyISPyBUnsuccessfulResponse("Update failed")

    result = adapter.update_bl_sample(bl_sample)

    assert result == {}
    client.patch.assert_called_once_with(
        "samples/1115",
        json=bl_sample,
    )
    adapter.logger.exception.assert_called_once_with(
        "Failed to update beamline sample in PyISPyB"
    )
