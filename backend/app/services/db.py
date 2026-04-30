from __future__ import annotations

import json
from typing import Any

import asyncpg
from fastapi import HTTPException, Request, status


async def _init_connection(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "jsonb",
        encoder=lambda value: json.dumps(value, ensure_ascii=False),
        decoder=json.loads,
        schema="pg_catalog",
        format="text",
    )
    await connection.set_type_codec(
        "json",
        encoder=lambda value: json.dumps(value, ensure_ascii=False),
        decoder=json.loads,
        schema="pg_catalog",
        format="text",
    )


async def create_db_pool(database_url: str) -> asyncpg.Pool | None:
    if not database_url:
        return None
    return await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=5,
        command_timeout=30,
        init=_init_connection,
    )


async def close_db_pool(pool: Any) -> None:
    if isinstance(pool, asyncpg.Pool):
        await pool.close()


def get_db_pool(request: Request) -> Any:
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    return pool
