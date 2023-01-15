# https://github.com/tiangolo/fastapi/issues/4458S

import asyncio
from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute


class ThreadedRoute(APIRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = asyncio.Lock()

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            await self.lock.acquire()
            response: Response = await original_route_handler(request)
            self.lock.release()
            return response

        return custom_route_handler


class ThreadedRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, route_class=ThreadedRoute)
