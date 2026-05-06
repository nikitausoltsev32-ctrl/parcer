from __future__ import annotations

import csv
import io
import posixpath
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact, ContactList
from app.models.contact_import_job import ContactImportJob
from app.models.user import User

CANONICAL_FIELDS = ("name", "email", "company", "phone", "city", "website", "position", "industry")
PREVIEW_FIELDS = ("name", "email", "company", "phone", "city")
TRIAL_LEADS_LIMIT = 50
IMPORT_JOB_TTL = timedelta(hours=24)

_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "full name", "full_name", "contact", "contact name", "fio", "имя", "фио", "контакт"),
    "email": ("email", "e-mail", "mail", "почта", "эл почта", "электронная почта"),
    "company": (
        "company",
        "company name",
        "organization",
        "organisation",
        "компания",
        "организация",
        "название компании",
    ),
    "phone": ("phone", "mobile", "tel", "telephone", "телефон", "тел", "мобильный"),
    "city": ("city", "town", "location", "город", "населенный пункт"),
    "website": ("website", "site", "url", "web", "domain", "сайт", "домен"),
    "position": ("position", "title", "role", "job title", "должность", "роль"),
    "industry": ("industry", "sector", "niche", "отрасль", "сфера", "ниша"),
}


class ContactImportError(Exception):
    def __init__(self, detail: Any, status_code: int = 400) -> None:
        super().__init__(str(detail))
        self.detail = detail
        self.status_code = status_code


@dataclass
class ParsedImport:
    filename: str
    file_type: str
    headers: list[str]
    column_map: dict[str, str]
    rows: list[dict[str, Any]]
    total_rows: int
    skipped_rows: int


