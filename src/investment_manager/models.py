from dataclasses import dataclass


@dataclass
class Position:
    institution_name: str
    account_name: str
    account_number: str
    account_type: str
    owner: str
    ticker: str
    value: float


@dataclass
class Account:
    institution_name: str
    account_name: str
    account_number: str
    account_type: str
    owner: str
