import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from tabnanny import check
from typing import Any, Callable, List, Tuple, Union

from hive_rc_auto.helpers.config import Config
from hive_rc_auto.helpers.hive_calls import (
    HiveTrx,
    get_client,
    get_delegated_posting_auth_accounts,
    get_rcs,
    get_tracking_accounts,
    make_lighthive_call,
    send_custom_json,
)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel, Field


def get_mongo_db(collection: str) -> AsyncIOMotorCollection:
    """Returns the MongoDB"""
    return AsyncIOMotorClient(Config.DB_CONNECTION)["podping"][collection]

def get_utc_now_timestamp() -> datetime:
    return datetime.now(timezone.utc)

class RCStatus(str, Enum):
    OK = "ok"
    LOW = "low"
    HIGH = "high"




class RCAccType(str, Enum):
    DELEGATING = "delegating"
    TARGET = "target"


def mill(input: float) -> int:
    """Divide by 1 million"""
    return round(input / 1e6)


def mill_s(input: float) -> str:
    m = mill(input)
    return f"{m:>12,} M"


class RCManabar(BaseModel):
    current_mana: int
    last_update_time: datetime


class RCCreationAdjustment(BaseModel):
    amount: int
    precision: int
    nai: str

    @property
    def amount_float(self) -> float:
        return self.amount / (10 * self.precision)


class RCDirectDelegation(BaseModel):
    acc_from: str = Field(None, alias="from")
    acc_to: str = Field(None, alias="to")
    delegated_rc: int = 0
    cut: bool = None

    def db_format(self, trx: HiveTrx) -> dict:
        ans = {}
        ans["timestamp"] = get_utc_now_timestamp()
        ans["account"] = self.acc_to
        ans = ans | self.dict() | trx.dict()
        return ans

    @property
    def payload_item(self) -> List[dict]:
        return [
            "delegate_rc",
            {
                "from": self.acc_from,
                "delegatees": [self.acc_to],
                "max_rc": self.delegated_rc,
            },
        ]

    @property
    def cut_string(self) -> str:
        if self.cut is None:
            return ""
        if self.cut:
            return "| Cutting    !"
        else:
            return "| Increasing ^"

    def log_line_output(self, logger: Callable):
        logger(
            f"{self.acc_from:<16} -> {self.acc_to} | "
            f"{mill(self.delegated_rc):>12,} M"
            f"{self.cut_string}"
        )


