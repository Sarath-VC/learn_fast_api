from enum import Enum

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, EmailStr

from sqlmodel import Field, Session, SQLModel, create_engine, select


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

class Image(BaseModel):
    url: HttpUrl
    name: str

class Item(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Foo",
                    "description": "A very nice Item",
                    "price": 35.4,
                    "tax": 3.2,
                }
            ]
        }
    }


    name: str
    description: str | None = Field(
        default=None, title="The description of the item", max_length=300
    )
    price: float = Field(gt=0, description="The price must be greater than zero")
    tax: float | None = Field(default=None,  examples=[3.2])
    tags: list = [] #Normal list without type
    tags_set: set[str] = set()
    image: Image | None = None #Nested model "image": {
        # "url": "http://example.com/baz.jpg",
        # "name": "The Foo live"
    # }
    images: list[Image] | None = None # "images": [
    #     {
    #         "url": "http://example.com/baz.jpg",
    #         "name": "The Foo live"
    #     },
    #     {
    #         "url": "http://example.com/dave.jpg",
    #         "name": "The Baz"
    #     }
    # ]

class Offer(BaseModel):
    """
    Arbitrarily deeply nested models
    """
    name: str
    description: str | None = None
    price: float
    items: list[Item]

class User(BaseModel):
    username: str
    full_name: str | None = None

class FilterParams(BaseModel):
    model_config = {"extra": "forbid"} # This will restrict the query parameters that you want to receive.
    # Can't send random param on the route.

    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"
    tags: list[str] = [] # List of string List[str] is used before Python 3.9 List imported from typing

class Cookies(BaseModel):
    session_id: str
    fatebook_tracker: str | None = None
    googall_tracker: str | None = None

class CommonHeaders(BaseModel):
    host: str
    save_data: bool
    if_modified_since: str | None = None
    traceparent: str | None = None
    x_tag: list[str] = []

class UserIn(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str | None = None

class UserOut(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

class BaseUser(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    disabled: bool | None = None


class BaseUserIn(BaseUser):
    password: str

class BaseUserOut(BaseUser):
    pass

class BaseUserInDB(BaseUser):
    hashed_password: str

class BaseItem(BaseModel):
    description: str
    type: str

class CarItem(BaseItem):
    type: str = "car"

class PlaneItem(BaseItem):
    type: str = "plane"
    size: int

class FormData(BaseModel):
    username: str
    password: str

class Tags(Enum):
    forms = "Form"
    files = "Files"
    exceptions = "Exceptions"
    dependency = "Dependency"
    auth = "Auth"

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)
    secret_name: str