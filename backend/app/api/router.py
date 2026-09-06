from fastapi import APIRouter

from app.api.v1 import auth, connections, datasets, documents, evaluation, queries, schema, sessions, simulate, specialists

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1")
api_router.include_router(connections.router, prefix="/v1")
api_router.include_router(datasets.router, prefix="/v1")
api_router.include_router(documents.router, prefix="/v1")
api_router.include_router(evaluation.router, prefix="/v1")
api_router.include_router(queries.router, prefix="/v1")
api_router.include_router(sessions.router, prefix="/v1")
api_router.include_router(schema.router, prefix="/v1")
api_router.include_router(simulate.router, prefix="/v1")
api_router.include_router(specialists.router, prefix="/v1")

