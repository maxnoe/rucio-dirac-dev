from pathlib import Path

import pytest

from rucio.client.replicaclient import ReplicaClient
from rucio.client.uploadclient import UploadClient
from test_utils_dirac import wait_for_status


@pytest.fixture(scope="session")
def test_file(test_scope, tmp_path_factory):
    name = "test.dat"
    path = tmp_path_factory.mktemp("data_") / name
    path.write_text("Hello, World!")
    lfn = f"/testvo/{test_scope}/{name}"

    upload_spec = {
        "path": path,
        "rse": "STORAGE-2",
        "did_scope": test_scope,
        "did_name": lfn,
        "lifetime": 2,
    }
    upload_client = UploadClient()
    upload_client.upload([upload_spec])
    return lfn


@pytest.mark.usefixtures("_init_dirac")
def test_get_file_metadata(test_file):
    from DIRAC.Resources.Storage.StorageElement import StorageElement

    se = StorageElement("STORAGE-2")
    result = se.getFileMetadata(test_file)
    assert result["OK"], f"Error getting file metadatae: {result['Message']}"


@pytest.mark.usefixtures("_init_dirac")
def test_get_file(test_file, tmp_path):
    from DIRAC.Interfaces.API.Dirac import Dirac

    dirac = Dirac()
    result = dirac.getFile(test_file, destDir=str(tmp_path))
    assert result["OK"], f"Error downloading file: {result['Message']}"
    assert (tmp_path / "test.dat").read_text() == "Hello, World!"


@pytest.mark.usefixtures("_init_dirac")
def test_add_file(tmp_path, test_scope):
    from DIRAC.DataManagementSystem.Client.DataManager import DataManager

    name = "add_test.dat"
    path = tmp_path / name
    path.write_text("Hello from DIRAC")

    lfn = f"/testvo/{test_scope}/{name}"

    rse = "STORAGE-1"
    dm = DataManager()
    result = dm.putAndRegister(lfn, str(path), rse)

    # check dirac result
    assert result["OK"]
    failed = result["Value"]["Failed"]
    assert len(failed) == 0
    successful = result["Value"]["Successful"]
    assert lfn in successful
    assert "put" in successful[lfn]
    assert "register" in successful[lfn]

    # check with rucio
    replica_client = ReplicaClient()
    replicas = list(replica_client.list_replicas([{"scope": test_scope, "name": lfn}]))
    assert len(replicas) == 1
    assert replicas[0]["states"][rse] == "AVAILABLE"


@pytest.mark.usefixtures("_init_dirac")
def test_rucio_file_as_job_input(test_file):
    from DIRAC.Interfaces.API.Dirac import Dirac
    from DIRAC.Interfaces.API.Job import Job

    dirac = Dirac()

    job = Job()
    name = Path(test_file).name
    job.setExecutable("cat", arguments=name)
    job.setName("test_input_data")
    job.setDestination("CTAO.CI.de")
    job.setInputData([test_file])

    res = dirac.submitJob(job)
    assert res["OK"]
    job_id = res["Value"]

    wait_for_status(dirac, job_id=job_id, status="Done", error_on={"Failed"})


@pytest.mark.usefixtures("_init_dirac")
def test_store_output(test_scope, tmp_path):
    from DIRAC.Interfaces.API.Dirac import Dirac
    from DIRAC.Interfaces.API.Job import Job

    rse = "STORAGE-1"

    dirac = Dirac()

    job = Job()
    name = "output.dat"
    job.setExecutable("bash", arguments=f"-c 'echo \"Hello from DIRAC\" > {name}'")
    job.setName("test_output_data")
    job.setDestination("CTAO.CI.de")

    lfn = f"/testvo/{test_scope}/{name}"
    job.setOutputData([f"LFN:{lfn}"], outputSE=rse)

    res = dirac.submitJob(job)
    assert res["OK"]
    job_id = res["Value"]

    wait_for_status(dirac, job_id=job_id, status="Done", error_on={"Failed"})

    # see that the file is known to rucio
    replica_client = ReplicaClient()
    replicas = list(replica_client.list_replicas([{"scope": test_scope, "name": lfn}]))
    assert len(replicas) == 1
    assert replicas[0]["states"][rse] == "AVAILABLE"

    # get the file with dirac
    result = dirac.getFile(lfn, destDir=str(tmp_path))
    assert result["OK"], f"Error downloading file: {result['Message']}"
    assert (tmp_path / name).read_text() == "Hello from DIRAC\n"
