"""
API-ruter for Excel-import og database-status.
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Query, HTTPException

from hr_database import import_excel, list_imports, init_database
from hr_database.database import DEFAULT_DB_PATH, get_connection
from web.app import get_analytics

router = APIRouter()


@router.post("/import/upload")
async def upload_excel(
    file: UploadFile = File(...),
    clear_existing: bool = Query(False),
):
    """
    Importer ansattdata fra Excel-fil.
    Mottar fil via multipart form data, importerer til database.
    """
    # Valider filtype
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Kun Excel-filer (.xlsx, .xls) er støttet.",
        )

    # Lagre til temp-mappe med originalt filnavn og importer
    tmp_dir = None
    tmp_path = None
    try:
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, file.filename)
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        antall = import_excel(
            filepath=tmp_path,
            clear_existing=clear_existing,
            verbose=False,
        )

        # Opprett ny analytics-instans for å fange opp nye data
        import web.app
        web.app.analytics = type(web.app.analytics)(web.app.analytics.db_path)

        return {
            "status": "ok",
            "melding": f"Importerte {antall} rader fra {file.filename}",
            "antall_rader": antall,
            "filnavn": file.filename,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Importfeil: {str(e)}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if tmp_dir and os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)


@router.get("/import/history")
async def import_history():
    """Returner import-logg."""
    return list_imports()


@router.get("/status")
async def database_status():
    """Database-status: antall ansatte, aktive, siste import."""
    try:
        analytics = get_analytics()
        summary = analytics.employees_summary()
        imports = list_imports()
        siste_import = imports[0] if imports else None

        return {
            "database": str(DEFAULT_DB_PATH),
            "totalt_ansatte": summary["totalt"],
            "aktive_ansatte": summary["aktive"],
            "sluttede": summary["sluttede"],
            "siste_import": siste_import,
        }
    except Exception as e:
        return {
            "database": str(DEFAULT_DB_PATH),
            "feil": str(e),
            "totalt_ansatte": 0,
        }
