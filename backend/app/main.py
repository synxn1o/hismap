from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Public API
    from app.api.public.entries import router as entries_router
    from app.api.public.locations import router as locations_router
    from app.api.public.authors import router as authors_router
    from app.api.public.books import router as books_router
    from app.api.public.filters import router as filters_router
    from app.api.public.search import router as search_router

    app.include_router(locations_router, prefix="/api")
    app.include_router(entries_router, prefix="/api")
    app.include_router(authors_router, prefix="/api")
    app.include_router(books_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(filters_router, prefix="/api")

    # Admin API
    from app.api.admin.auth import router as admin_auth_router
    from app.api.admin.authors import router as admin_authors_router
    from app.api.admin.books import router as admin_books_router
    from app.api.admin.entries import router as admin_entries_router
    from app.api.admin.locations import router as admin_locations_router

    app.include_router(admin_auth_router, prefix="/api")
    app.include_router(admin_entries_router, prefix="/api")
    app.include_router(admin_locations_router, prefix="/api")
    app.include_router(admin_authors_router, prefix="/api")
    app.include_router(admin_books_router, prefix="/api")

    return app


app = create_app()
