from pathlib import Path

import pytest

from rucio.client.replicaclient import ReplicaClient
from rucio.client.uploadclient import UploadClient
from rucio.client.didclient import DIDClient
from rucio.client import Client
from DIRAC.TransformationSystem.Client.Transformation import Transformation
from DIRAC.TransformationSystem.Client.TransformationClient import TransformationClient
from DIRAC.Interfaces.API.Job import Job
import datetime


from test_utils_dirac import wait_for_status
from DIRAC.Resources.Catalog.FileCatalog import FileCatalog


@pytest.fixture(scope="session")
def test_file(test_scope, tmp_path_factory):
    name = "test.dat"
    path = tmp_path_factory.mktemp("data_") / name
    path.write_text("Hello, World!")
    lfn = f"/testvo.example.org/{test_scope}/{name}"

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

    lfn = f"/testvo.example.org/{test_scope}/{name}"

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

    lfn = f"/testvo.example.org/{test_scope}/{name}"
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


@pytest.mark.verifies_usecase("DPPS-UC-110-1.X")
@pytest.mark.usefixtures("_init_dirac")
def test_add_metadata(tmp_path, test_scope):
    """
    Test the addition of metadata to a file in the DIRAC Rucio catalog.
    This test performs the following steps:
    1. Registers the file in Rucio using the DIRAC Data Management System.
    3. Sets metadata for the registered file.
    4. Retrieves and verifies the metadata.
    5. Searches for the file using various metadata queries.
    """
    from DIRAC.DataManagementSystem.Client.DataManager import DataManager

    name = "add_test_metadata.dat"
    path = tmp_path / name
    path.write_text("Hello from DIRAC")

    lfn = f"/testvo.example.org/{test_scope}/{name}"

    rse = "STORAGE-1"
    dm = DataManager()
    resultPutAndRegister = dm.putAndRegister(lfn, str(path), rse)

    # check dirac result
    # print("\n".join(result['CallStack']))
    assert resultPutAndRegister["OK"]
    failed = resultPutAndRegister["Value"]["Failed"]
    assert len(failed) == 0, f"Failed to upload file: {failed}, result: {result}"
    successful = resultPutAndRegister["Value"]["Successful"]
    assert lfn in successful
    assert "put" in successful[lfn]
    assert "register" in successful[lfn]

    # add metadata
    catalog = FileCatalog(catalogs=['RucioFileCatalog'])
    metadata_dict = {
                "MCCampaign": "Prod5bTest",
                "array_layout": "Advanced-Baseline",
                "site": "LaPalma",
                "particle": "electron",
                "thetaP": 20,
                "phiP": 180.0,
                "tel_sim_prog_version": "2020-06-29b",
                "tel_sim_prog": "sim_telarray",
                "data_level": -1,
                "outputType": "Data",
                "configuration_id": 15,
            }
    catalog.setMetadata(lfn, metadata_dict)
   
    # get metadata
    resultGetMetadata = catalog.getFileUserMetadata([lfn])
    assert resultGetMetadata["OK"]
    returnedMetadata = resultGetMetadata["Value"]["Successful"][lfn]
    assert returnedMetadata['MCCampaign'] == 'Prod5bTest'
    assert returnedMetadata['data_level'] == -1
    assert returnedMetadata['configuration_id'] == 15

    # find file by metadata
    # string
    metadata_dict = { 
            'particle': 'electron'}
                                            
    resultFindFilesByMetadata = catalog.findFilesByMetadata(metadata_dict)
    assert resultFindFilesByMetadata["OK"]
    assert lfn in resultFindFilesByMetadata["Value"]
    
    # number
    metadata_dict = {
            'configuration_id': {'=': 15}}
    assert lfn in catalog.findFilesByMetadata(metadata_dict)["Value"]

    metadata_dict = {
            'configuration_id': {'>=': 13}}
    assert lfn in catalog.findFilesByMetadata(metadata_dict)["Value"]

    metadata_dict = {
            'configuration_id': {'>=': 16}}
    assert len(catalog.findFilesByMetadata(metadata_dict)["Value"]) == 0

    # in
    metadata_dict = { 
            'particle': {'in': ['proton','electron']}}                                   
    resultFindFilesByMetadata = catalog.findFilesByMetadata(metadata_dict)
    assert resultFindFilesByMetadata["OK"]
    assert lfn in resultFindFilesByMetadata["Value"]
    

    metadata_dict = { 
            'particle': {'in': ['proton','electron']},'site': {'in': [ "LaPalma", 'paranal'] }  }                                 
    resultFindFilesByMetadata = catalog.findFilesByMetadata(metadata_dict)
    assert resultFindFilesByMetadata["OK"]
    assert lfn in resultFindFilesByMetadata["Value"]
   
    metadata_dict = { 
            'particle': {'in': ['proton','electron']},'site': {'in': [ "Paris", 'paranal'] }  }                                 
    resultFindFilesByMetadata = catalog.findFilesByMetadata(metadata_dict)
    assert resultFindFilesByMetadata["OK"]
    assert len(resultFindFilesByMetadata["Value"]) == 0

    metadata_dict = { 
            'particle': {'in': ['proton','electron']},'site': {'in': [ "LaPalma", 'paranal']},'configuration_id': {'=': 14} }                                
    resultFindFilesByMetadata = catalog.findFilesByMetadata(metadata_dict)
    assert resultFindFilesByMetadata["OK"]
    assert len(resultFindFilesByMetadata["Value"]) == 0

@pytest.mark.usefixtures("_init_dirac")
def test_transformation():
    transClient = TransformationClient()
        # Standard parameters

    transformation = Transformation()
    transformation.setTransformationName(str(datetime.datetime.now()))
    transformation.setType("DataReprocessing")
    transformation.setDescription("Rucio Catalog test")
    transformation.setLongDescription("Rucio Catalog test")
    transformation.setCataLog("RucioFileCatalog")
    inputquery = { 
        'particle': 'electron'}
    transformation.setInputMetaQuery(inputquery)
    workflow_body = create_workflow_body()
    transformation.setBody(workflow_body)
    resultTransformationCreate = transformation.addTransformation()
    transformation.setStatus("Active")
    transformation.setAgentType("Automatic")
    assert resultTransformationCreate["OK"]
    

def create_workflow_body():
    job = Job()
    job.setName("mandelbrot raw")
    job.setOutputSandbox(["*log"])
    job.setExecutable("ls")
    return(job.workflow.toXML())