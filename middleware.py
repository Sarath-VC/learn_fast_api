import time
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware



from main import app
from varaibles import origins

"""
When you add multiple middlewares using either @app.middleware() decorator or app.add_middleware()
method, each new middleware wraps the application, forming a stack. The last middleware added is the outermost, 
and the first is the innermost.
app.add_middleware(MiddlewareA)
app.add_middleware(MiddlewareB)

This results in the following execution order:

Request: MiddlewareB → MiddlewareA → route

Response: route → MiddlewareA → MiddlewareB
"""

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# This will allow cors orign
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)