class RCAccount(BaseModel):
    timestamp: datetime = Field(
        default_factory=get_utc_now_timestamp,
        title="Timestamp",
        description="Timestamp of RC reading.",
    )
    account: str = Field(None, title="Account Name")
    delegating: RCAccType = Field(
        RCAccType.TARGET,
        title="Delegating",
        description="Delegating account or target account",
    )
    rc_manabar: RCManabar = Field(title="RC Manabar")
    max_rc_creation_adjustment: RCCreationAdjustment
    max_rc: int = Field(title="RC Max")
    delegated_rc: int = Field(title="Out Deleg")
    received_delegated_rc: int = Field(title="Recv Deleg")
    real_mana: int = Field(
        0,
        title="Current RC",
        description="Current RC Mana after allowing for regeneration.",
    )
    real_mana_percent: float = Field(
        0.0,
        title="RC Now",
        description="Current RC Mana Percentage after allowing for regeneration.",
    )
    delta_percent: float = Field(
        0.0, title="RC Dt", description="RC Delta extrapolated out for 1 hour"
    )
    rc_deleg_available: int = Field(
        0,
        title="RC Dl Avail",
        description="Current RC this account can delegate.",
    )
    old_mana_percent: float = Field(
        0.0, title="RC Last", description="Previous RC Mana Percentage."
    )
    status: RCStatus = 0
    alarm_set: bool = Field(
        False, title="Alarm", description="Flag for raising an alarm."
    )
    deleg_out: List[RCDirectDelegation] = Field(
        [],
        title="Delegations made",
        description="Outgoing delegations from this account",
    )
    deleg_recv: List[Any] = Field(
        [],
        title="Delegations made",
        description="Outgoing delegations from this account",
    )

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)
        if data.get("deleg_out"):
            # Handle correct transfer of mutable strings
            __pydantic_self__.deleg_out = data["deleg_out"].copy()

        # Calculate real_mana (RC) as a percentage allowing for regeneration
        last_mana = __pydantic_self__.rc_manabar.current_mana
        max_mana = __pydantic_self__.max_rc
        updated_at = __pydantic_self__.rc_manabar.last_update_time
        time_since_last = datetime.now(timezone.utc) - updated_at
        regenerated_mana = (
            time_since_last.total_seconds()
            * max_mana
            / Config.VOTING_MANA_REGENERATION_IN_SECONDS
        )
        __pydantic_self__.real_mana = last_mana + regenerated_mana
        real_mana_percent = __pydantic_self__.real_mana * 100 / max_mana
        __pydantic_self__.real_mana_percent = (
            100.0 if real_mana_percent > 100 else real_mana_percent
        )
        # Filter for too_high and too_low
        if (
            not __pydantic_self__.account in Config.DELEGATING_ACCOUNTS
            and __pydantic_self__.received_delegated_rc
            and real_mana_percent > Config.RC_PCT_UPPER_TARGET
        ):
            __pydantic_self__.status = RCStatus.HIGH
        elif real_mana_percent < Config.RC_PCT_LOWER_TARGET:
            __pydantic_self__.status = RCStatus.LOW
        else:
            __pydantic_self__.status = RCStatus.OK

        __pydantic_self__.delta_percent = (
            (__pydantic_self__.real_mana_percent - __pydantic_self__.old_mana_percent)
            if __pydantic_self__.old_mana_percent != 0.0
            else 0.0
        )
        # Extrapolate RC Delta to 1 hour
        __pydantic_self__.delta_percent *= 3600 / Config.UPDATE_FREQUENCY_SECS

        if (
            __pydantic_self__.real_mana_percent + __pydantic_self__.delta_percent
            < Config.RC_PCT_ALARM_LEVEL
        ):
            __pydantic_self__.alarm_set = True

        __pydantic_self__.rc_deleg_available = __pydantic_self__.real_mana - (
            Config.RC_BASE_LEVEL + __pydantic_self__.received_delegated_rc
        )

    class Config:
        use_enum_values = True  # <--

    @property
    def delta_icon(self) -> str:
        """"""
        if self.status == RCStatus.LOW:
            return "🔴"
        if self.delta_percent > 0:
            return "✅"
        if self.delta_percent < 0:
            return "🟡"
        return "🟦"

    @property
    def rc(self):
        """Return RC as a percentage"""
        return self.rc_manabar.current_mana / self.max_rc

    @property
    def rc_percent(self):
        return self.rc * 100

    async def fill_delegations(self):
        self.deleg_out = await list_rc_direct_delegations(self.account)

    def calculate_new_delegation(self) -> int:
        """
        According to the rules, work out what the new total delegation this account
        needs to return to range.
        If delegation is going DOWN, returns the amount it must go down by as a negative.
        """
        if self.status == RCStatus.LOW:
            percent_gap = Config.RC_PCT_LOWER_TARGET - self.real_mana_percent
            new_amount = self.max_rc * (1 + ((percent_gap) / 100))
            return new_amount
        if self.status == RCStatus.HIGH and self.delta_percent > 0:
            percent_gap = self.real_mana_percent - Config.RC_PCT_UPPER_TARGET
            delta = -(self.max_rc * (((percent_gap) / 100))) * 1.3
            return delta
        return 0

    @property
    def db_format(self) -> dict:
        """Return fields to stor in the database"""
        data = self.dict(
            include={
                "timestamp": True,
                "account": True,
                "delegating": True,
                "status": True,
                "max_rc": True,
                "delegated_rc": True,
                "received_delegated_rc": True,
                "real_mana": True,
                "real_mana_percent": True,
                "delta_percent": True,
                "rc_deleg_available": True,
            }
        )
        data["delta_icon"] = self.delta_icon
        if Config.TESTNET:
            data["testnet"] = True
        return data

    def log_output(self):
        logging.info(f"{self.account:<16} ---------------------------------------- ")
        logging.info(f"  % | {self.rc_percent:>5.2f} ")
        logging.info(f"  % | {self.real_mana_percent:>5.2f} ")
        logging.info(f"Max | {self.max_rc:>20,}")
        logging.info(f"Cur | {self.real_mana:>20,}")
        logging.info(f"Del | {self.delegated_rc:>20,}")
        logging.info(f"Rec | {self.received_delegated_rc:>20,}")

    def log_line_output(self, logger: Callable):
        alarm_txt = " <----- Alarm" if self.alarm_set else ""
        logger(
            f"{self.account:<16} | {self.delta_icon} | "
            f"{self.real_mana_percent:>6.1f} %| "
            f"{self.delta_percent:>8.2f} %| "
            f"{mill(self.real_mana):>12,} M |"
            # f"{mill(self.max_rc):>12,} M | "
            f"{mill(self.delegated_rc):>12,} M |"
            f"{mill(self.received_delegated_rc):>12,} M |"
            # f"{mill(self.rc_deleg_available):>12,} M |"
            f"{alarm_txt}"
        )

    @classmethod
    def log_line_header(cls, logger: Callable):
        logger("-" * 50)
        logger(
            f"{cls.__fields__['account'].field_info.title:<16} |    | "
            f"{cls.__fields__['real_mana_percent'].field_info.title:>6} %| "
            f"{cls.__fields__['delta_percent'].field_info.title:>8} %| "
            f"{cls.__fields__['real_mana'].field_info.title:>12} M |"
            # f"{cls.__fields__['max_rc'].field_info.title:>12} M | "
            f"{cls.__fields__['delegated_rc'].field_info.title:>12} M |"
            f"{cls.__fields__['received_delegated_rc'].field_info.title:>12} M |"
            # f"{cls.__fields__['rc_deleg_available'].field_info.title:>12} M |"
        )


