import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import Conflict, Forbidden, NotFound, ValidationError
from app.main import create_app


@pytest.fixture
def app() -> FastAPI:
    test_app = create_app()

    @test_app.get("/_test/errors/{error_name}")
    async def raise_domain_error(error_name: str) -> None:
        error_types = {
            "not-found": NotFound,
            "conflict": Conflict,
            "validation": ValidationError,
            "forbidden": Forbidden,
        }
        raise error_types[error_name]("mapped error")

    return test_app


@pytest.mark.asyncio
async def test_health_returns_ok(app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("error_name", "expected_status"),
    [
        ("not-found", 404),
        ("conflict", 409),
        ("validation", 422),
        ("forbidden", 403),
    ],
)
@pytest.mark.asyncio
async def test_domain_errors_map_to_expected_status(
    app: FastAPI,
    error_name: str,
    expected_status: int,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/_test/errors/{error_name}")

    assert response.status_code == expected_status
    assert response.json() == {"detail": "mapped error"}
