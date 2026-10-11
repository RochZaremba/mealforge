from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from mealforge.core.api import ApiError
from mealforge.core.body_limit import BodyLimitMiddleware
from mealforge.core.config import Settings
from mealforge.core.database import build_engine, database_is_ready
from mealforge.core.problems import HealthResponse, Problem, ReadyResponse
from mealforge.core.request_id import RequestIdMiddleware
from mealforge.households.invitations import router as invitations_router
from mealforge.households.routes import router as household_router
from mealforge.identity.routes import router as identity_router
from mealforge.importers.preview import router as import_preview_router
from mealforge.importers.save import router as import_save_router
from mealforge.recipes.demo import router as demo_router
from mealforge.recipes.links.routes import router as recipe_links_router
from mealforge.recipes.routes import router as recipe_router


def problem_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    problem = Problem(error_code=code, message=message, request_id=request.state.request_id)
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
        headers={"X-Request-ID": problem.request_id, "Cache-Control": "no-store"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="MealForge API",
        version="0.1.0",
        description="Prywatny system wspólnej kuchni. WAVE-00: diagnostyka usługi.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.engine = engine
    application.state.settings = settings
    application.add_middleware(BodyLimitMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(identity_router)
    application.include_router(demo_router)
    application.include_router(household_router)
    application.include_router(invitations_router)
    application.include_router(recipe_router)
    application.include_router(recipe_links_router)
    application.include_router(import_preview_router)
    application.include_router(import_save_router)

    @application.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return problem_response(request, exc.status, exc.code, exc.message)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        message = "Nie znaleziono zasobu." if exc.status_code == 404 else "Żądanie odrzucone."
        return problem_response(request, exc.status_code, "HTTP_ERROR", message)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return problem_response(request, 422, "VALIDATION_ERROR", "Nieprawidłowe dane żądania.")

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, _: Exception) -> JSONResponse:
        return problem_response(request, 500, "INTERNAL_ERROR", "Wystąpił wewnętrzny błąd usługi.")

    @application.get("/health", response_model=HealthResponse, operation_id="get_health")
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get(
        "/ready",
        response_model=ReadyResponse,
        operation_id="get_readiness",
        responses={
            503: {
                "description": "Usługa nie jest gotowa.",
                "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
            }
        },
    )
    def readiness(request: Request) -> ReadyResponse | JSONResponse:
        try:
            ready = database_is_ready(engine)
        except SQLAlchemyError:
            ready = False
        if not ready:
            return problem_response(
                request,
                503,
                "SERVICE_NOT_READY",
                "Usługa nie jest jeszcze gotowa. Spróbuj ponownie później.",
            )
        return ReadyResponse()

    return application
