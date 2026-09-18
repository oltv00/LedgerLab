from fastapi import FastAPI

from ledgerlab.create_login import router as login_router
from ledgerlab.create_organization import router as organization_router
from ledgerlab.create_organization_membership import router as membership_router
from ledgerlab.create_register import router as register_router
from ledgerlab.create_user import router as user_router
from ledgerlab.current_user import router as current_user_router

app = FastAPI()
app.include_router(organization_router)
app.include_router(user_router)
app.include_router(membership_router)
app.include_router(register_router)
app.include_router(login_router)
app.include_router(current_user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
