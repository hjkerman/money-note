from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.repositories.entries import create_entry, delete_entry, list_entries, update_entry
from app.schemas import LedgerEntry, LedgerEntryIn, LedgerEntryPatch
from app.services.presentation import present_ledger_entries, present_ledger_entry

router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.get("/{section}", response_model=list[LedgerEntry])
def get_entries(section: str, _: dict = Depends(require_user)) -> list[dict]:
    if section not in {"current", "archive"}:
        raise HTTPException(status_code=404, detail="unknown section")
    return present_ledger_entries(list_entries(section))


@router.post("", response_model=LedgerEntry)
def post_entry(entry: LedgerEntryIn, _: dict = Depends(require_user)) -> dict:
    try:
        return present_ledger_entry(create_entry(entry))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{entry_id}", response_model=LedgerEntry)
def patch_entry(entry_id: int, patch: LedgerEntryPatch, _: dict = Depends(require_user)) -> dict:
    try:
        entry = update_entry(entry_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    return present_ledger_entry(entry)


@router.delete("/{entry_id}")
def remove_entry(entry_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="entry not found")
    return {"deleted": True}
