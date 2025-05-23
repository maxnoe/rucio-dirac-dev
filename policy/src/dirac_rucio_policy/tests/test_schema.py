import re

import pytest
from rucio.common.exception import InvalidObject

valid_lfns = [
    "/testvo.example.org/foo/bar/test.dat",
    "/testvo.example.org/foo/bar/1234.dat",
    "/foo/bar",
    "/foo/bar/test.dat",
    "/testvo.example.org/dl0/telescope/TEL001/events/2024/06/17/TEL001_SDH001_20240617T030105_SBID2000012345_OBSID2000006789_TEL_SHOWER_CHUNK000.fits.fz",
]

invalid_lfns = [
    "foo",
    "foo.dat",
    # missing first slash
    "testvo.example.org/dl0/telescope/TEL001/events/2024/06/17/TEL001_SDH001_20240617T030105_SBID2000012345_OBSID2000006789_TEL_SHOWER_CHUNK000.fits.fz",
]


@pytest.mark.parametrize("lfn", valid_lfns)
def test_valid_lfns(lfn):
    from dirac_rucio_policy.schema import validate_schema

    validate_schema("name", lfn)


@pytest.mark.parametrize("lfn", invalid_lfns)
def test_invalid_lfns(lfn):
    from dirac_rucio_policy.schema import validate_schema

    with pytest.raises(InvalidObject):
        validate_schema("name", lfn)


def test_scope_name_regexp():
    from dirac_rucio_policy.schema import SCOPE_NAME_REGEXP

    true_scope = "foo"
    lfn = f"/testvo.example.org/{true_scope}/bar/test.dat"
    url = f"{true_scope}{lfn}"

    m = re.match(SCOPE_NAME_REGEXP, f"/{url}")
    assert m is not None
    scope, name = m.group(1, 2)
    assert scope == true_scope
    assert name == lfn
