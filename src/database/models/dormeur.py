from uuid import UUID

from tortoise import fields
from tortoise.models import Model


class Dormeur(Model):
    """Dormeur model.

    Represents a user in the database.

    Attrs:
    """

    id: fields.Field[UUID] = fields.UUIDField(pk=True)

    discord_id: fields.Field[int] = fields.BigIntField(unique=True)


__all__ = ["Dormeur"]
