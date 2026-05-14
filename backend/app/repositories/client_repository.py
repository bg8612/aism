from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client


class ClientRepository:
    async def list_clients(self, session: AsyncSession) -> list[Client]:
        result = await session.scalars(select(Client).order_by(Client.created_at.desc(), Client.id.desc()))
        return list(result.all())

    async def get_client(self, session: AsyncSession, *, client_id: int) -> Client | None:
        return await session.get(Client, client_id)

    async def create_client(
        self,
        session: AsyncSession,
        *,
        name: str,
        contact_name: str | None,
        contact_phone: str | None,
        contact_email: str | None,
        is_active: bool = True,
    ) -> Client:
        client = Client(
            name=name,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            is_active=is_active,
        )
        session.add(client)
        await session.flush()
        return client

    async def update_client(
        self,
        session: AsyncSession,
        *,
        client: Client,
        name: str | None = None,
        contact_name: str | None = None,
        contact_phone: str | None = None,
        contact_email: str | None = None,
        is_active: bool | None = None,
    ) -> Client:
        if name is not None:
            client.name = name
        if contact_name is not None:
            client.contact_name = contact_name
        if contact_phone is not None:
            client.contact_phone = contact_phone
        if contact_email is not None:
            client.contact_email = contact_email
        if is_active is not None:
            client.is_active = is_active
        await session.flush()
        return client

    async def deactivate_client(self, session: AsyncSession, *, client: Client) -> Client:
        client.is_active = False
        await session.flush()
        return client
