from datetime import datetime, timedelta

from mxcubecore.model.lims_session import Proposal, Session


def current_user_response():
    return {
        "givenName": "Admin",
        "familyName": "Test_User",
        "login": "testusr",
        "Permissions": [
            "all_proposals",
            "all_sessions",
            "own_proposals",
            "own_sessions",
        ],
        "personId": 123456,
        "beamLineGroups": [],
        "beamLines": [],
    }


def proposal_response(
    proposal_id: 10,
    proposal_code: str = "MX",
    proposal_number: str = "20090662",
):
    return {
        "proposalCode": proposal_code,
        "proposalNumber": proposal_number,
        "proposal": f"{proposal_code.lower()}{proposal_number}",
        "title": "Test Proposal",
        "state": "open",
        "proposalType": "MX",
        "proposalId": proposal_id,
    }


def proposals_response():
    return [
        proposal_response(
            proposal_id=10,
            proposal_code="mx",
            proposal_number="20090662",
        ),
        proposal_response(
            proposal_id=11,
            proposal_code="mx",
            proposal_number="20210662",
        ),
    ]


def session_response(
    session_id=1,
    proposal="mx20090662",
    proposal_id=10,
):
    start_date = datetime.today()
    end_date = start_date + timedelta(1)
    return {
        "proposalId": proposal_id,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "beamLineName": "PROXIMA1",
        "sessionId": session_id,
        "proposal": proposal,
        "BeamLineSetup": {
            "synchrotronMode": "string",
            "beamLineSetupId": 1,
        },
    }


def default_proposal():
    return Proposal(
        proposal_id="10",
        person_id="123456",
        code="mx",
        number="20090662",
        title="test proposal",
    )


def default_session():
    return Session(
        session_id="1",
        proposal_id="10",
        proposal_name="mx20090662",
        code="mx",
        number="20090662",
    )


def default_image_dict():
    return {
        "dataCollectionId": 2,
        "imageNumber": 0,
        "fileName": "test.cbf",
        "fileLocation": "/data/test",
    }


def sample_response():
    return [
        {
            "name": "sample-01",
            "code": "smpl-01",
            "blSampleId": 1,
            "location": 1,
            "Container": {
                "code": "CONTAINER-01",
                "sampleChangerLocation": "1",
            },
            "Crystal": {
                "Protein": {
                    "acronym": "TEST",
                },
                "crystalId": 12345,
                "space_group": None,
                "cell_a": 0.0,
                "cell_alpha": 0.0,
                "cell_b": 0.0,
                "cell_beta": 0.0,
                "cell_c": 0.0,
                "cell_gamma": 0.0,
            },
            "DiffractionPlan": {
                "diffractionPlanId": 23456,
            },
        }
    ]


def default_data_collection():
    return {
        "dataCollectionId": 1,
        "dataCollectionGroupId": 99,
        "strategySubWedgeOrigId": None,
        "detectorId": None,
        "blSubSampleId": None,
        "startPositionId": 9,
        "endPositionId": None,
        "dataCollectionNumber": 1,
        "startTime": "2015-01-20T16:17:13",
        "endTime": "2015-01-20T16:17:13",
        "runStatus": "failed",
        "sessionId": 123,
    }


def default_detector():
    return {
        "detectorId": 1,
        "detectorType": "PixelDetector",
        "detectorManufacturer": "ExampleManufacturer",
        "detectorModel": "ExampleModel",
        "detectorPixelSizeHorizontal": 0.075,
    }


def default_bl_config():
    return {
        "detector_manufacturer": "ExampleManufacturer",
        "detector_model": "ExampleModel",
        "detector_binning_mode": "1x1",
        "detector_type": "PixelDetector",
    }


def default_energy_scan():
    return {
        "fluorescenceDetector": "Pilatus",
        "scanFileFullPath": "/data/scan1.dat",
        "choochFileFullPath": "/data/chooch1.dat",
        "jpegChoochFileFullPath": "/data/chooch1.jpg",
    }


def default_xfe_spectrum():
    return {
        "sessionId": 44692,
        "blSampleId": 299,
        "fittedDataFileFullPath": "string",
        "scanFileFullPath": "string",
        "jpegScanFileFullPath": "string",
    }


def default_bl_sample():
    return {"blSampleId": 1115, "name": "abcf-28", "code": ""}
