import getpass
import shutil

import pytest

from rucio.client import Client
from rucio.client.didclient import DIDClient
from rucio.client.uploadclient import UploadClient


def test_server_version():
    """Test the expected version of rucio is running"""
    client = Client()
    result = client.ping()
    assert result["version"].startswith("37")


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
    dataset_name = f"/testvo.example.org/{test_scope}/dataset_aiv_basic"

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
    lfn = f"/testvo.example.org/{test_scope}/file_aiv_basic"
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
