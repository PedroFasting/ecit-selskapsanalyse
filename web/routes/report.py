"""
API-rute for PDF-rapportgenerering.
"""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from hr import generate_report
from web.app import get_analytics

router = APIRouter()


@router.get("/report/pdf")
async def download_report(year: Optional[int] = Query(None)):
    """
    Generer og last ned HR-rapport som PDF.
    """
    analytics = get_analytics()

    # Generer til temp-fil
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "hr_rapport.pdf")

    try:
        pdf_path = generate_report(
            analytics=analytics,
            output_path=output_path,
            year=year,
        )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename="hr_rapport.pdf",
            background=None,  # Ikke slett filen i bakgrunnen ennå
        )
    except Exception as e:
        # Rydd opp ved feil
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rmdir(tmp_dir)
        raise
