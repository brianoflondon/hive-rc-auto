from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable

from pydantic import BaseModel, Field


def mill(input: int) -> int:
    """Divide by 1 million"""
    return round(input / 1e6)


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


class RCStatus(Enum):
    OK = 0
    LOW = 1
    HIGH = 2


class RCAccount(BaseModel):
    timestamp: datetime = Field(
        default=datetime.now(timezone.utc),
        title="Timestamp",
        description="Timestamp of RC reading.",
    )
    account: str = Field(None, title="Account Name")
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

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)
        # Calculate real_mana (RC) as a percentage allowing for regeneration
        last_mana = __pydantic_self__.rc_manabar.current_mana
        max_mana = __pydantic_self__.max_rc
        updated_at = __pydantic_self__.rc_manabar.last_update_time
        time_since_last = datetime.now(timezone.utc) - updated_at
        regenerated_mana = (
            time_since_last.total_seconds()
            * max_mana
            / VOTING_MANA_REGENERATION_IN_SECONDS
        )
        __pydantic_self__.real_mana = last_mana + regenerated_mana
        real_mana_percent = __pydantic_self__.real_mana * 100 / max_mana
        __pydantic_self__.real_mana_percent = (
            100.0 if real_mana_percent > 100 else real_mana_percent
        )
        # Filter for too_high and too_low
        if (
            __pydantic_self__.account != DELEGATING_ACCOUNT
            and __pydantic_self__.received_delegated_rc
            and real_mana_percent > RC_PCT_UPPER_TARGET
        ):
            __pydantic_self__.status = RCStatus.HIGH
        elif real_mana_percent < RC_PCT_LOWER_TARGET:
            __pydantic_self__.status = RCStatus.LOW
        else:
            __pydantic_self__.status = RCStatus.OK

        __pydantic_self__.delta_percent = (
            (__pydantic_self__.real_mana_percent - __pydantic_self__.old_mana_percent)
            if __pydantic_self__.old_mana_percent != 0.0
            else 0.0
        )
        # Extrapolate RC Delta to 1 hour
        __pydantic_self__.delta_percent *= 3600 / UPDATE_FREQUENCY_MINS

        if (
            __pydantic_self__.real_mana_percent + __pydantic_self__.delta_percent
            < RC_PCT_ALARM_LEVEL
        ):
            __pydantic_self__.alarm_set = True

        __pydantic_self__.rc_deleg_available = __pydantic_self__.real_mana - (
            RC_BASE_LEVEL + __pydantic_self__.received_delegated_rc
        )

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
            f"{self.delta_percent:>7.3f} %| "
            f"{mill(self.real_mana):>12,} M |"
            # f"{mill(self.max_rc):>12,} M | "
            f"{mill(self.delegated_rc):>12,} M |"
            f"{mill(self.received_delegated_rc):>12,} M |"
            # f"{mill(self.rc_deleg_available):>12,} M |"
            f"{alarm_txt}"
        )

    @classmethod
    def log_line_header(cls, logger: Callable):
        logger(
            f"{cls.__fields__['account'].field_info.title:<16} |    | "
            f"{cls.__fields__['real_mana_percent'].field_info.title:>6} %| "
            f"{cls.__fields__['delta_percent'].field_info.title:>7} %| "
            f"{cls.__fields__['real_mana'].field_info.title:>12} M |"
            # f"{cls.__fields__['max_rc'].field_info.title:>12} M | "
            f"{cls.__fields__['delegated_rc'].field_info.title:>12} M |"
            f"{cls.__fields__['received_delegated_rc'].field_info.title:>12} M |"
            # f"{cls.__fields__['rc_deleg_available'].field_info.title:>12} M |"
        )


class RCDirectDelegation(BaseModel):
    acc_from: str = Field(None, alias="from")
    acc_to: str = Field(None, alias="to")
    delegated_rc: int = 0

    @property
    def payload_item(self):
        return [
            "delegate_rc",
            {
                "from": self.acc_from,
                "delegatees": [self.acc_to],
                "max_rc": self.delegated_rc,
            },
        ]
