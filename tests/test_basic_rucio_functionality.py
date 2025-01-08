import getpass
import shutil
import time

import pytest

from rucio.client import Client
from rucio.client.client import ReplicaClient, RuleClient
from rucio.client.didclient import DIDClient
from rucio.client.uploadclient import UploadClient

pytestmark = [
    pytest.mark.rucio_clients,
    pytest.mark.bdms,
]


def test_server_version():
    """Test the expected version of rucio is running"""
    client = Client()
    result = client.ping()
    assert result["version"].startswith("36")


def remove_tokens():
    """Remove current auth tokens to 'logout'"""
    username = getpass.getuser()
    token_path = f"/tmp/{username}/.rucio_{username}"
    shutil.rmtree(token_path, ignore_errors=True)


def test_default_authentication(rucio_test_account):
    """Test we authenticated successfully"""
    remove_tokens()
    client = Client()
    result = client.whoami()

    assert result["account"] == rucio_test_account


def test_userpass_authentication(rucio_test_account):
    """Test we authenticated successfully"""
    remove_tokens()
    client = Client(
        auth_type="userpass", creds=dict(username="test-user", password="secret")
    )
    result = client.whoami()
    assert result["account"] == rucio_test_account


def test_x509_authentication(user_cert, user_key, rucio_test_account):
    """Test we authenticated successfully"""
    remove_tokens()
    client = Client(
        auth_type="x509", creds=dict(client_cert=user_cert, client_key=user_key)
    )
    result = client.whoami()
    assert result["account"] == rucio_test_account


def test_x509_proxy_authentication(voms_proxy, rucio_test_account):
    """Test we authenticated successfully"""
    remove_tokens()
    client = Client(auth_type="x509_proxy", creds=dict(client_proxy=voms_proxy))
    result = client.whoami()
    assert result["account"] == rucio_test_account


def test_rses():
    """Test the expected RSEs are configured"""
    client = Client()
    result = list(client.list_rses())

    rses = [r["rse"] for r in result]
    assert "STORAGE-1" in rses
    assert "STORAGE-2" in rses
    assert "STORAGE-3" in rses


def test_add_dataset(test_scope):
    """Test adding a simple dataset works"""
    dataset_name = f"/ctao.dpps.test/{test_scope}/dataset_aiv_basic"

    did_client = DIDClient()
    success = did_client.add_dataset(
        scope=test_scope,
        name=dataset_name,
        rse="STORAGE-1",
    )
    assert success

    names = list(did_client.list_dids(scope=test_scope, filters={}))
    assert dataset_name in names


@pytest.mark.usefixtures("voms_proxy")
def test_upload_file(test_scope, tmp_path):
    """Test uploading a simple file works"""
    lfn = f"/ctao.dpps.test/{test_scope}/file_aiv_basic"
    path = tmp_path / "file_aiv_basic"
    path.write_text("Hello, World!")

    upload_client = UploadClient()

    upload_spec = {
        "path": path,
        "rse": "STORAGE-2",
        "did_scope": test_scope,
        "did_name": lfn,
    }
    # 0 = success
    assert upload_client.upload([upload_spec]) == 0


def wait_for_replication_status(rule, status, timeout=180, poll=5):
    rule_client = RuleClient()

    start = time.perf_counter()

    current_status = None
    result = None

    while (time.perf_counter() - start) < timeout:
        result = rule_client.get_replication_rule(rule)
        current_status = result["state"]

        if current_status == status:
            return

        time.sleep(poll)

    msg = (
        f"Rule {rule} did not reach status '{status}' within {timeout} seconds."
        f" Current status is '{current_status}'.\nFull output: {result}"
    )
    raise TimeoutError(msg)


@pytest.mark.usefixtures("voms_proxy")
def test_replication(test_scope, tmp_path):
    name = "transfer_test"
    # dataset_lfn = name
    dataset_lfn = f"/ctao.dpps.test/{test_scope}/{name}"
    file_lfn = f"/ctao.dpps.test/{test_scope}/{name}.dat"

    path = tmp_path / f"{name}.dat"
    path.write_text("I am a test for replication rules.")

    main_rse = "STORAGE-1"
    replica_rse = "STORAGE-2"

    client = Client()
    upload_client = UploadClient()
    did_client = DIDClient()
    rule_client = RuleClient()
    replica_client = ReplicaClient()

    upload_spec = {
        "path": path,
        "rse": main_rse,
        "did_scope": test_scope,
        "did_name": file_lfn,
    }
    # 0 = success
    assert upload_client.upload([upload_spec]) == 0
    assert did_client.add_dataset(scope=test_scope, name=dataset_lfn)
    dids = [{"scope": test_scope, "name": file_lfn}]
    assert client.attach_dids(scope=test_scope, name=dataset_lfn, dids=dids)

    dids = [{"scope": test_scope, "name": dataset_lfn}]
    rule = rule_client.add_replication_rule(
        dids=dids, copies=1, rse_expression=replica_rse
    )[0]

    wait_for_replication_status(rule=rule, status="OK", timeout=180)
    replicas = next(replica_client.list_replicas(dids))
    assert replicas["states"] == {"STORAGE-1": "AVAILABLE", "STORAGE-2": "AVAILABLE"}
