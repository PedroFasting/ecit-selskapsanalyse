"""
API-ruter for dashboard-system: brukere, autentisering, profiler og pins.
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from hr.database import get_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic-modeller
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    navn: str
    epost: str
    rolle: str = "bruker"


class UserUpdate(BaseModel):
    navn: Optional[str] = None
    epost: Optional[str] = None
    rolle: Optional[str] = None


class LoginRequest(BaseModel):
    user_id: int


class ProfileCreate(BaseModel):
    navn: str
    beskrivelse: str = ""
    synlig_for: str = "alle"


class ProfileUpdate(BaseModel):
    navn: Optional[str] = None
    beskrivelse: Optional[str] = None
    synlig_for: Optional[str] = None


class PinCreate(BaseModel):
    profile_id: Optional[int] = None
    metric: str
    group_by: str
    split_by: Optional[str] = None
    filter_dim: Optional[str] = None      # Bakoverkompatibel: enkelt-filter
    filter_val: Optional[str] = None      # Bakoverkompatibel: enkelt-filter
    filters: Optional[dict] = None        # Nytt: flervalg-filtre som JSON {dim: [val1, val2, ...]}
    date_as_of: Optional[str] = None
    chart_type: Optional[str] = None
    tittel: str


class PinReorder(BaseModel):
    pin_ids: list[int]


class MigrateLocalPins(BaseModel):
    pins: list[dict]


class TemplateCreate(BaseModel):
    navn: str
    metric: str
    group_by: str
    split_by: Optional[str] = None
    filters: Optional[dict] = None
    chart_type: Optional[str] = None


class TemplateMigrate(BaseModel):
    templates: list[dict]


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------

def _get_current_user(request: Request) -> Optional[dict]:
    """Hent innlogget bruker fra cookie."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, navn, epost, rolle, aktiv FROM brukere WHERE id = ? AND aktiv = 1",
            (uid,),
        ).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def _require_user(request: Request) -> dict:
    """Krev innlogget bruker. Kaster 401 hvis ikke."""
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Ikke innlogget")
    return user


def _require_admin(request: Request) -> dict:
    """Krev admin-bruker. Kaster 403 hvis ikke."""
    user = _require_user(request)
    if user["rolle"] != "admin":
        raise HTTPException(status_code=403, detail="Krever admin-tilgang")
    return user


