from typing import Any

from pydantic import BaseModel

from src.utils.custom_exceptions import AppException, AssigningAlreadyExistingValueError
from src.utils.exception_constants import HTTP409


def ensure_exists(obj: Any, exception: AppException) -> None:
    if obj is None:
        raise exception


def update_object(instance: Any, request: BaseModel) -> None:
    changed = False

    for field, value in request.model_dump(exclude_unset=True).items():
        if getattr(instance, field) != value:
            setattr(instance, field, value)
            changed = True

    if not changed:
        raise AssigningAlreadyExistingValueError(HTTP409.DUPLICATE_VALUE)
