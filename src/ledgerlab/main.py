from fastapi import FastAPI

from ledgerlab.create_organization import router as organization_router
from ledgerlab.create_user import router as user_router

app = FastAPI()
app.include_router(organization_router)
app.include_router(user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
