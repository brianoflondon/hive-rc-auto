import logging
import os
import re
import uuid
from datetime import datetime

import pytest
from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import (
    construct_operation,
    get_client,
    send_custom_json,
)
from lighthive.datastructures import Operation
from lighthive.exceptions import RPCNodeException

os.environ["TESTNET"] = "true"
hive_operation_id = "bol_testing"


@pytest.mark.asyncio
async def test_construct_operation():
    payload = {"key": "value"}
    payload = {"myfield": uuid.uuid4(), "datetime": datetime.utcnow()}
    op = await construct_operation(
        hive_operation_id=hive_operation_id,
        payload=payload,
        required_posting_auth=Config.PRIMARY_ACCOUNT,
    )
    assert type(op) is Operation


@pytest.mark.asyncio
async def test_send_custom_json():
    payload = {"key": "value"}
    payload = {"myfield": uuid.uuid4(), "datetime": datetime.utcnow()}
    op = await construct_operation(
        hive_operation_id=hive_operation_id,
        payload=payload,
        required_posting_auth=Config.PRIMARY_ACCOUNT,
    )
    client = get_client()
    try:
        trx = await send_custom_json(
            client=client,
            payload=payload,
            hive_operation_id=hive_operation_id,
            required_posting_auth=Config.PRIMARY_ACCOUNT,
        )
    except RPCNodeException as ex:
        assert re.match(r".*missing required posting authority.*", ex.args[0])

    client = get_client(posting_keys=[Config.POSTING_KEY])
    try:
        trx = await send_custom_json(
            client=client,
            payload=payload,
            hive_operation_id=hive_operation_id,
            required_posting_auth=Config.PRIMARY_ACCOUNT,
        )
    except Exception as ex:
        assert False
    assert trx


@pytest.mark.asyncio
async def test_send_multiple_payloads():
    payload = []
    for n in range(10):
        payload += [
            {
                "payload_item": n,
                "myfield": uuid.uuid4(),
                "datetime": datetime.utcnow(),
            }
        ]

    client = get_client(posting_keys=[Config.POSTING_KEY])
    try:
        trx = await send_custom_json(
            client=client,
            payload=payload,
            hive_operation_id=hive_operation_id,
            required_posting_auth=Config.PRIMARY_ACCOUNT,
        )
    except Exception as ex:
        assert False
    assert trx