# ---------------------------------------------------------------------------
# Auth-endepunkter
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users():
    """Liste alle aktive brukere (for login-dropdown)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, navn, epost, rolle FROM brukere WHERE aktiv = 1 ORDER BY navn"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/users", status_code=201)
async def create_user(request: Request, body: UserCreate):
    """Opprett ny bruker (kun admin)."""
    _require_admin(request)
    conn = get_connection()
    try:
        # Sjekk duplikat
        existing = conn.execute(
            "SELECT id FROM brukere WHERE epost = ?", (body.epost,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="E-post finnes allerede")

        cursor = conn.execute(
            "INSERT INTO brukere (navn, epost, rolle) VALUES (?, ?, ?)",
            (body.navn, body.epost, body.rolle),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "navn": body.navn, "epost": body.epost, "rolle": body.rolle}
    finally:
        conn.close()


@router.put("/users/{user_id}")
async def update_user(request: Request, user_id: int, body: UserUpdate):
    """Oppdater en bruker (kun admin). Kan ikke endre egen rolle."""
    current = _require_admin(request)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, navn, epost, rolle FROM brukere WHERE id = ? AND aktiv = 1",
            (user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bruker ikke funnet")

        # Ikke tillat å endre egen rolle
        if body.rolle is not None and current["id"] == user_id:
            raise HTTPException(
                status_code=400,
                detail="Du kan ikke endre din egen rolle",
            )

        # Valider rolle
        if body.rolle is not None and body.rolle not in ("admin", "bruker"):
            raise HTTPException(status_code=400, detail="Rolle må være 'admin' eller 'bruker'")

        # Sjekk duplikat e-post
        if body.epost is not None and body.epost != row["epost"]:
            dup = conn.execute(
                "SELECT id FROM brukere WHERE epost = ? AND id != ?",
                (body.epost, user_id),
            ).fetchone()
            if dup:
                raise HTTPException(status_code=409, detail="E-post finnes allerede")

        # Bygg dynamisk UPDATE
        updates = []
        params = []
        if body.navn is not None:
            if not body.navn.strip():
                raise HTTPException(status_code=400, detail="Navn kan ikke være tomt")
            updates.append("navn = ?")
            params.append(body.navn.strip())
        if body.epost is not None:
            if not body.epost.strip():
                raise HTTPException(status_code=400, detail="E-post kan ikke være tom")
            updates.append("epost = ?")
            params.append(body.epost.strip())
        if body.rolle is not None:
            updates.append("rolle = ?")
            params.append(body.rolle)

        if not updates:
            raise HTTPException(status_code=400, detail="Ingen felt å oppdatere")

        params.append(user_id)
        conn.execute(f"UPDATE brukere SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        updated = conn.execute(
            "SELECT id, navn, epost, rolle FROM brukere WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(updated)
    finally:
        conn.close()


@router.delete("/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    """Deaktiver en bruker (kun admin). Kan ikke slette seg selv."""
    current = _require_admin(request)

    if current["id"] == user_id:
        raise HTTPException(status_code=400, detail="Du kan ikke slette deg selv")

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, navn FROM brukere WHERE id = ? AND aktiv = 1",
            (user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bruker ikke funnet")

        conn.execute("UPDATE brukere SET aktiv = 0 WHERE id = ?", (user_id,))
        conn.commit()
        return {"ok": True, "deaktivert": row["navn"]}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Alderskategorier (konfigurerbare)
# ---------------------------------------------------------------------------

class AgeCategoryItem(BaseModel):
    min_alder: int
    maks_alder: int
    etikett: str


class AgeCategoryUpdate(BaseModel):
    kategorier: list[AgeCategoryItem]


@router.get("/age-categories")
async def list_age_categories():
    """Hent alle alderskategorier (sortert)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, min_alder, maks_alder, etikett, sortering "
            "FROM alderskategorier ORDER BY sortering"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/age-categories")
async def update_age_categories(request: Request, body: AgeCategoryUpdate):
    """Erstatt alle alderskategorier (kun admin). Validerer at kategoriene ikke overlapper."""
    _require_admin(request)

    # Validering
    if not body.kategorier:
        raise HTTPException(status_code=400, detail="Minst én kategori er påkrevd")

    for cat in body.kategorier:
        if cat.min_alder < 0 or cat.maks_alder < cat.min_alder:
            raise HTTPException(
                status_code=400,
                detail=f"Ugyldig intervall: {cat.min_alder}-{cat.maks_alder}"
            )
        if not cat.etikett.strip():
            raise HTTPException(status_code=400, detail="Etikett kan ikke være tom")

    # Sjekk overlapp (sortert etter min_alder)
    sorted_cats = sorted(body.kategorier, key=lambda c: c.min_alder)
    for i in range(1, len(sorted_cats)):
        if sorted_cats[i].min_alder <= sorted_cats[i - 1].maks_alder:
            raise HTTPException(
                status_code=400,
                detail=f"Kategoriene overlapper: '{sorted_cats[i - 1].etikett}' og '{sorted_cats[i].etikett}'"
            )

    conn = get_connection()
    try:
        conn.execute("DELETE FROM alderskategorier")
        for idx, cat in enumerate(sorted_cats):
            conn.execute(
                "INSERT INTO alderskategorier (min_alder, maks_alder, etikett, sortering) "
                "VALUES (?, ?, ?, ?)",
                (cat.min_alder, cat.maks_alder, cat.etikett.strip(), idx),
            )
        conn.commit()
        return {"ok": True, "antall": len(sorted_cats)}
    finally:
        conn.close()


