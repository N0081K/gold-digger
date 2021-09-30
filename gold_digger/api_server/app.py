from .api_server import API
from .helpers import ContextMiddleware

app = API(
    middleware=[
        ContextMiddleware(),
    ],
)
