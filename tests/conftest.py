import os
import subprocess as sp
from datetime import datetime
from secrets import token_hex

import pytest

from rucio.client.scopeclient import ScopeClient

USER_CERT = os.getenv("RUCIO_CFG_CLIENT_CERT", "/tmp/usercert.pem")
USER_KEY = os.getenv("RUCIO_CFG_CLIENT_KEY", "/tmp/userkey.pem")


@pytest.fixture(scope="session")
def rucio_test_account():
    return "root"


@pytest.fixture(scope="session")
def _dirac_proxy():
    sp.run(["dirac-proxy-init", "-g", "dpps_group"], check=True)


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
    sp.run(
        [
            "voms-proxy-init",
            "-valid",
            "9999:00",
            "-cert",
            user_cert,
            "-key",
            user_key,
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
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
