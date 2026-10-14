import json

import pytest

pytest.importorskip("pyicat_plus")

from pyicat_plus.client import models as icat_models  # noqa: E402

from mxcubecore.HardwareObjects.ICATLIMS import (  # noqa: E402
    ICATLIMS,
    _to_metadata_dict,
)


@pytest.fixture
def params():
    params = icat_models.IcatDatasetParameters.blank()
    params.title = "dataset"
    params.proposal = "mx1234"
    params.folder_path = "/data/mx1234/dataset"
    params.start_time = "2026-10-13T10:00:00+02:00"
    params.end_time = "2026-10-13T10:05:00+02:00"
    params.sample.name = "sample1"
    params.complete = True
    params.MX.numberOfImages = 3600
    params.MX.transmission = 12.5
    params.MX.scanType = "datacollection"
    return params


def test_metadata_dict_keeps_native_types(params):
    metadata = _to_metadata_dict(params, {})

    assert metadata["complete"] is True
    assert metadata["MX_numberOfImages"] == 3600
    assert isinstance(metadata["MX_numberOfImages"], int)
    assert metadata["MX_transmission"] == 12.5
    assert isinstance(metadata["MX_transmission"], float)
    assert metadata["MX_scanType"] == "datacollection"


def test_metadata_dict_has_same_keys_as_icat_dict(params):
    metadata = _to_metadata_dict(params, {})

    assert metadata.keys() == params.finalize().to_icat_dict().keys()


def test_metadata_dict_merges_extra(params):
    extra = {"InstrumentCryostat01_value": "room temperature", "MX_transmission": 50}

    metadata = _to_metadata_dict(params, extra)

    assert metadata["InstrumentCryostat01_value"] == "room temperature"
    assert metadata["MX_transmission"] == 50


def test_metadata_dict_serializes_to_same_icat_strings(params):
    # store_dataset() rebuilds the model from the dict it receives and
    # stringifies it before sending: the typed dict must end up identical
    # to what to_icat_dict() used to send.
    metadata = _to_metadata_dict(params, {})

    model, unknown_keys = icat_models.IcatDatasetParameters.from_icat_dict_known_keys(
        metadata
    )

    assert unknown_keys == []
    assert model.to_icat_dict() == params.finalize().to_icat_dict()


def test_write_metadata_json_keeps_native_types(params, tmp_path):
    gathered = {
        "directory": tmp_path,
        "file_metadata": _to_metadata_dict(params, {}),
        "snapshot_paths": [],
    }

    ICATLIMS.__new__(ICATLIMS)._write_metadata(gathered)

    written = json.loads((tmp_path / "metadata.json").read_text())
    assert written["complete"] is True
    assert written["MX_numberOfImages"] == 3600
    assert written["MX_transmission"] == 12.5
