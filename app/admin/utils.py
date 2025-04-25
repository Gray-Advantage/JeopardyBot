from functools import wraps

from aiohttp.web import json_response as aiohttp_json_response
from aiohttp.web_response import Response
from pydantic import BaseModel, ValidationError


def json_response(data: BaseModel | None = None, status: str = "ok") -> Response:
    data = {} if data is None else data.model_dump()

    return aiohttp_json_response(
        data={
            "status": status,
            "data": data,
        },
    )


def error_json_response(
    http_status: int,
    status: str | None = None,
    message: str | None = None,
    data: dict | None = None,
):
    return aiohttp_json_response(
        status=http_status,
        data={
            "status": status or 400,
            "message": message,
            "data": data,
        },
    )


def validate_json(model: type[BaseModel]):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(self, *args, **kwargs):
            try:
                json_data = await self.request.json()
                validated = model(**json_data)
                self.request['data'] = validated
            except ValidationError as e:
                return error_json_response(400, message=str(e))

            return await handler(self, *args, **kwargs)

        return wrapper
    return decorator
