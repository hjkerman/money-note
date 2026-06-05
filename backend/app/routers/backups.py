from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import require_user
from app.schemas import CsvBackupImportIn
from app.services.csv_backup import export_csv_backup, import_csv_backup

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("/csv")
def download_csv_backup(_: dict = Depends(require_user)) -> Response:
    filename, payload = export_csv_backup()
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/csv/import")
def upload_csv_backup(payload: CsvBackupImportIn, _: dict = Depends(require_user)) -> dict[str, object]:
    try:
        imported = import_csv_backup(payload.content_base64)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"filename": payload.filename, "imported": imported}
