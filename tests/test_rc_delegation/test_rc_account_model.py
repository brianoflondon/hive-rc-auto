"""Offline checks for the Pydantic models that parse Hive RC responses."""

from datetime import UTC, datetime

import pytest

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import HiveTrx
from hive_rc_auto.helpers.rc_delegation import (
    RCAccount,
    RCDirectDelegation,
    RCStatus,
)


def _account(current_mana: int, max_rc: int, **extra) -> RCAccount:
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "account": extra.pop("account", "target"),
        "rc_manabar": {"current_mana": current_mana, "last_update_time": now},
        "max_rc_creation_adjustment": {
            "amount": "5663907926",
            "precision": 6,
            "nai": "@@000000037",
        },
        "max_rc": max_rc,
        "delegated_rc": 0,
        "received_delegated_rc": extra.pop("received_delegated_rc", 0),
    }
    payload.update(extra)
    return RCAccount.model_validate(payload)


def test_low_mana_is_flagged(monkeypatch):
    monkeypatch.setattr(Config, "DELEGATING_ACCOUNTS", ["podping"])
    monkeypatch.setattr(Config, "RC_PCT_LOWER_TARGET", 50)
    monkeypatch.setattr(Config, "RC_PCT_UPPER_TARGET", 80)
    monkeypatch.setattr(Config, "RC_PCT_ALARM_LEVEL", 40)
    monkeypatch.setattr(Config, "RC_BASE_LEVEL", 1_000)
    monkeypatch.setattr(Config, "UPDATE_FREQUENCY_SECS", 300)
    monkeypatch.setattr(Config, "VOTING_MANA_REGENERATION_IN_SECONDS", 5 * 24 * 3600)
    monkeypatch.setattr(Config, "TESTNET", False)

    account = _account(10, 100)
    assert account.status == RCStatus.LOW
    assert account.real_mana_percent == pytest.approx(10, abs=0.1)
    assert account.alarm_set is True
    assert account.db_format["status"] == "low"
    assert account.max_rc_creation_adjustment.amount == 5663907926


def test_high_mana_on_a_receiving_account(monkeypatch):
    monkeypatch.setattr(Config, "DELEGATING_ACCOUNTS", ["podping"])
    monkeypatch.setattr(Config, "RC_PCT_LOWER_TARGET", 20)
    monkeypatch.setattr(Config, "RC_PCT_UPPER_TARGET", 80)
    monkeypatch.setattr(Config, "RC_PCT_ALARM_LEVEL", 10)
    monkeypatch.setattr(Config, "RC_BASE_LEVEL", 1_000)
    monkeypatch.setattr(Config, "UPDATE_FREQUENCY_SECS", 300)
    monkeypatch.setattr(Config, "VOTING_MANA_REGENERATION_IN_SECONDS", 5 * 24 * 3600)
    monkeypatch.setattr(Config, "TESTNET", False)

    account = _account(95, 100, received_delegated_rc=50)
    assert account.status == RCStatus.HIGH
    assert account.db_format["delegating"] == "target"


def test_delegation_aliases_and_header():
    delegation = RCDirectDelegation.model_validate({
        "from": "podping",
        "to": "target",
        "delegated_rc": 10,
        "cut": False,
    })
    assert delegation.acc_from == "podping"
    assert delegation.acc_to == "target"
    assert delegation.payload_item[1]["from"] == "podping"

    trx = HiveTrx.model_validate({"id": "abc", "block_num": 1, "trx_num": 2, "expired": False})
    stored = delegation.db_format(trx)
    assert stored["trx_id"] == "abc"
    assert stored["acc_from"] == "podping"

    lines = []
    RCAccount.log_line_header(lines.append)
    assert "RC Now" in lines[1]
