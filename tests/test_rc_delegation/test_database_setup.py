import pytest
from hive_rc_auto.helpers.rc_delegation import setup_mongo_db


def test_setup_mongo_db():
    setup_mongo_db()
    assert True
