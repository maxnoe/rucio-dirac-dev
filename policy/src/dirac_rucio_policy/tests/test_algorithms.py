import pytest

long_lfn = "/ctao/test/telescope/TEL001/events/2024/06/17/TEL001_SDH001_20240617T030105_SBID2000012345_OBSID2000006789_TEL_SHOWER_CHUNK000.fits.fz"
lfns = {
    "/ctao.org/foo/foo.dat": "foo",
    "/ctao.org/bar/test.dat": "bar",
    long_lfn: "test",
    # special handling
    "/ctao.dpps.test/": "root",
    "/ctao.dpps.test": "root",
    "/": "root",
}


@pytest.mark.parametrize(("lfn", "expected_scope"), lfns.items())
def test_extract_scope_ctao(lfn, expected_scope):
    from bdms_rucio_policy.algorithms import extract_scope_bdms

    scope, did = extract_scope_bdms(lfn, scopes=None)
    assert scope == expected_scope
    assert did == lfn


@pytest.mark.parametrize("lfn", lfns)
def test_extract_scope_ctao_invalid(lfn):
    from bdms_rucio_policy.algorithms import extract_scope_bdms

    with pytest.raises(ValueError, match="DID 'test:foo.dat' does not match"):
        extract_scope_bdms("test:foo.dat", scopes=None)

    with pytest.raises(ValueError, match="DID 'test/bar/baz' does not match"):
        extract_scope_bdms("test/bar/baz", scopes=None)
