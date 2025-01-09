"""
CTAO rucio policy: schema.

Modified from lib/rucio/common/schema/generic.py.
"""

from jsonschema import ValidationError, validate
from rucio.common.exception import InvalidObject
from rucio.common.schema.generic import SCHEMAS as GENERIC_SCHEMAS

NAME_LENGTH = 250
NAME = {
    "description": "Data Identifier name",
    "type": "string",
    # this was changed with respect to the "generic" scheme
    # allow slashes in filenames, require starts with /
    "pattern": "^/[A-Za-z0-9][A-Za-z0-9\\.\\-\\_/]*$",
    "maxLength": NAME_LENGTH,
}

# CHANGED from default, taken from belleii schema to make work with dirac
SCOPE_NAME_REGEXP = "/([^/]*)(?=/)(.*)"

CUSTOM_SCHEMAS = {
    "name": NAME,
}


def validate_schema(name, obj):
    """
    Validate object against json schema

    :param name: The json schema name.
    :param obj: The object to validate.
    """
    try:
        if obj:
            schema = CUSTOM_SCHEMAS.get(name)
            if schema is None:
                schema = GENERIC_SCHEMAS.get(name, {})
            validate(obj, schema)
    except ValidationError as error:  # NOQA, pylint: disable=W0612
        raise InvalidObject(f"Problem validating {name}: {error}")
