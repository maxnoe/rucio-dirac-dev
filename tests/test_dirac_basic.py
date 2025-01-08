"""Test job status."""
import pytest

from test_utils_dirac import wait_for_status

pytestmark = [
    pytest.mark.wms,
    pytest.mark.dirac_client,
]


@pytest.mark.usefixtures("_dirac_proxy")
def test_status():
    from DIRAC.Interfaces.API.Dirac import Dirac
    from DIRAC.Interfaces.API.Job import Job

    dirac = Dirac()

    job = Job()
    job.setExecutable("echo", arguments="Hello world")
    job.setName("testjob")
    job.setDestination("CTAO.CI.de")
    res = dirac.submitJob(job)
    assert res["OK"]
    job_id = res["Value"]

    wait_for_status(dirac, job_id=job_id, status="Done")