class RCListOfAccounts(BaseModel):
    all: List[str] = []
    delegating: List[str] = []
    receiving: List[str] = []

    def __init__(__pydantic_self__, primary_account=Config.PRIMARY_ACCOUNT) -> None:
        # Slow and expensive operation. Run on startup and rarely.
        super().__init__()
        __pydantic_self__.delegating = get_delegated_posting_auth_accounts(
            primary_account
        )
        __pydantic_self__.receiving = get_tracking_accounts(primary_account)
        __pydantic_self__.all = list(
            set(__pydantic_self__.delegating + __pydantic_self__.receiving)
        )


class RCAllData(BaseModel):

    timestamp: datetime = Field(
        default=datetime.now(timezone.utc),
        title="Timestamp",
        description="Timestamp of All readings.",
    )
    rcs: List[RCAccount] = Field(
        [], title="All RC Accounts", description="All the tracked accounts RC details"
    )
    accounts: RCListOfAccounts
    pending_delegations: List[RCDirectDelegation] = Field(
        [], title="List of pending delegations"
    )

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)

    def pending_delegations_by(self, delegator: str) -> int:
        """Return just the pending delegations for a specific delgator account"""
        return int(sum([dd.delegated_rc for dd in self.pending_delegations]))

    async def fill_data(self, old_all_rcs: List[RCAccount] = None):
        """
        Fills in the data
        """
        self.timestamp = datetime.now(timezone.utc)
        self.rcs = await get_rc_of_accounts(self.accounts, old_all_rcs=old_all_rcs)
        pass

    async def update_delegations(self):
        """
        Implement rules to update the delegations of high or low accounts
        """
        new_delegations = []
        if self.rcs:
            for rc in self.rcs:
                if (
                    rc.account in self.accounts.receiving
                    and not rc.status == RCStatus.OK
                ):
                    new_amount = rc.calculate_new_delegation()
                    new_delegations.append((rc.account, new_amount))
                    logging.debug(f"Delegate {mill_s(new_amount)} to {rc.account:>16}")

            new_delegations.sort(key=lambda x: x[1], reverse=True)
            for deleg in new_delegations:
                if deleg[1] > 0:
                    delegate_from = await self.which_account_to_delegate_from(
                        deleg[0], amount=deleg[1]
                    )
                    new_dd = RCDirectDelegation.parse_obj(
                        {
                            "from": delegate_from,
                            "to": deleg[0],
                            "delegated_rc": deleg[1],
                            "cut": False,
                        }
                    )
                    self.pending_delegations.append(new_dd)
                    logging.debug(f"Deleg from {delegate_from} {deleg[0]} {deleg[1]}")
                elif deleg[1] < 0:
                    (
                        cut_delegate_from,
                        new_amount,
                    ) = await self.which_account_to_cut_delegation_from(
                        deleg[0], amount=deleg[1]
                    )
                    new_dd = RCDirectDelegation.parse_obj(
                        {
                            "from": cut_delegate_from,
                            "to": deleg[0],
                            "delegated_rc": new_amount,
                            "cut": True,
                        }
                    )
                    self.pending_delegations.append(new_dd)
                    logging.debug(
                        f"Cut Deleg from {cut_delegate_from} {deleg[0]} {deleg[1]}"
                    )

    async def get_payload_for_pending_delegations(
        self, send_json: bool = False
    ) -> List:
        """
        Sorts through the pending delegations and returns separate payloads
        one for each delegator. If send_json is True, send the jsons
        """
        payloads = []
        hive_operation_id = "rc"
        client = get_client(posting_keys=[Config.POSTING_KEY])
        different_delegators = {dd.acc_from for dd in self.pending_delegations}
        for delegator in different_delegators:
            payload = []
            for dd in [
                dd for dd in self.pending_delegations if dd.acc_from == delegator
            ]:
                # Each item in payload must be a list with one item in it
                payload += [dd.payload_item]
            payloads.append(payload)
            if send_json:
                try:
                    trx = await send_custom_json(
                        client=client,
                        payload=payload,
                        hive_operation_id=hive_operation_id,
                        required_posting_auth=dd.acc_from,
                    )
                    if trx:
                        logging.info(f"Custom Json: {trx.trx_num}")
                        db_name = (
                            "rc_history_testnet" if Config.TESTNET else "rc_history"
                        )
                        db_delegations = get_mongo_db(db_name)
                        await db_delegations.insert_many(
                            [pd.db_format(trx=trx) for pd in self.pending_delegations]
                        )
                except Exception as ex:
                    logging.error(ex)
        return payloads

    def log_output(self, logger: Callable):
        """
        Log the output of all the data to the passed logger
        """
        if self.rcs:
            self.rcs[0].log_line_header(logger)
            [
                rc.log_line_output(logger)
                for rc in self.rcs
                if rc.delegating == RCAccType.DELEGATING
            ]
            logger("-------- Targets             -----------")
            [
                rc.log_line_output(logger)
                for rc in self.rcs
                if rc.delegating == RCAccType.TARGET
            ]
        if self.pending_delegations:
            logger("-------- Pending delegations  -----------")
            [dd.log_line_output(logger) for dd in self.pending_delegations]

    def _get_rcs(self, account: str) -> RCAccount:
        return [rc for rc in self.rcs if rc.account == account][0]

    def _get_inbound_delegations(self, account: str) -> List[RCDirectDelegation]:
        dd_all = []
        for acc in self.accounts.delegating:
            rc = self._get_rcs(acc)
            dd_all += [dd for dd in rc.deleg_out if dd.acc_to == account]
        return dd_all

    async def which_account_to_delegate_from(self, target: str, amount: int) -> str:
        """
        Takes in a target account name and an amount and returns which delegating account
        has enough RC to fulfill the delegation.
        """
        rc = self._get_rcs(target)
        dd_list = self._get_inbound_delegations(target)

        logging.debug(f"Account: {target}")
        [dd.log_line_output(logging.debug) for dd in dd_list]

        for delegator in self.accounts.delegating:
            dd_from = [dd for dd in dd_list if dd.acc_from == delegator]
            if dd_from:
                amount -= dd_from[0].delegated_rc - self.pending_delegations_by(
                    delegator
                )
            rc_real_mana = self._get_rcs(delegator).real_mana
            logging.debug(
                f"Checking: {delegator:<16} | "
                f"{mill_s(rc_real_mana)} - {mill_s(amount)} "
                f"= {mill_s(rc_real_mana-amount)}"
            )
            if self._get_rcs(delegator).real_mana > amount:
                return delegator

        return "Not enough RCs"

    async def which_account_to_cut_delegation_from(
        self, target: str, amount: int
    ) -> Tuple[str, int]:
        """Which delegating account can we reduce delegation from to drop delegation
        by the target amount"""
        rc = self._get_rcs(target)
        dd_list = self._get_inbound_delegations(target)
        logging.info(f"Account: {target:>16} remove {mill_s(amount)}")
        [dd.log_line_output(logging.debug) for dd in dd_list]
        for delegator in reversed(self.accounts.delegating):
            dd_from = [dd for dd in dd_list if dd.acc_from == delegator]
            if dd_from:
                new_delegation = max(dd_from[0].delegated_rc + amount, 0)
                logging.info(
                    f"Checking: {delegator:<16} | "
                    f"{mill_s(dd_from[0].delegated_rc)} {mill_s(amount)} "
                    f"= {mill_s(new_delegation)}"
                )
                return delegator, new_delegation

    async def store_all_data(self):
        """Store all this item's relevant data in a MongoDB"""
        db_name = "rc_history_testnet" if Config.TESTNET else "rc_history"
        db_rc_history = get_mongo_db(db_name)
        data = [rc.db_format for rc in self.rcs]
        ans = await db_rc_history.insert_many(data)


