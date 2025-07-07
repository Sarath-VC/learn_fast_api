from enum import Enum
import random
from datetime import datetime, time, timedelta
from uuid import UUID

from typing import Annotated, Literal
from fastapi import FastAPI, Query, Path, Body, Cookie, Header
from pydantic import BaseModel, AfterValidator, Field, HttpUrl

app = FastAPI()

data = {
    "isbn-9781529046137": "The Hitchhiker's Guide to the Galaxy",
    "imdb-tt0371724": "The Hitchhiker's Guide to the Galaxy",
    "isbn-9781439512982": "Isaac Asimov: The Complete Stories, Vol. 2",
}

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

def check_valid_id(id: str):
    if not id.startswith(("isbn-", "imdb-")):
        raise ValueError('Invalid ID format, it must start with "isbn-" or "imdb-"')
    return id

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

@app.get("/")
async def root():
    """
    This is the root path for the Project.
    :return:
    Hello World as string
    """
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async  def read_item(item_id: int, needy: str, q: str or None = None, short: bool = False):
    """
    This is used for understanding path parameter in Fast API
    :param item_id: data_type int. If the type is not defined, then item can be either string or integer
    :param needy: Required. Act as query param
    :param q: data_type str. Optional parameter and if not it will be set as None Act as query param
    :param short data_type bool Optional parameter and if not it will be set as False Act as query param
    :return: item_id
    """
    item = {"item_id": item_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    """
    This is used to understand passing values to a class
    :param model_name: class ModelName
    :return:
    """
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}



@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    """
    This is used to send path of something inside the path parameter.
    :param file_path: and the last part, :path, tells it that the parameter should match any path.
    :return:
    """
    return {"file_path": file_path}

@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10):
    """
    This is used for understanding query parameter.
    The query is the set of key-value pairs that go after the ? in a URL, separated by & characters.
    Example: /items/?skip=1&item=2
    :param skip:
    :param limit:
    :return:
    """
    return fake_items_db[skip : skip + limit]

