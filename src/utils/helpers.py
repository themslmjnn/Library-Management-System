from typing import Any

from pydantic import BaseModel

from src.utils.custom_exceptions import AppException


def ensure_exists(obj: Any, exception: AppException) -> None:
    if obj is None:
        raise exception


def update_object(instance: Any, request: BaseModel) -> None:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)