async def store_import_file(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> str:
    await cleanup_import_jobs(db, user_id)
    job = ContactImportJob(
        id=uuid.uuid4(),
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        payload=content,
        status="pending",
        expires_at=datetime.now(UTC) + IMPORT_JOB_TTL,
    )
    db.add(job)
    await db.commit()
    return f"import://{job.id}"


async def load_import_file(db: AsyncSession, user_id: uuid.UUID, file_url: str) -> ContactImportJob:
    if not file_url.startswith("import://"):
        raise ContactImportError("Unsupported import file URL", status_code=422)

    token = file_url.removeprefix("import://")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", token):
        raise ContactImportError("Invalid import file URL", status_code=422)

    job = await db.get(ContactImportJob, uuid.UUID(token))
    if not job:
        raise ContactImportError("Import file was not found or expired", status_code=404)
    if job.user_id != user_id:
        raise ContactImportError("Import file does not belong to current user", status_code=403)
    if job.status != "pending":
        raise ContactImportError("Import file was already consumed", status_code=409)
    if _as_aware_utc(job.expires_at) < datetime.now(UTC):
        job.status = "expired"
        await db.commit()
        raise ContactImportError("Import file expired", status_code=410)
    return job


async def preview_contact_import(
    db: AsyncSession,
    user: User,
    *,
    filename: str,
    content: bytes,
    content_type: str | None = None,
    persist_file: bool = True,
) -> dict[str, Any]:
    parsed = parse_contact_file(filename, content)
    existing_count = await _count_user_contacts(db, user.id)
    file_url = await store_import_file(db, user.id, filename, content, content_type) if persist_file else None
    return _response_payload(parsed, user, existing_count, file_url=file_url, status="preview")


async def confirm_contact_import(
    db: AsyncSession,
    user: User,
    *,
    filename: str,
    content: bytes,
    list_name: str | None = None,
) -> dict[str, Any]:
    parsed = parse_contact_file(filename, content)
    existing_count = await _count_user_contacts(db, user.id)
    _ensure_quota(user, existing_count, len(parsed.rows))

    contact_list = ContactList(
        id=uuid.uuid4(),
        user_id=user.id,
        name=(list_name or "").strip() or _default_list_name(filename),
        source="import",
        source_meta={
            "filename": filename,
            "file_type": parsed.file_type,
            "columns": parsed.column_map,
        },
        total_count=len(parsed.rows),
    )
    db.add(contact_list)
    await db.flush()

    saved = 0
    for row in parsed.rows:
        website = row.get("website")
        city = row.get("city")
        raw = {
            **row.get("raw", {}),
            "company": row.get("company"),
            "city": city,
            "import_row_number": row["row_number"],
        }
        enrichment = {"website": website, "city": city} if website or city else None
        db.add(
            Contact(
                id=uuid.uuid4(),
                user_id=user.id,
                list_id=contact_list.id,
                contact_name=row.get("name") or row.get("company"),
                email=row.get("email"),
                phone=row.get("phone"),
                position=row.get("position"),
                raw=raw,
                enrichment=enrichment,
            )
        )
        saved += 1

    await db.commit()
    return {
        **_response_payload(parsed, user, existing_count, status="imported"),
        "list_id": str(contact_list.id),
        "list_name": contact_list.name,
        "saved": saved,
    }


async def confirm_contact_import_job(
    db: AsyncSession,
    user: User,
    *,
    file_url: str,
    list_name: str | None = None,
) -> dict[str, Any]:
    job = await load_import_file(db, user.id, file_url)
    result = await confirm_contact_import(db, user, filename=job.filename, content=job.payload, list_name=list_name)
    job.status = "consumed"
    job.payload = b""
    await db.commit()
    return result


async def cleanup_import_jobs(db: AsyncSession, user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await db.execute(
        delete(ContactImportJob).where(
            ContactImportJob.user_id == user_id,
            or_(ContactImportJob.expires_at < now, ContactImportJob.status != "pending"),
        )
    )
    await db.commit()


def parse_contact_file(filename: str, content: bytes) -> ParsedImport:
    suffix = Path(filename.lower()).suffix
    if suffix in (".csv", ".tsv"):
        headers, raw_rows = _read_csv(content, delimiter="\t" if suffix == ".tsv" else None)
        file_type = suffix.removeprefix(".")
    elif suffix == ".xlsx":
        headers, raw_rows = _read_xlsx(content)
        file_type = "xlsx"
    else:
        raise ContactImportError("Only CSV, TSV and XLSX files are supported", status_code=400)

    if not headers:
        raise ContactImportError("Import file is empty or has no header row", status_code=400)

    column_map = _detect_columns(headers)
    if not any(field in column_map for field in ("name", "email", "company")):
        raise ContactImportError(
            {
                "error": "columns_not_detected",
                "message": "Could not detect name, email or company columns",
                "headers": headers,
            },
            status_code=422,
        )

    rows: list[dict[str, Any]] = []
    skipped = 0
    for index, raw in enumerate(raw_rows, start=2):
        normalized = {field: _clean(raw.get(source)) for field, source in column_map.items()}
        if not any(normalized.get(field) for field in ("name", "email", "company", "phone")):
            skipped += 1
            continue
        rows.append(
            {
                "row_number": index,
                **{field: normalized.get(field) for field in CANONICAL_FIELDS},
                "raw": {header: _clean(raw.get(header)) for header in headers},
            }
        )

    if not rows:
        raise ContactImportError("Import file has no usable contact rows", status_code=400)

    return ParsedImport(
        filename=filename,
        file_type=file_type,
        headers=headers,
        column_map=column_map,
        rows=rows,
        total_rows=len(raw_rows),
        skipped_rows=skipped,
    )


def _read_csv(content: bytes, delimiter: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
    text = _decode_text(content)
    sample = text[:4096]
    if delimiter:
        dialect = csv.excel_tab
    else:
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [_clean(h) or f"Column {i + 1}" for i, h in enumerate(reader.fieldnames or [])]
    rows = []
    for row in reader:
        normalized_row = {headers[i]: value for i, value in enumerate(row.values()) if i < len(headers)}
        if any(_clean(value) for value in normalized_row.values()):
            rows.append(normalized_row)
    return headers, rows


def _read_xlsx(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            shared_strings = _read_shared_strings(zf)
            sheet_path = _first_sheet_path(zf)
            root = ET.fromstring(zf.read(sheet_path))
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ContactImportError("Could not read XLSX file", status_code=400) from exc

    matrix: list[list[str]] = []
    for row in root.findall(f".//{_MAIN_NS}sheetData/{_MAIN_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{_MAIN_NS}c"):
            ref = cell.attrib.get("r", "")
            col_idx = _column_index(ref) if ref else len(cells)
            cells[col_idx] = _cell_value(cell, shared_strings)
        if cells:
            matrix.append([cells.get(i, "") for i in range(max(cells) + 1)])

    header_index = next((i for i, values in enumerate(matrix) if any(_clean(v) for v in values)), None)
    if header_index is None:
        return [], []

    headers = [_clean(value) or f"Column {i + 1}" for i, value in enumerate(matrix[header_index])]
    rows: list[dict[str, str]] = []
    for values in matrix[header_index + 1 :]:
        row = {header: values[i] if i < len(values) else "" for i, header in enumerate(headers)}
        if any(_clean(value) for value in row.values()):
            rows.append(row)
    return headers, rows


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    values: list[str] = []
    for item in root.findall(f"{_MAIN_NS}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{_MAIN_NS}t")))
    return values


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    sheet = workbook.find(f".//{_MAIN_NS}sheet")
    if sheet is None:
        raise KeyError("sheet")
    rel_id = sheet.attrib.get(f"{_REL_NS}id")
    if not rel_id:
        return "xl/worksheets/sheet1.xml"

    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in rels:
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib["Target"]
            return posixpath.normpath(target.lstrip("/") if target.startswith("xl/") else f"xl/{target}")
    return "xl/worksheets/sheet1.xml"


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{_MAIN_NS}t"))

    value = cell.find(f"{_MAIN_NS}v")
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "TRUE" if value.text == "1" else "FALSE"
    return value.text


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    total = 0
    for char in letters:
        total = total * 26 + (ord(char) - ord("A") + 1)
    return max(total - 1, 0)


def _detect_columns(headers: list[str]) -> dict[str, str]:
    normalized_headers = {_normalize_header(header): header for header in headers}
    mapping: dict[str, str] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            header = normalized_headers.get(_normalize_header(alias))
            if header:
                mapping[field] = header
                break
    return mapping


def _response_payload(
    parsed: ParsedImport,
    user: User,
    existing_count: int,
    *,
    status: str,
    file_url: str | None = None,
) -> dict[str, Any]:
    remaining = _remaining_quota(user, existing_count)
    duplicate_emails = _duplicate_email_count(parsed.rows)
    would_exceed = remaining is not None and len(parsed.rows) > remaining
    payload = {
        "status": status,
        "file_name": parsed.filename,
        "file_type": parsed.file_type,
        "file_url": file_url,
        "columns_detected": parsed.column_map,
        "preview": [{field: row.get(field) for field in PREVIEW_FIELDS} for row in parsed.rows[:5]],
        "stats": {
            "rows_total": parsed.total_rows,
            "valid_rows": len(parsed.rows),
            "skipped_rows": parsed.skipped_rows,
            "duplicate_emails": duplicate_emails,
            "existing_contacts": existing_count,
            "trial_limit": _lead_limit(user),
            "remaining_contacts": remaining,
            "would_exceed_trial": would_exceed,
        },
        "requires_confirmation": status == "preview",
    }
    if would_exceed:
        payload["message"] = (
            f"Trial limit exceeded: {existing_count} contacts already exist, "
            f"{len(parsed.rows)} new contacts requested, {_lead_limit(user)} allowed."
        )
    return payload


def _ensure_quota(user: User, existing_count: int, incoming_count: int) -> None:
    remaining = _remaining_quota(user, existing_count)
    if remaining is not None and incoming_count > remaining:
        raise ContactImportError(
            {
                "error": "trial_limit_exceeded",
                "message": "Trial allows 50 contacts total. Upgrade or import fewer contacts.",
                "limit": _lead_limit(user),
                "existing_contacts": existing_count,
                "incoming_contacts": incoming_count,
                "remaining_contacts": remaining,
            },
            status_code=403,
        )


def _remaining_quota(user: User, existing_count: int) -> int | None:
    if (user.plan or "trial").lower() != "trial":
        return None
    return max(_lead_limit(user) - existing_count, 0)


def _lead_limit(user: User) -> int:
    return int(user.leads_quota or TRIAL_LEADS_LIMIT)


async def _count_user_contacts(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count(Contact.id)).where(Contact.user_id == user_id))
    return int(result.scalar_one() or 0)


def _duplicate_email_count(rows: list[dict[str, Any]]) -> int:
    seen: set[str] = set()
    duplicates = 0
    for row in rows:
        email = (row.get("email") or "").lower()
        if not email:
            continue
        if email in seen:
            duplicates += 1
        seen.add(email)
    return duplicates


def _default_list_name(filename: str) -> str:
    stem = Path(filename).stem.strip()
    return stem or "Imported contacts"


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1251", errors="replace")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_header(value: str) -> str:
    value = value.lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", value)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
