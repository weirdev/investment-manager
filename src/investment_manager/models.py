from dataclasses import dataclass


@dataclass
class Position:
    institution_name: str
    account_name: str
    account_type: str
    ticker: str
    value: float


@dataclass
class Account:
    institution_name: str
    account_name: str
    account_type: str
