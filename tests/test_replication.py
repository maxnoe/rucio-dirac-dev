import time

import pytest

from rucio.client import Client
from rucio.client.client import ReplicaClient, RuleClient
from rucio.client.didclient import DIDClient
from rucio.client.uploadclient import UploadClient


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
    dataset_lfn = f"/testvo.example.org/{test_scope}/{name}"
    file_lfn = f"/testvo.example.org/{test_scope}/{name}.dat"

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
