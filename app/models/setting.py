"""Key/value settings storage."""
from sqlmodel import SQLModel, Field


class Setting(SQLModel, table=True):
    """Simple key/value store for application settings."""
    __tablename__ = "settings"

    key: str = Field(default=None, primary_key=True, description="Setting name")
    value: str = Field(sa_column_kwargs={"nullable": False}, description="Setting value as string")