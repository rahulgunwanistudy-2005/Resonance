import secrets
from typing import Annotated

from fastapi import Depends, Header, Request

from api.app.schemas import DomainError
from api.app.services.catalog import Catalog


def catalog(request: Request) -> Catalog:
    value = request.app.state.catalog
    if not isinstance(value, Catalog):
        raise RuntimeError("Application catalog was not initialized")
    return value


CatalogDep = Annotated[Catalog, Depends(catalog)]


def require_admin(
    service: CatalogDep, authorization: Annotated[str | None, Header()] = None
) -> None:
    expected = service.settings.admin_token
    if not expected or len(expected) < 24:
        raise DomainError(
            "Admin approval is disabled until an admin token is configured", 503
        )
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not secrets.compare_digest(supplied, expected):
        raise DomainError("An admin token is required for this action", 401)
