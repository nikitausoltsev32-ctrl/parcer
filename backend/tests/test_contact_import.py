import io
import zipfile

from sqlalchemy import select

from app.models.contact import Contact, ContactList
from app.models.contact_import_job import ContactImportJob
from app.models.user import User
from app.services.chat.tools import _handle_import_contacts
from app.services.crm.contact_import import parse_contact_file, store_import_file


async def _auth_headers(client, email: str = "import@test.com") -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _csv_bytes(rows: int = 2) -> bytes:
    lines = ["name,email,company,phone,city"]
    for index in range(rows):
        lines.append(f"Person {index},p{index}@example.com,Company {index},+700000000{index},Kazan")
    return ("\n".join(lines) + "\n").encode()


def _minimal_xlsx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "xl/workbook.xml",
            """<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
  Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <sheetData>
  <row r="1">
   <c r="A1" t="inlineStr"><is><t>name</t></is></c>
   <c r="B1" t="inlineStr"><is><t>email</t></is></c>
   <c r="C1" t="inlineStr"><is><t>company</t></is></c>
  </row>
  <row r="2">
   <c r="A2" t="inlineStr"><is><t>Alice</t></is></c>
   <c r="B2" t="inlineStr"><is><t>alice@example.com</t></is></c>
   <c r="C2" t="inlineStr"><is><t>Acme</t></is></c>
  </row>
 </sheetData>
</worksheet>""",
        )
    return buf.getvalue()


def test_parse_contact_file_reads_xlsx():
    parsed = parse_contact_file("contacts.xlsx", _minimal_xlsx())

    assert parsed.file_type == "xlsx"
    assert parsed.column_map == {"name": "name", "email": "email", "company": "company"}
    assert parsed.rows[0]["name"] == "Alice"
    assert parsed.rows[0]["email"] == "alice@example.com"


async def test_contacts_import_preview_does_not_create_contacts(client, db_session):
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/contacts/import",
        headers=headers,
        files={"file": ("contacts.csv", _csv_bytes(), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview"
    assert data["file_url"].startswith("import://")
    assert data["columns_detected"]["email"] == "email"
    assert data["stats"]["valid_rows"] == 2
    assert len(data["preview"]) == 2

    contacts = (await db_session.execute(select(Contact))).scalars().all()
    jobs = (await db_session.execute(select(ContactImportJob))).scalars().all()
    assert contacts == []
    assert len(jobs) == 1
    assert jobs[0].status == "pending"


async def test_contacts_import_confirm_creates_contact_list_and_contacts(client, db_session):
    headers = await _auth_headers(client, "confirm-import@test.com")

    response = await client.post(
        "/api/v1/contacts/import?confirmed=true&list_name=May%20Leads",
        headers=headers,
        files={"file": ("contacts.csv", _csv_bytes(), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "imported"
    assert data["saved"] == 2
    assert data["list_name"] == "May Leads"

    contact_list = (await db_session.execute(select(ContactList))).scalar_one()
    contacts = (await db_session.execute(select(Contact).order_by(Contact.email))).scalars().all()
    assert contact_list.source == "import"
    assert contact_list.total_count == 2
    assert [c.email for c in contacts] == ["p0@example.com", "p1@example.com"]
    assert contacts[0].raw["company"] == "Company 0"


async def test_contacts_import_enforces_trial_contact_limit(client, db_session):
    headers = await _auth_headers(client, "limit-import@test.com")
    # Registration defaults to plan="dev" (unlimited) outside production; the trial cap
    # only applies to trial users, so force the trial plan to exercise it.
    user = (
        await db_session.execute(select(User).where(User.email == "limit-import@test.com"))
    ).scalar_one()
    user.plan = "trial"
    await db_session.commit()

    response = await client.post(
        "/api/v1/contacts/import?confirmed=true",
        headers=headers,
        files={"file": ("contacts.csv", _csv_bytes(51), "text/csv")},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "trial_limit_exceeded"


async def test_import_contacts_tool_previews_then_confirms(db_session):
    user = User(email="tool-import@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    file_url = await store_import_file(db_session, user.id, "contacts.csv", _csv_bytes())

    preview = await _handle_import_contacts(
        {"__db": db_session, "__user": user, "file_url": file_url, "confirmed": False}
    )
    assert preview["status"] == "preview"
    assert preview["stats"]["valid_rows"] == 2

    confirmed = await _handle_import_contacts(
        {"__db": db_session, "__user": user, "file_url": file_url, "confirmed": True, "list_name": "Chat import"}
    )
    assert confirmed["status"] == "imported"
    assert confirmed["saved"] == 2
    assert confirmed["list_name"] == "Chat import"
    job = (await db_session.execute(select(ContactImportJob))).scalar_one()
    assert job.status == "consumed"
