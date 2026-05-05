from fastapi import APIRouter

from app.api.v1 import (
    auth,
    campaigns,
    chat,
    companies,
    contacts,
    inbox,
    lead_search,
    reminders,
    smtp_accounts,
    templates,
    users,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(chat.router)
router.include_router(companies.router)
router.include_router(contacts.router)
router.include_router(campaigns.router)
router.include_router(inbox.router)
router.include_router(lead_search.router)
router.include_router(reminders.router)
router.include_router(smtp_accounts.router)
router.include_router(templates.router)


@router.get("/health")
async def health():
    return {"status": "ok"}
