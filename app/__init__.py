
from fastapi import FastAPI

from . import models, schemas, dependencies, services, core

__version__ = "0.1.0"
__app_name__ = "Learn FastAPI"

app = FastAPI(title=__app_name__, version=__version__)