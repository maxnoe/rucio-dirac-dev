from .algorithms import extract_scope_dirac, lfn2pfn_dirac

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "SUPPORTED_VERSION",
    "get_algorithms",
]

SUPPORTED_VERSION = "~=37.0"


def get_algorithms():
    return {
        "lfn2pfn": {
            "dirac": lfn2pfn_dirac,
        },
        "scope": {
            "dirac": extract_scope_dirac,
        },
    }