@app.get("/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str, q: str or None = None, short: bool = False):
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item

@app.post("/create/items/")
async def create_item(item: Item):
    """
    This is used to understand post method. Also Request body using class
    :param item:
    :return: item
    """
    item_dict = item.dict()
    if item.tax is not None:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict

@app.put("/update/items/{item_id}")
async def update_item(item_id: int, item: Item, q: str or None = None):
    """
    This is to understand put method.
    :param item_id: int
    :param item: class of Item
    :param q:
    :return:
    """
    result = {"item_id": item_id, **item.dict()}
    if q:
        result.update({"q": q})
    return result

@app.get("/annotated/items/")
async def annotated_items(q: Annotated[str or None, Query(min_length=3, max_length=50)] = None, pattern="^fixedquery$"):
    """
    Annotated can be used to add metadata to your parameters
    Here we are using Query() because this is a query parameter
    :param q:
    :return:
    """
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

@app.get("/annotated/default/items/")
async def annotated_default_items(q: Annotated[str, Query(min_length=3)] = "fixedquery"):
    """

    :param q: default value is fixedquery.
    Also used
    - q: Annotated[str, Query()] = "rick"
    - q: str = Query(default="rick")
    :return:
    """
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

@app.get("/query/parameter/list/items/")
async def query_param_list_items(q: Annotated[list[str] | None, Query()] = None):
    """
    Help to pass a list of data for param
    :param q: http://localhost:8000/items/?q=foo&q=bar
    :return:
    """
    query_items = {"q": q}
    return query_items

@app.get("/query/parameter/list/default/items/")
async def query_param_list_default_items(q: Annotated[list[str], Query()] = ["foo", "bar"]):
    """
    Help for list of param in query with default value.
    :param q:
    :return:
    """
    query_items = {"q": q}
    return query_items

@app.get("/query/parameter/list/list/default/items/")
async def query_param_list_list_items(q: Annotated[list, Query()] = []):
    """
    Help to pass as a list in any type
    :param q: list
    :return:
    """
    query_items = {"q": q}
    return query_items

@app.get("/annotated/metadata/items/")
async def annotated_metadata_items(q: Annotated[
        str | None,
        Query(
            title="Query string",
            description="Query string for the items to search in the database that have a good match",
            min_length=3,
            max_length=50,
            pattern="^fixedquery$",
            deprecated=True,
        ),
    ] = None,):
    """
    Annotated can be used to add metadata to your parameters
    title : for title
    description: for description
    deprecated: You have to leave it there a while because there are clients using it, but you want the docs to clearly
    show it as deprecated.
    :param q:
    :return:
    """
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

@app.get("/annotated/alias/items/")
async def annotated_alias_items(q: Annotated[str | None, Query(alias="item-query")] = None):
    """
    alias: But item-query is not a valid Python variable name.
    The closest would be item_query.
    But you still need it to be exactly item-query
    Then you can declare an alias, and that alias is what will be used to find the parameter value
    :param q:
    :return:
    """
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

@app.get("/annotated/exclude/schema/items/")
async def annotated_exclude_schema_items(hidden_query: Annotated[str | None, Query(include_in_schema=False)] = None,):
    """
    To exclude a query parameter from the generated OpenAPI schema (and thus, from the automatic documentation systems),
    set the parameter include_in_schema of Query to False:
    :param hidden_query:
    :return:
    """
    if hidden_query:
        return {"hidden_query": hidden_query}
    else:
        return {"hidden_query": "Not found"}

@app.get("/annotated/custom/validation/items/")
async def annotated_validation_items(id: Annotated[str | None, AfterValidator(check_valid_id)] = None,):
    if id:
        item = data.get(id)
    else:
        id, item = random.choice(list(data.items()))
    return {"id": id, "name": item}

@app.get("/query/param/pydantic/model/")
async def read_pydantic_model(filter_query: Annotated[FilterParams, Query()]):
    return filter_query

@app.put("/mix/body/path/query/{item_id}")
async def multi_body_param(item_id: Annotated[int, Path(title="The ID of the item to get", ge=0, le=1000)],
                           item: Item, user: User, q: str | None = None,):
    result = {
        "item_id": item_id,
        "item": item,
        "user": user
    }
    if q:
        result.update({"q": q})
    return result

@app.put("/mix/body/path/query/singular/value/{item_id}/")
async  def single_body_param(item_id: int, item: Item, user: User, importance: Annotated[int, Body()]):
    """
    Can pass other params in body other than pydantic model using Body()
    :param item_id:
    :param item:
    :param user:
    :param importance: this will treat as a body param
    :return:
    """
    return {
        "item_id": item_id,
        "item": item,
        "user": user,
        "importance": importance
    }

@app.put("/mix/body/path/query/singular/value/embed/{item_id}/")
async  def single_body_param(item_id: int, item: Annotated[Item, Body(embed=True, examples=[
                {
                    "name": "Foo",
                    "description": "A very nice Item",
                    "price": 35.4,
                    "tax": 3.2,
                }], openapi_examples={
                "normal": {
                    "summary": "A normal example",
                    "description": "A **normal** item works correctly.",
                    "value": {
                        "name": "Foo",
                        "description": "A very nice Item",
                        "price": 35.4,
                        "tax": 3.2,
                    },
                },
                "converted": {
                    "summary": "An example with converted data",
                    "description": "FastAPI can convert price `strings` to actual `numbers` automatically",
                    "value": {
                        "name": "Bar",
                        "price": "35.4",
                    },
                },
                "invalid": {
                    "summary": "Invalid data is rejected with an error",
                    "value": {
                        "name": "Baz",
                        "price": "thirty five point four",
                    },
                },
            },)]):
    """
    Can pass other params in body other than pydantic model using Body()
    examples : For json schema example (For an older version)
    openapi_examples:  for OpenApi Schema example. (For an older version)
    :param item_id:
    :param item: here we can add key for the item like { "item": { Item dict } }
    By default, FastAPI will then expect its body directly.
    But if you want it to expect a JSON with a key 'item'
    :return:
    """
    return {
        "item_id": item_id,
        "item": item
    }

@app.post("/images/multiple/")
async def create_multiple_images(images: list[Image]):
    return images

@app.post("/index-weights/")
async def create_index_weights(weights: dict[int, float]):
    """
    declare a body as a dict with keys of some type and values of some other type.
    :param weights: accept any dict as long as it has int keys with float values
    Keep in mind that JSON only supports str as keys.
    But Pydantic has automatic data conversion.
    This means that, even though your API clients can only send strings as keys, as long as those strings contain pure
    integers, Pydantic will convert them and validate them.
    And the dict you receive as weights will actually have int keys and float values.
    :return:
    """
    return weights


@app.put("/items/additional/datatypes/{item_id}")
async def read_items(
    item_id: UUID,
    start_datetime: Annotated[datetime, Body()],
    end_datetime: Annotated[datetime, Body()],
    process_after: Annotated[timedelta, Body()],
    repeat_at: Annotated[time | None, Body()] = None,
):
    """
    Date, datetime and timedelta will be in ISO8601 format
    """
    start_process = start_datetime + process_after
    duration = end_datetime - start_process
    return {
        "item_id": item_id,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "process_after": process_after,
        "repeat_at": repeat_at,
        "start_process": start_process,
        "duration": duration,
    }


@app.get("/cookies/items/")
async def cookies_items(session_id: Annotated[str | None, Cookie()] = None):
    """
    Used to understand Cookies
    :param session_id: Comes inside the cookies imported from fastapi
    :return:
    """
    return { "session_id": session_id}

@app.get("/header/items/")
async def header_items(user_agent: Annotated[str | None, Header()] = None):
    """
    This is used to understand Header parameter
    :param user_agent: Passed in Header
    But automatically convert this param to User-Agent by fastapi to support the HTTP proxies
    Can also disable this by Header(convert_underscores=False) but may affect the HTTP proxies
    :return:
    """
    return {
        "user_agent": user_agent
    }

@app.get("/duplicate/header/items/")
async def header_items(x_token: Annotated[list[str] | None, Header()] = None):
    """
    This is used to understand Duplicate Header parameter
    It is possible to receive duplicate headers. That means, the same header with multiple values.
    :param x_token: Passed in Header (X-Token)
    :return:
    """
    return {
        "X-Token Values": x_token
    }

@app.get("/cookies/model/items/")
async def cookies_model_items(cookies: Annotated[Cookies, Cookie()]):
    """
    Used to understand Cookies as model
    :param cookies: Taken from the class Cookies
    :return:
    """
    return cookies

@app.get("/header/model/items/")
async def header_model_items(headers: Annotated[CommonHeaders, Header()]):
    """
    Used to understand Header as model
    :param headers: Taken from the class CommonHeaders
    :return:
    """
    return headers

