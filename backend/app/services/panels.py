from app.repositories.panels import delete_panels_by_type
from app.services.snapshot import create_pre_restore_backup


def complete_panels_by_type(month: str, panel_type: str) -> int:
    """청구·가족카드 전달분을 지우기 전에 복원 가능한 서버 snapshot을 남긴다."""
    create_pre_restore_backup()
    return delete_panels_by_type(month, panel_type)
