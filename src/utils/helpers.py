from fastapi import HTTPException, status


def ensure_exists(object, message) -> None:
    if object is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
     

def update_object(instance, request) -> None:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)