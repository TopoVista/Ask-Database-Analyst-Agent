from fastapi import APIRouter

from app.api.v1 import auth, connections, queries, schema, sessions, simulate

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1")
api_router.include_router(connections.router, prefix="/v1")
api_router.include_router(queries.router, prefix="/v1")
api_router.include_router(sessions.router, prefix="/v1")
api_router.include_router(schema.router, prefix="/v1")
api_router.include_router(simulate.router, prefix="/v1")

