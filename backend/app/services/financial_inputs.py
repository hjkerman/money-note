"""Explicit opt-in input boundary; ordinary SQLite callers retain legacy reads.

No provider is constructed or imported from experimental code by app runtime.
Implementations supply raw relationships/maintained inputs, never new financial
formulas. A read-only view must check its own lifetime before forwarding scope.
"""

from abc import ABC, abstractmethod


class FinancialInputScope(ABC):
    @abstractmethod
    def financial_inputs(self):
        """Return the explicitly supplied input provider, or None."""


def inputs_for(conn):
    return conn.financial_inputs() if isinstance(conn, FinancialInputScope) else None
