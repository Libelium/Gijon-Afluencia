from models.download_model import Download, DownloadStatus
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import os
import time


def update_download_status(id: int, new_status: DownloadStatus, db: Session) -> None:

    download = db.query(Download).get(id)
    if download:
        download.status = new_status.value
        download.updated_at = func.now()
        db.commit()
    else:
        raise Exception("Download not found")


def create_download(payload: dict, db: Session) -> Download:

    download = Download(
        user_id=payload.get("user_id"),
        downloadable_type=payload.get("downloadable_type"),
        downloadable_id=payload.get("downloadable_id"),
        file_name=payload.get("file_name"),
        file_extension=payload.get("file_extension"),
        downloaded=False,
        status=payload.get("status"),
        created_at=func.now(),
        updated_at=func.now(),
    )

    db.add(download)
    db.commit()

    return download
