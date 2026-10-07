"""One coherent financial read, followed by a fresh non-touching terminal guard.

This transport is additive. It is not a replay format, mutation receipt or a
way to resolve an unknown mutation outcome. No state or validation PASS outlives
its construction attempt; existing client publication/generation guards remain
necessary when clients eventually adopt it.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
import re

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import auth
from app.authoritative_schemas import AuthoritativeState
from app.config import get_settings
from app.db import SCHEMA, session
from app.db_migrations import CURRENT_SCHEMA_VERSION, _validate_revision_triggers
from app.money import validate_money_payload
from app.repositories.cash_flows import list_cash_flows
from app.repositories.entries import (
    list_confirmed_planned_entries, list_entries, list_recent_closed_month_expense_counts,
)
from app.repositories.panels import list_panels
from app.repositories.settings import list_settings
from app.schemas import CashFlow, LedgerEntry, MonthlyPanel
from app.services.card_charge import default_discount_policy
from app.services.card_charge.profiles import transit_discount_profile_status
from app.services.card_payments import current_payment_status, discount_month_status
from app.services.clock import app_today
from app.services.financial_relationships import card_ownership_read_view
from app.services.financial_periods import valid_fixed_confirmation_period
from app.services.judgment import app_judgment
from app.services.month import month_close_status
from app.services.presentation import present_ledger_entries, present_monthly_panels
from app.services.snapshot import (
    _validate_confirmation_timestamp, _validate_snapshot,
    export_snapshot_from_connection, snapshot_state_fingerprint,
)
from app.services.summary import _summary_values_from_read_view
from app.share_auth import SENSITIVE_SHARE_SETTING_KEYS


MAX_CONSTRUCTION_ATTEMPTS = 3


@dataclass(frozen=True)
class BundleCredential:
    token_hash: str
    user_id: int


def require_bundle_credential(request: Request) -> BundleCredential:
    # Capture the selection BEFORE ordinary auth. Cookie precedence is exactly
    # the existing contract; neither retry nor terminal verification reselects.
    token = auth._session_token_from_request(request)
    user = auth.require_user(request)
    if not token:
        raise HTTPException(401, "authentication required")
    return BundleCredential(auth._hash_session_token(token), int(user["id"]))


@dataclass(frozen=True)
class EvaluationContext:
    today: date
    month: str
    timezone_offset_minutes: int
    settings: Mapping[str, str]


@dataclass(frozen=True)
class ViewIdentity:
    revision: int
    schema: tuple[Any, ...]


def _read_identity(conn: Any) -> ViewIdentity:
    rows = conn.execute("SELECT id, revision, typeof(revision) FROM authoritative_state_revision").fetchall()
    if (len(rows) != 1 or rows[0][0] != 1 or rows[0][2] != "integer"
            or rows[0][1] < 0):
        raise ValueError("invalid authoritative revision state")
    # DDL counters alone can be reset. Also compare actual definitions, including
    # revision triggers and auth schema, so schema ABA cannot hide changed rules.
    schema = (
        conn.execute("PRAGMA user_version").fetchone()[0],
        conn.execute("PRAGMA main.schema_version").fetchone()[0],
        conn.execute("PRAGMA temp.schema_version").fetchone()[0],
        tuple(tuple(row) for row in conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )),
    )
    return ViewIdentity(rows[0][1], schema)


def _construct(conn: Any, credential: BundleCredential) -> tuple[dict[str, Any], ViewIdentity, EvaluationContext]:
    # This first financial read pins the SQLite snapshot before any projection.
    identity = _read_identity(conn)
    if identity.schema[0] != CURRENT_SCHEMA_VERSION:
        raise ValueError("authoritative state requires the current database version")
    _validate_revision_triggers(conn, SCHEMA)
    today = app_today()
    context = EvaluationContext(today, today.strftime("%Y-%m"),
                                get_settings().timezone_offset_minutes,
                                MappingProxyType(dict(list_settings(conn=conn))))
    _, snapshot = export_snapshot_from_connection(conn, today, require_current_columns=True)
    _validate_snapshot(snapshot)
    _validate_fixed_metadata(snapshot, context.settings.get("last_closed_month"))
    # Snapshot retains its strict validators, including its independent card
    # check. The existing T6.3 scope shares ONLY downstream card ownership PASS.
    with card_ownership_read_view(conn) as view:
        entries = list_entries("current", today=today, conn=view)
        panels = list_panels(context.month, include_confirmed_fixed=True, conn=view)
        summary = _summary_values_from_read_view(view, today=today, visible_current_entries=entries)
        payment = current_payment_status(today, conn=view)
        cycle_start = date(today.year, today.month, 1)
        cycle_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
        recent_start = (date(today.year - 1, 12, 1) if today.month == 1
                        else date(today.year, today.month - 1, 1))
        # Judgment uses raw inputs and calendar-month cash, NOT presentation
        # panels or the wider recent cash list displayed by the current clients.
        judgment = app_judgment(
            entries, list_panels(context.month, conn=view),
            list_cash_flows(cycle_start, cycle_end, conn=view), summary, payment,
            context.settings, list_recent_closed_month_expense_counts(conn=view), today=today,
        )
        state = {
            "month_close_status": month_close_status(today, conn=view, timezone_offset_minutes=context.timezone_offset_minutes),
            "entries": _present_entries(entries, view, context),
            "panels": _present_panels(panels, view, context),
            "summary": summary,
            "card_payment_status": payment,
            "judgment": judgment,
            "confirmed_planned_entries": _present_entries(list_confirmed_planned_entries(today, conn=view), view, context),
            "cash_flows": _complete_rows(list_cash_flows(recent_start, cycle_end, conn=view), CashFlow),
            "settings": {key: value for key, value in context.settings.items()
                         if key not in SENSITIVE_SHARE_SETTING_KEYS},
            "owner_discount_month": discount_month_status(context.month, "owner", conn=view),
            "family_discount_month": discount_month_status(context.month, "family", conn=view),
            "transit_discount_profile": transit_discount_profile_status(context.month, conn=view),
        }
    bundle = {
        "bundle_version": 1,
        "principal": {"user_id": credential.user_id},
        "authority": {
            "state_revision": identity.revision,
            "state_fingerprint": snapshot_state_fingerprint(snapshot),
            "evaluation_date": today.isoformat(),
            "discount_policy_defaults": {scope: default_discount_policy(scope) for scope in ("owner", "family")},
        },
        "snapshot": snapshot,
        "state": state,
    }
    return bundle, identity, context


def _complete_rows(rows: list[dict[str, Any]], model: type[BaseModel]) -> list[BaseModel]:
    required = {key for key, field in model.model_fields.items() if not field.exclude}
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"incomplete {model.__name__} projection: {sorted(missing)}")
        validate_money_payload(row)
    return [model.model_validate(row) for row in rows]


def _present_entries(entries: list[dict[str, Any]], view: Any, context: EvaluationContext) -> list[BaseModel]:
    rendered = present_ledger_entries(entries, conn=view, today=context.today, settings=context.settings)
    for raw, row in zip(entries, rendered, strict=True):
        if raw.get("_confirmed_expense") is None:
            # These three NULLs are the existing non-confirmed row contract,
            # not a fallback for a missing confirmed actual relationship.
            row.update({key: None for key in ("confirmed_amount_value", "confirmed_effective_discount_amount",
                                              "confirmed_effective_amount_value")})
    return _complete_rows(rendered, LedgerEntry)


def _present_panels(panels: list[dict[str, Any]], view: Any, context: EvaluationContext) -> list[BaseModel]:
    rendered = present_monthly_panels(panels, conn=view, today=context.today, settings=context.settings)
    for raw, row in zip(panels, rendered, strict=True):
        if raw["panel_type"] != "fixed":
            row.update(can_confirm_fixed=False, fixed_execution_month=None)
    return _complete_rows(rendered, MonthlyPanel)


def _validate_fixed_metadata(snapshot: dict[str, Any], last_closed: str | None) -> None:
    # The same current-v7 field contract used by restore, without historical
    # normalization, inference, writes or another schema connection.
    for panel in snapshot["data"]["monthly_panels"]:
        if panel["panel_type"] != "fixed":
            continue
        linked = panel["confirmed_cash_flow_id"] is not None
        timestamp, period = panel["confirmed_at"], panel["confirmed_month"]
        if timestamp is not None or linked:
            _validate_confirmation_timestamp(timestamp, "confirmed fixed expense has no valid confirmation timestamp")
        if not linked:
            if timestamp is not None or period is not None:
                raise ValueError("confirmed fixed expense has no cash-flow relationship")
            continue
        if not isinstance(panel["spent_on"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", panel["spent_on"]):
            raise ValueError("confirmed fixed expense has no valid spent_on date")
        try:
            day = date.fromisoformat(panel["spent_on"])
        except (ValueError, TypeError):
            raise ValueError("confirmed fixed expense has no valid spent_on date") from None
        if not valid_fixed_confirmation_period(day, period, last_closed):
            raise ValueError("confirmed fixed expense has inconsistent confirmed_month")


def _prepare(bundle: dict[str, Any]) -> JSONResponse:
    # Validate money BEFORE Pydantic can coerce a malformed fractional value.
    # Dump and prepare all JSON bytes inside the construction transaction.
    projections = bundle["state"]
    for key in ("entries", "panels", "confirmed_planned_entries", "cash_flows"):
        projections[key] = [row.model_dump(mode="json") for row in projections[key]]
    validate_money_payload(bundle)
    result = AuthoritativeState.model_validate(bundle).model_dump(mode="json")
    validate_money_payload(result)
    return JSONResponse(content=result)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _terminal_guard(credential: BundleCredential, identity: ViewIdentity,
                    context: EvaluationContext) -> bool:
    # A NEW view, never the old financial snapshot and never touching auth.
    with session(transaction_mode="DEFERRED") as conn:
        conn.execute("PRAGMA query_only=ON")
        current = _read_identity(conn)
        row = conn.execute(
            "SELECT auth_sessions.user_id, auth_sessions.expires_at, users.is_active "
            "FROM auth_sessions JOIN users ON users.id = auth_sessions.user_id "
            "WHERE auth_sessions.session_token_hash = ?", (credential.token_hash,),
        ).fetchone()
        # Read time AFTER potentially blocking SQLite reads, not before BEGIN.
        now = _utc_now()
        evaluation_date = app_today()
        try:
            expiry = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) if row else None
        except (ValueError, TypeError, AttributeError):
            expiry = None
        if (row is None or row["user_id"] != credential.user_id or not row["is_active"]
                or expiry is None or expiry.tzinfo is None or expiry <= now):
            raise HTTPException(401, "authentication required")
        return (current == identity and evaluation_date == context.today
                and get_settings().timezone_offset_minutes == context.timezone_offset_minutes)


def authoritative_state_response(credential: BundleCredential) -> JSONResponse:
    for _ in range(MAX_CONSTRUCTION_ATTEMPTS):
        with session(transaction_mode="DEFERRED") as conn:
            conn.execute("PRAGMA query_only=ON")
            bundle, identity, context = _construct(conn, credential)
            response = _prepare(bundle)
        if _terminal_guard(credential, identity, context):
            return response
    raise HTTPException(409, detail={"code": "authoritative_state_changed",
                                    "message": "authoritative state changed; refresh again"})
