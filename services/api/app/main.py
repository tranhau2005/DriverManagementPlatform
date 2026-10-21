from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.errors import DomainError, domain_error_handler


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app() -> FastAPI:
    app = FastAPI(title="Driver Management Platform API")
    app.add_exception_handler(DomainError, domain_error_handler)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
