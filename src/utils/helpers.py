from src.utils.exceptions import AppException


def ensure_exists(obj, exception: AppException) -> None:
    if obj is None:
        raise exception
     

def update_object(instance, request) -> None:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)