async def get_rc_of_accounts(
    check_accounts: RCListOfAccounts, old_all_rcs: List[RCAccount] = None
) -> List[RCAccount]:
    """
    Performs the lookup and fills in the RC data for all accounts
    """

    response = get_rcs(check_accounts.all)
    old_current_percents = (
        {i.account: i.real_mana_percent for i in old_all_rcs} if old_all_rcs else None
    )
    ans: List[RCAccount] = []
    if rc_accounts := response.get("rc_accounts"):
        for a in rc_accounts:
            if old_current_percents:  # and old_current_percents[a.get("account")]:
                a["old_mana_percent"] = old_current_percents[a.get("account")]

            if a["account"] in check_accounts.delegating:
                # Now fill in delegations FROM all delegating accounts
                dd_list = await list_rc_direct_delegations(a["account"])
                a["deleg_out"] = dd_list
                [dd.log_line_output(logging.debug) for dd in dd_list]
                a["delegating"] = RCAccType.DELEGATING
            else:
                a["delegating"] = RCAccType.TARGET
            ans.append(RCAccount.parse_obj(a))
    return ans


async def list_rc_direct_delegations(
    acc_from: str, acc_to: str = "", limit: int = 100
) -> List[RCDirectDelegation]:
    """
    Returns all RC Delegations from this account optionaly to the second
    one. If you want a delegation from one account to another only, set limit =1
    https://peakd.com/rc/@howo/direct-rc-delegation-documentation
    """
    client_rc = get_client(api_type="rc_api")
    query = {"start": [acc_from, acc_to], "limit": limit}
    response = make_lighthive_call(
        client=client_rc,
        call_to_make=client_rc.list_rc_direct_delegations,
        params=query,
    )
    if response.get("rc_direct_delegations"):
        ans = [
            RCDirectDelegation.parse_obj(res)
            for res in response.get("rc_direct_delegations")
        ]
        return ans
    return []
