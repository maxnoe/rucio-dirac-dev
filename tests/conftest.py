import os
import subprocess as sp
from datetime import datetime
from secrets import token_hex
import logging

import pytest

from rucio.client.scopeclient import ScopeClient

USER_CERT = os.getenv("RUCIO_CFG_CLIENT_CERT", "/tmp/usercert.pem")
USER_KEY = os.getenv("RUCIO_CFG_CLIENT_KEY", "/tmp/userkey.pem")


log = logging.getLogger("tests")

SP_KWARGS = dict(text=True, stdout=sp.PIPE, stderr=sp.STDOUT)

@pytest.fixture(scope="session")
def rucio_test_account():
    return "root"


@pytest.fixture(scope="session")
def _dirac_configuration():

    ret = sp.run(["dirac-proxy-init", "--nocs"], **SP_KWARGS)
    assert ret.returncode == 0, f"Failed to create initial dirac proxy: {ret.stdout}"
    log.info("Successfully created initial dirac proxy: \n%s", ret.stdout)

    cmd = [
        "dirac-configure",
        "-C",
        "dips://dirac-server:9135/Configuration/Server",
        "-S",
        "Rucio-Tests",
    ]
    ret = sp.run(cmd, **SP_KWARGS)
    assert ret.returncode == 0, f"Failed configure dirac: {ret.stdout}"
    log.info("Successfully configured dirac: \n%s", ret.stdout)


@pytest.fixture(scope="session")
def _dirac_proxy(_dirac_configuration):
    ret = sp.run(["dirac-proxy-init", "-g", "test_group"], **SP_KWARGS)
    assert ret.returncode == 0, ret.stdout
    log.info("Successfully created dirac proxy: \n%s", ret.stdout)


@pytest.fixture(scope="session")
def _init_dirac(_dirac_proxy):
    """Import and init DIRAC, needs to be run first for anything using DIRAC"""
    import DIRAC

    DIRAC.initialize()


@pytest.fixture(scope="session")
def user_cert():
    return os.getenv("RUCIO_CFG_CLIENT_CERT", "/opt/rucio/etc/usercert.pem")


@pytest.fixture(scope="session")
def user_key():
    return os.getenv("RUCIO_CFG_CLIENT_KEY", "/opt/rucio/etc/userkey.pem")


@pytest.fixture(scope="session")
def voms_proxy(user_key, user_cert):
    """Auth proxy needed for accessing RSEs"""
    ret = sp.run(
        [
            "voms-proxy-init",
            "-valid",
            "9999:00",
            "-cert",
            user_cert,
            "-key",
            user_key,
        ],
        capture_output=True,
        text=True,
    )
    assert ret.returncode == 0, ret.stderr
    return f"/tmp/x509up_u{os.getuid()}"


@pytest.fixture(scope="session")
def test_scope(rucio_test_account):
    """To avoid name conflicts and old state, use a unique scope for the tests"""
    # length of scope is limited to 25 characters
    random_hash = token_hex(2)
    date_str = f"{datetime.now():%Y%m%d_%H%M%S}"
    scope = f"t_{date_str}_{random_hash}"

    sc = ScopeClient()
    sc.add_scope(rucio_test_account, scope)
    return scope
