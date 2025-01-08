import os
import time

TEST_TIMEOUT = float(os.getenv("DIRAC_TEST_JOB_TIMEOUT", 180))


def wait_for_status(
    dirac, job_id, status, error_on=None, timeout=TEST_TIMEOUT, poll=5.0
):
    start = time.perf_counter()

    current_status = None

    error_on = set(error_on) if error_on is not None else set()

    while (time.perf_counter() - start) < timeout:
        res = dirac.getJobStatus(job_id)
        current_status = res["Value"][job_id]["Status"]

        if current_status == status:
            return res

        if current_status in error_on:
            raise ValueError(f"Job entered error state '{current_status}'")

        time.sleep(poll)

    msg = (
        f"Job {job_id} did not reach status '{status}' within {timeout} seconds."
        f" Current status is '{current_status}'."
    )
    raise TimeoutError(msg)
