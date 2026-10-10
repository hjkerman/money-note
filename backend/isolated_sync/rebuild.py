"""Explicit O(N) bootstrap/reference assembly. Never a transaction finalizer."""

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping

from isolated_sync.canonical import Context, Object
from isolated_sync.facts import build_facts
from isolated_sync.patricia import Index
from isolated_sync.raw import TABLES, Row
from isolated_sync.segments import Tree, raw_root


@dataclass(frozen=True)
class Rebuild:
    trees: Mapping[str, Tree]
    raw: Object
    index: Index


def rebuild(context: Context, data: dict) -> Rebuild:
    """Admit complete explicit raw state, build immutable trees and complete F.

    No DB is opened, identity is issued, certificate is finalized or authority
    exposed. Callers must separately establish schema compatibility/read view.
    """
    facts = build_facts(context, data)
    trees = {table: Tree.build(context, table, [Row.make(table, r) for r in data[table]])
             for table in TABLES}
    return Rebuild(MappingProxyType(trees), raw_root(context, trees), Index.build(context, facts))
