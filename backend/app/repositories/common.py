from math import ceil
from typing import Any


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def installment_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["monthly_amount"] = ceil((data["principal_amount"] + data["fee_amount"]) / data["months"])
    return data
