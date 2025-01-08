from itertools import product

import pytest

from rucio.client.didclient import DIDClient
from rucio.client.uploadclient import UploadClient

TEST_RSE = "STORAGE-1"


@pytest.mark.usefixtures("voms_proxy")
def test_add_metadata(test_scope, tmp_path):
    """Test adding/getting metadata works"""
    name = "file_with_metadata"
    lfn = f"/testvo/{test_scope}/name"
    path = tmp_path / name
    path.write_text("Hello, World!")

    upload_client = UploadClient()
    upload_spec = {
        "path": path,
        "rse": TEST_RSE,
        "did_scope": test_scope,
        "did_name": lfn,
    }
    # 0 = success
    assert upload_client.upload([upload_spec]) == 0

    did_client = DIDClient()
    meta = {
        "obs_id": 200000001,
        "tel_id": 1,
        "category": "A",
        "format": "zfits",
        "data_levels": ["DL0", "DL1"],
        "data_type": "event",
    }
    did_client.set_metadata_bulk(scope=test_scope, name=lfn, meta=meta)

    # default for plugin is "DIDColumn", which only includes the internal rucio metadata
    result = did_client.get_metadata(scope=test_scope, name=lfn, plugin="ALL")

    # check all our metadata was received correctly
    for key, value in meta.items():
        assert key in result, f"Key {key} missing in retrieved metadata"
        assert (
            result[key] == value
        ), f"Key {key} has wrong value, expected {value}, got {result[key]}"


@pytest.fixture()
def _metadata_test_dids(tmp_path, test_scope):
    """Setup a set of example files to test querying by metadata"""
    upload_client = UploadClient()
    did_client = DIDClient()

    def add_file(obs_id, tel_id, data_type):
        name = f"data_obs{obs_id}_tel{tel_id:03d}.{data_type}.txt"
        lfn = f"/testvo/{test_scope}/{name}"
        path = tmp_path / name
        path.write_text(name)

        spec = {
            "did_scope": test_scope,
            "did_name": lfn,
            "path": path,
            "rse": TEST_RSE,
        }
        upload_client.upload([spec])
        meta = {"obs_id": obs_id, "tel_id": tel_id, "data_type": data_type}
        did_client.set_metadata_bulk(test_scope, lfn, meta=meta)

    obs_ids = (200000001, 200000002, 200000003)
    tel_ids = (1, 2, 3, 4)
    data_types = ("event", "monitoring", "service")

    for obs_id, tel_id, data_type in product(obs_ids, tel_ids, data_types):
        add_file(obs_id, tel_id, data_type)


@pytest.mark.usefixtures("voms_proxy", "_metadata_test_dids")
def test_query_by_metadata(test_scope):
    """Test querying dids by metadata attributes"""

    did_client = DIDClient()

    # query for by one attribute, should return len(tel_ids) * len(data_types) files
    obs_id = 200000002
    dids = list(
        did_client.list_dids(test_scope, filters={"obs_id": obs_id}, did_type="file")
    )
    assert len(dids) == 12
    assert all(str(obs_id) in did for did in dids)

    # query for by two attributes
    obs_id = 200000002
    data_type = "event"
    query = {"obs_id": obs_id, "data_type": data_type}
    dids = list(did_client.list_dids(test_scope, filters=query, did_type="file"))
    assert len(dids) == 4
    assert all(str(obs_id) in did and data_type in did for did in dids)

    # query using comparison operator
    # should only return entries for obs_id > 200000002, so only for 200000003
    obs_id = 200000002
    expected_obs_id = 200000003
    query = {"obs_id.gt": obs_id, "data_type": data_type}
    dids = list(did_client.list_dids(test_scope, filters=query, did_type="file"))
    assert len(dids) == 4
    assert all(str(expected_obs_id) in did and data_type in did for did in dids)
