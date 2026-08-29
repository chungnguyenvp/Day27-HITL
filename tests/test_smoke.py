import json


def test_public_modules_import_and_audit_file_is_json_list():
    import app  # noqa: F401
    import audit  # noqa: F401
    import graph  # noqa: F401
    import models  # noqa: F401
    import reasoning  # noqa: F401

    with open("audit_log.json", encoding="utf-8") as handle:
        assert isinstance(json.load(handle), list)
