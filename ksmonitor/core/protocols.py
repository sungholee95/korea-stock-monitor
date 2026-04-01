from __future__ import annotations

from dataclasses import Field
from datetime import datetime
from typing import Any, ClassVar, Protocol


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class RestResponseOutput(DataclassInstance, Protocol):
    output_raw: dict[str, str] | list[dict[str, str]]
    polled_at: datetime

    @classmethod
    def descriptions_ko(cls) -> dict[str, str]:
        """Return {field_name: korean_description} from field metadata."""
        ...


class RestResponse(DataclassInstance, Protocol):
    _output_schema: ClassVar[type[RestResponseOutput]]
    output: RestResponseOutput