@router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    """Enkel innlogging — velg bruker fra dropdown."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, navn, epost, rolle FROM brukere WHERE id = ? AND aktiv = 1",
            (body.user_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bruker ikke funnet")

        # Oppdater sist innlogget
        conn.execute(
            "UPDATE brukere SET sist_innlogget = ? WHERE id = ?",
            (datetime.now().isoformat(), body.user_id),
        )
        conn.commit()

        response.set_cookie(
            key="user_id",
            value=str(body.user_id),
            path="/",
            samesite="strict",
            httponly=False,  # Frontend trenger å lese denne
        )
        return dict(row)
    finally:
        conn.close()


@router.get("/auth/me")
async def get_me(request: Request):
    """Returnerer innlogget bruker basert på cookie."""
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Ikke innlogget")
    return user


@router.post("/auth/logout")
async def logout(response: Response):
    """Logg ut — fjern cookie."""
    response.delete_cookie("user_id", path="/")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Dashboard-profiler
# ---------------------------------------------------------------------------

@router.get("/dashboard/profiles")
async def list_profiles(request: Request):
    """Hent profiler synlige for innlogget bruker + 'Mine grafer' pseudo-profil."""
    user = _require_user(request)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, slug, navn, beskrivelse, opprettet_av, synlig_for, sortering "
            "FROM dashboard_profiler ORDER BY sortering, navn"
        ).fetchall()

        is_admin = user["rolle"] == "admin"

        profiles = [
            {
                "id": None,
                "slug": "",
                "navn": "Mine grafer",
                "beskrivelse": "Dine personlige grafer",
                "editable": True,
            }
        ]

        for r in rows:
            r_dict = dict(r)
            synlig = r_dict["synlig_for"]
            # Synlighetssjekk
            if synlig == "alle" or is_admin:
                visible = True
            elif synlig == "admin":
                visible = is_admin
            else:
                # Kommaseparerte bruker-IDer
                visible = str(user["id"]) in synlig.split(",")

            if visible:
                profiles.append({
                    "id": r_dict["id"],
                    "slug": r_dict["slug"],
                    "navn": r_dict["navn"],
                    "beskrivelse": r_dict["beskrivelse"],
                    "editable": is_admin,
                })

        return profiles
    finally:
        conn.close()


@router.post("/dashboard/profiles", status_code=201)
async def create_profile(request: Request, body: ProfileCreate):
    """Opprett ny profil (kun admin)."""
    user = _require_admin(request)
    conn = get_connection()
    try:
        # Generer slug
        slug = body.navn.lower().replace(" ", "-").replace("æ", "ae").replace("ø", "o").replace("å", "a")

        # Sjekk duplikat
        existing = conn.execute(
            "SELECT id FROM dashboard_profiler WHERE slug = ?", (slug,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Profil med slug '{slug}' finnes allerede")

        # Finn høyeste sortering
        max_sort = conn.execute(
            "SELECT COALESCE(MAX(sortering), -1) FROM dashboard_profiler"
        ).fetchone()[0]

        cursor = conn.execute(
            "INSERT INTO dashboard_profiler (slug, navn, beskrivelse, opprettet_av, synlig_for, sortering) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (slug, body.navn, body.beskrivelse, user["id"], body.synlig_for, max_sort + 1),
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "slug": slug,
            "navn": body.navn,
            "beskrivelse": body.beskrivelse,
        }
    finally:
        conn.close()


@router.put("/dashboard/profiles/{profile_id}")
async def update_profile(request: Request, profile_id: int, body: ProfileUpdate):
    """Oppdater profil (kun admin)."""
    _require_admin(request)
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM dashboard_profiler WHERE id = ?", (profile_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Profil ikke funnet")

        updates = []
        values = []
        if body.navn is not None:
            updates.append("navn = ?")
            values.append(body.navn)
        if body.beskrivelse is not None:
            updates.append("beskrivelse = ?")
            values.append(body.beskrivelse)
        if body.synlig_for is not None:
            updates.append("synlig_for = ?")
            values.append(body.synlig_for)

        if updates:
            values.append(profile_id)
            conn.execute(
                f"UPDATE dashboard_profiler SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            conn.commit()

        return {"ok": True}
    finally:
        conn.close()


@router.delete("/dashboard/profiles/{profile_id}")
async def delete_profile(request: Request, profile_id: int):
    """Slett profil og alle tilhørende pins (kun admin)."""
    _require_admin(request)
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM dashboard_profiler WHERE id = ?", (profile_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Profil ikke funnet")

        conn.execute("DELETE FROM dashboard_pins WHERE profil_id = ?", (profile_id,))
        conn.execute("DELETE FROM dashboard_profiler WHERE id = ?", (profile_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pins
# ---------------------------------------------------------------------------

@router.get("/dashboard/pins")
async def list_pins(request: Request, profile_id: Optional[int] = None):
    """
    Hent pins for en profil eller 'Mine grafer'.
    profile_id=None → brukerens egne pins.
    """
    user = _require_user(request)
    conn = get_connection()
    try:
        if profile_id is None:
            # Mine grafer
            rows = conn.execute(
                "SELECT id, metric, group_by, split_by, filter_dim, filter_val, "
                "filters, date_as_of, chart_type, tittel, sortering "
                "FROM dashboard_pins WHERE bruker_id = ? AND profil_id IS NULL "
                "ORDER BY sortering",
                (user["id"],),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, metric, group_by, split_by, filter_dim, filter_val, "
                "filters, date_as_of, chart_type, tittel, sortering "
                "FROM dashboard_pins WHERE profil_id = ? "
                "ORDER BY sortering",
                (profile_id,),
            ).fetchall()

        # Parse filters JSON og sørg for bakoverkompatibilitet
        result = []
        for r in rows:
            pin = dict(r)
            # Parse JSON filters hvis den finnes
            if pin.get("filters"):
                try:
                    pin["filters"] = json.loads(pin["filters"])
                except (json.JSONDecodeError, TypeError):
                    pin["filters"] = None
            # Bakoverkompatibilitet: bygg filters fra filter_dim/filter_val
            if not pin.get("filters") and pin.get("filter_dim") and pin.get("filter_val"):
                pin["filters"] = {pin["filter_dim"]: [pin["filter_val"]]}
            result.append(pin)

        return result
    finally:
        conn.close()


@router.post("/dashboard/pins", status_code=201)
async def create_pin(request: Request, body: PinCreate):
    """
    Opprett ny pin.
    profile_id=None → 'Mine grafer' for innlogget bruker.
    profile_id=N → legg til i profil N (krever admin).
    """
    user = _require_user(request)
    conn = get_connection()
    try:
        bruker_id = None
        profil_id = None

        if body.profile_id is None:
            # Mine grafer
            bruker_id = user["id"]
        else:
            # Profil-pin — krever admin
            if user["rolle"] != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Kun admin kan legge til grafer i profiler",
                )
            # Verifiser at profilen finnes
            profile = conn.execute(
                "SELECT id FROM dashboard_profiler WHERE id = ?", (body.profile_id,)
            ).fetchone()
            if not profile:
                raise HTTPException(status_code=404, detail="Profil ikke funnet")
            profil_id = body.profile_id

        # Bakoverkompatibilitet: bygg filters fra filter_dim/filter_val hvis filters mangler
        effective_filters = body.filters
        if not effective_filters and body.filter_dim and body.filter_val:
            effective_filters = {body.filter_dim: [body.filter_val]}

        # Serialiser filters til JSON for lagring
        filters_json = json.dumps(effective_filters, ensure_ascii=False, sort_keys=True) if effective_filters else None

        # Bakoverkompatibilitet: populer filter_dim/filter_val fra filters hvis det er nøyaktig 1 dimensjon med 1 verdi
        filter_dim = body.filter_dim
        filter_val = body.filter_val
        if effective_filters and not filter_dim:
            dims = list(effective_filters.items())
            if len(dims) == 1:
                k, v = dims[0]
                vals = v if isinstance(v, list) else [v]
                if len(vals) == 1:
                    filter_dim = k
                    filter_val = vals[0]

        # Duplikat-sjekk — bruk filters JSON for sammenligning
        if bruker_id:
            dup = conn.execute(
                "SELECT id FROM dashboard_pins "
                "WHERE bruker_id = ? AND profil_id IS NULL "
                "AND metric = ? AND group_by = ? "
                "AND COALESCE(split_by, '') = ? "
                "AND COALESCE(filters, '') = ? "
                "AND COALESCE(date_as_of, '') = ?",
                (bruker_id, body.metric, body.group_by,
                 body.split_by or "", filters_json or "",
                 body.date_as_of or ""),
            ).fetchone()
        else:
            dup = conn.execute(
                "SELECT id FROM dashboard_pins "
                "WHERE profil_id = ? "
                "AND metric = ? AND group_by = ? "
                "AND COALESCE(split_by, '') = ? "
                "AND COALESCE(filters, '') = ? "
                "AND COALESCE(date_as_of, '') = ?",
                (profil_id, body.metric, body.group_by,
                 body.split_by or "", filters_json or "",
                 body.date_as_of or ""),
            ).fetchone()

        if dup:
            raise HTTPException(status_code=409, detail="Denne grafen finnes allerede i valgt profil")

        # Finn høyeste sortering
        if bruker_id:
            max_sort = conn.execute(
                "SELECT COALESCE(MAX(sortering), -1) FROM dashboard_pins "
                "WHERE bruker_id = ? AND profil_id IS NULL",
                (bruker_id,),
            ).fetchone()[0]
        else:
            max_sort = conn.execute(
                "SELECT COALESCE(MAX(sortering), -1) FROM dashboard_pins WHERE profil_id = ?",
                (profil_id,),
            ).fetchone()[0]

        cursor = conn.execute(
            "INSERT INTO dashboard_pins "
            "(bruker_id, profil_id, metric, group_by, split_by, filter_dim, filter_val, "
            "filters, date_as_of, chart_type, tittel, sortering) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (bruker_id, profil_id, body.metric, body.group_by,
             body.split_by, filter_dim, filter_val,
             filters_json, body.date_as_of, body.chart_type, body.tittel, max_sort + 1),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "tittel": body.tittel}
    finally:
        conn.close()


@router.delete("/dashboard/pins/{pin_id}")
async def delete_pin(request: Request, pin_id: int):
    """
    Fjern en pin.
    Brukere kan fjerne egne 'Mine grafer'-pins.
    Admin kan fjerne pins fra alle profiler.
    """
    user = _require_user(request)
    conn = get_connection()
    try:
        pin = conn.execute(
            "SELECT id, bruker_id, profil_id FROM dashboard_pins WHERE id = ?",
            (pin_id,),
        ).fetchone()
        if not pin:
            raise HTTPException(status_code=404, detail="Pin ikke funnet")

        pin_dict = dict(pin)

        # Tilgangssjekk
        if pin_dict["profil_id"] is not None:
            # Profil-pin — krever admin
            if user["rolle"] != "admin":
                raise HTTPException(status_code=403, detail="Kun admin kan fjerne profil-pins")
        else:
            # Mine grafer — kun eier
            if pin_dict["bruker_id"] != user["id"]:
                raise HTTPException(status_code=403, detail="Du kan kun fjerne egne pins")

        conn.execute("DELETE FROM dashboard_pins WHERE id = ?", (pin_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.put("/dashboard/pins/reorder")
async def reorder_pins(request: Request, body: PinReorder):
    """Endre rekkefølge på pins."""
    _require_user(request)
    conn = get_connection()
    try:
        for idx, pin_id in enumerate(body.pin_ids):
            conn.execute(
                "UPDATE dashboard_pins SET sortering = ? WHERE id = ?",
                (idx, pin_id),
            )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/dashboard/pins/migrate-local")
async def migrate_local_pins(request: Request, body: MigrateLocalPins):
    """Migrer localStorage-pins til 'Mine grafer' for innlogget bruker."""
    user = _require_user(request)
    conn = get_connection()
    try:
        migrated = 0
        for idx, pin in enumerate(body.pins):
            metric = pin.get("metric")
            group_by = pin.get("group_by")
            tittel = pin.get("title") or pin.get("tittel") or ""

            if not metric or not group_by:
                continue

            # Håndter både gammelt (filter_dim/filter_val) og nytt (filters) format
            pin_filters = pin.get("filters")
            filters_json = json.dumps(pin_filters, ensure_ascii=False, sort_keys=True) if pin_filters else None

            # Duplikat-sjekk — bruk filters JSON for nye, filter_dim/val for gamle
            dup = conn.execute(
                "SELECT id FROM dashboard_pins "
                "WHERE bruker_id = ? AND profil_id IS NULL "
                "AND metric = ? AND group_by = ? "
                "AND COALESCE(split_by, '') = ? "
                "AND COALESCE(filters, '') = ? "
                "AND COALESCE(date_as_of, '') = ?",
                (user["id"], metric, group_by,
                 pin.get("split_by") or "", filters_json or "",
                 pin.get("date_as_of") or ""),
            ).fetchone()

            if dup:
                continue

            conn.execute(
                "INSERT INTO dashboard_pins "
                "(bruker_id, metric, group_by, split_by, filter_dim, filter_val, "
                "filters, date_as_of, chart_type, tittel, sortering) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], metric, group_by,
                 pin.get("split_by"), pin.get("filter_dim"), pin.get("filter_val"),
                 filters_json, pin.get("date_as_of"),
                 pin.get("chart_type"), tittel, idx),
            )
            migrated += 1

        conn.commit()
        return {"migrated": migrated}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analyse-maler (templates)
# ---------------------------------------------------------------------------

@router.get("/dashboard/templates")
async def list_templates(request: Request):
    """List alle maler for innlogget bruker."""
    user = _require_user(request)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, navn, metric, group_by, split_by, filters, chart_type, opprettet "
            "FROM analyse_maler WHERE bruker_id = ? ORDER BY navn",
            (user["id"],),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("filters"):
                try:
                    d["filters"] = json.loads(d["filters"])
                except (json.JSONDecodeError, TypeError):
                    d["filters"] = None
            result.append(d)
        return result
    finally:
        conn.close()


@router.post("/dashboard/templates", status_code=201)
async def create_template(request: Request, body: TemplateCreate):
    """Opprett eller overskriv en mal."""
    user = _require_user(request)
    filters_json = json.dumps(body.filters) if body.filters else None

    conn = get_connection()
    try:
        # Sjekk om mal med samme navn finnes — i så fall oppdater
        existing = conn.execute(
            "SELECT id FROM analyse_maler WHERE bruker_id = ? AND navn = ?",
            (user["id"], body.navn),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE analyse_maler SET metric=?, group_by=?, split_by=?, "
                "filters=?, chart_type=? WHERE id=?",
                (body.metric, body.group_by, body.split_by,
                 filters_json, body.chart_type, existing["id"]),
            )
            conn.commit()
            return {"id": existing["id"], "navn": body.navn, "updated": True}

        cursor = conn.execute(
            "INSERT INTO analyse_maler (bruker_id, navn, metric, group_by, split_by, filters, chart_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], body.navn, body.metric, body.group_by,
             body.split_by, filters_json, body.chart_type),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "navn": body.navn, "updated": False}
    finally:
        conn.close()


@router.delete("/dashboard/templates/{template_id}")
async def delete_template(template_id: int, request: Request):
    """Slett en mal (kun egen)."""
    user = _require_user(request)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM analyse_maler WHERE id = ? AND bruker_id = ?",
            (template_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mal ikke funnet")
        conn.execute("DELETE FROM analyse_maler WHERE id = ?", (template_id,))
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()


@router.post("/dashboard/templates/migrate")
async def migrate_local_templates(request: Request, body: TemplateMigrate):
    """Migrer maler fra localStorage til server."""
    user = _require_user(request)
    conn = get_connection()
    try:
        migrated = 0
        for tmpl in body.templates:
            navn = tmpl.get("name", "").strip()
            metric = tmpl.get("metric", "")
            group_by = tmpl.get("group_by", "")
            if not navn or not metric or not group_by:
                continue

            filters_json = json.dumps(tmpl["filters"]) if tmpl.get("filters") else None

            # Hopp over duplikater
            existing = conn.execute(
                "SELECT id FROM analyse_maler WHERE bruker_id = ? AND navn = ?",
                (user["id"], navn),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO analyse_maler (bruker_id, navn, metric, group_by, split_by, filters, chart_type) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user["id"], navn, metric, group_by,
                 tmpl.get("split_by"), filters_json, tmpl.get("chart_type")),
            )
            migrated += 1

        conn.commit()
        return {"migrated": migrated}
    finally:
        conn.close()
