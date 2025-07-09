import random
from datetime import datetime, time, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from passlib.context import CryptContext

from typing import Annotated, Any, Union
from fastapi import FastAPI, Query, Path, Body, Cookie, Header, Response, status, Form, File, UploadFile, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import AfterValidator

from schemas import (ModelName, Image, Item, Offer, User, FilterParams, Cookies, CommonHeaders, UserIn, UserOut, BaseUser,
                     BaseUserIn, BaseUserOut, BaseUserInDB, BaseItem, PlaneItem, CarItem, FormData, Tags, Token, TokenData)
from utiles import (check_valid_id, fake_save_user, common_parameters, verify_key, verify_token, query_or_cookie_extractor,
                    get_username, fake_decode_token, fake_password_hasher, get_user, create_access_token)
from varaibles import (items, base_items, fake_items_db, data, CommonQueryParams, yield_items, fake_users_db,
                       SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM)
from exceptions import UnicornException, OwnerError

app = FastAPI()
# app = FastAPI(dependencies=[Depends(verify_token), Depends(verify_key)])
# By adding dependencies in the app itself will declare the dependencies as global.
# So it will be available in whole application.

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    """
    Custom exception handler of the class UnicorException
    :param request:
    :param exc:
    :return:
    """
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something. There goes a rainbow..."},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Override request validation exceptions
    :param request:
    :param exc:
    :return: exception along with request body that sent on API - content=jsonable_encoder({"detail": exc.errors(), "body": exc.body})
    """
    print("This is the first handler, RequestValidationError")
    return PlainTextResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """
    Override the HTTPException error handler
    :param request:
    :param exc:
    :return:
    """
    print("This is the first handler, StarletteHTTPException")
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    print(f"OMG! An HTTP error!: {repr(exc)}")
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"OMG! The client sent invalid data!: {exc}")
    return await request_validation_exception_handler(request, exc)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # PWD CONCEPT
    # user = fake_decode_token(token)
    # if not user:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid authentication credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    # return user

#     JWT CONCEPT
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[BaseUser, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

@app.get("/", summary="Root Route",
    description="This is the root route for the Fast API app", response_description="The response description")
async def root():
    """
    This is the root path for the Project. if description is given on route then it have priority rather than doc string
    here.
    :return:
    Hello World as string
    """
    return {"message": "Hello World"}

@app.get("/deprecated/route/", deprecated=True)
async def deprecated_route():
    """
    This will treat the route as deprecated.
    :return:
    """
    return True

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

@app.post("/without/tooling/user/", response_model=UserOut)
async def create_user(user: UserIn) -> Any:
    """
    This is used to understand Body as UserIn model and Output response as UserOut
    :param user:
    :return: object of UserOut
    This may have possibility of complain by mypy. Becuase UserIn and UserOut are different class.
    """
    return user

@app.post("/with/tooling/user/")
async def create_user(user: BaseUserIn) -> BaseUser:
    """
    Here this will filterout data based on class defined. Here Both classes are of same so mypy won't complain
    :param user:
    :return:
    """
    return user


@app.get("/portal")
async def get_portal(teleport: bool = False) -> Response:
    """
    This simple case is handled automatically by FastAPI because the return type annotation is the class
    (or a subclass of) Response.
    And tools will also be happy because both RedirectResponse and JSONResponse are subclasses of Response, so the
    type annotation is correct.
    :param teleport:
    :return:
    """
    if teleport:
        return RedirectResponse(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    return JSONResponse(content={"message": "Here's your interdimensional portal."})

@app.get("/teleport")
async def get_teleport() -> RedirectResponse:
    """
    You can also use a subclass of Response in the type annotation:
    :return:
    """
    return RedirectResponse(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")


# @app.get("/invalid/annotation/portal")
# async def get_portal(teleport: bool = False) -> Response | dict:
#     """
#     Invalid annotation
#     Response and dict have no same class.
#     like a union between different types where one or more of them are not valid Pydantic types,
#     this will break the code so i am commenting it out. This is for example purpose/
#     :param teleport:
#     :return:
#     """
#     if teleport:
#         return RedirectResponse(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
#     return {"message": "Here's your interdimensional portal."}

@app.get("/disable/annotation/portal", response_model=None)
async def get_portal(teleport: bool = False) -> Response | dict:
    """
    The above invalid annotation will break the code so to avoid it we can use response_model=None
    :param teleport:
    :return:
    """
    if teleport:
        return RedirectResponse(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    return {"message": "Here's your interdimensional portal."}

@app.get("/exclude/unset/items/{item_id}", response_model=Item, response_model_exclude_unset=True)
async def read_item(item_id: str):
    """
    This will omit both default and none values from the response model.
    response_model_exclude_unset=True will do the trick
    :param item_id:
    :return:
    """
    return items[item_id]

@app.get("/exclude/default/items/{item_id}", response_model=Item, response_model_exclude_defaults=True)
async def read_item(item_id: str):
    """
    This will omit default values from the response model
    response_model_exclude_defaults=True do the trick
    :param item_id:
    :return:
    """
    return items[item_id]

@app.get("/exclude/none/items/{item_id}", response_model=Item, response_model_exclude_none=True)
async def read_item(item_id: str):
    """
    This will omit none values from the response model
    response_model_exclude_none=True do the trick
    :param item_id:
    :return:
    """
    return items[item_id]

@app.get("/include/items/{item_id}/name", response_model=Item, response_model_include={"name", "description"},
)
async def read_item_name(item_id: str):
    """
    This will help you to include only specific fields on the response model.
    response_model_include will help you for this. Defined in either {} or in []
    :param item_id:
    :return:
    """
    return items[item_id]


@app.get("/include/items/{item_id}/public", response_model=Item, response_model_exclude={"tax"})
async def read_item_public_data(item_id: str):
    return items[item_id]


@app.post("/create/user/", response_model=BaseUserOut)
async def create_user(user_in: BaseUserIn):
    user_saved = fake_save_user(user_in)
    return user_saved


@app.get("/union/items/{item_id}", response_model=Union[PlaneItem, CarItem])
async def read_item(item_id: str):
    return items[item_id]


@app.get("/keyword-weights/", response_model=dict[str, float])
async def read_keyword_weights():
    return {"foo": 2.3, "bar": 3.4}

@app.post("/status/code/items/", status_code=201)
async def create_item(name: str):
    return {"name": name}

@app.post("/status/code/status/items/", status_code=status.HTTP_201_CREATED)
async def create_item(name: str):
    return {"name": name}

@app.post("/form/login/", tags=[Tags.forms])
async def login(username: Annotated[str, Form()], password: Annotated[str, Form()]):
    return {"username": username}

@app.post("/form/model/login/", tags=[Tags.forms])
async def login(form_data: Annotated[FormData, Form()]):
    return {"form_data": form_data}

@app.post("/files/", tags=[Tags.files])
async def create_file(file: Annotated[bytes, File()]):
    """
    File upload from form.
    :param file:
    :return:
    """
    return {"file_size": len(file)}

@app.post("/uploadfile/", tags=[Tags.files])
async def create_upload_file(file: UploadFile):
    """
    Using UploadFile has several advantages over bytes:
    You don't have to use File() in the default value of the parameter.
    It uses a "spooled" file:
    A file stored in memory up to a maximum size limit, and after passing this limit it will be stored in disk.
    This means that it will work well for large files like images, videos, large binaries, etc. without consuming all the memory.
    You can get metadata from the uploaded file.
    It has a file-like async interface.
    It exposes an actual Python SpooledTemporaryFile object that you can pass directly to other libraries that expect a file-like object.

    :param file:
    :return:
    """

    return {"filename": file.filename}

@app.post("/files/", tags=[Tags.files])
async def create_files(files: Annotated[list[bytes], File()]):
    """
    Multiple files from form
    :param files:
    :return:
    """
    return {"file_sizes": [len(file) for file in files]}


@app.post("/uploadfiles/", tags=[Tags.files])
async def create_upload_files(files: list[UploadFile]):
    """
    Multiple files using Upload files
    :param files:
    :return:
    """
    return {"filenames": [file.filename for file in files]}

@app.post("/form/files/", tags=[Tags.files, Tags.forms])
async def create_file(
    file: Annotated[bytes, File()],
    fileb: Annotated[UploadFile, File()],
    token: Annotated[str, Form()],
):
    return {
        "file_size": len(file),
        "token": token,
        "fileb_content_type": fileb.content_type,
    }


@app.get("/exception/items/{item_id}", tags=[Tags.exceptions])
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items[item_id]}

@app.get("/exception/items-header/{item_id}", tags=[Tags.exceptions])
async def read_item_header(item_id: str):
    if item_id not in items:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "There goes my error"},
        )
    return {"item": items[item_id]}

@app.get("/unicorns/{name}", tags=[Tags.exceptions])
async def read_unicorn(name: str):
    if name == "yolo":
        raise UnicornException(name=name)
    return {"unicorn_name": name}

@app.get("/custom/exception/items/{item_id}", tags=[Tags.exceptions])
async def read_item(item_id: int):
    if item_id == 3:
        raise HTTPException(status_code=418, detail="Nope! I don't like 3.")
    return {"item_id": item_id}

@app.patch("/patch/items/{item_id}", response_model=Item)
async def update_item(item_id: str, item: Item):
    """
    To understand http patch.
    Used for partial update.

    :param item_id:
    :param item:
    :return:
    """
    stored_item_data = items[item_id]
    stored_item_model = Item(**stored_item_data)
    update_data = item.model_dump(exclude_unset=True) # item.dict() deprecated
    updated_item = stored_item_model.model_copy(update=update_data) # item.copy() deprecated
    items[item_id] = jsonable_encoder(updated_item)
    return updated_item

@app.get("/dependency/items/", tags=[Tags.dependency])
async def dependency_read_items(commons: Annotated[dict, Depends(common_parameters)]):
    """

    :param commons: this will return a set of parameter. These are the Dependency injection
    :return:
    """
    return commons


@app.get("/dependency/users/", tags=[Tags.dependency])
async def dependency_read_users(commons: Annotated[dict, Depends(common_parameters)]):
    """
    :param commons: this will return a set of parameter. These are the Dependency injection
    :return:
    """
    return commons

@app.get("/dependency/class/items/", tags=[Tags.dependency])
async  def dependency_class_read_items(commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)]):
    response = {}
    if commons.q:
        response.update({"q": commons.q})
    items = fake_items_db[commons.skip : commons.skip + commons.limit]
    response.update({"items": items})
    return response

@app.get("/dependency/class/users/", tags=[Tags.dependency])
async  def dependency_class_read_items(commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)]):
    response = {}
    if commons.q:
        response.update({"q": commons.q})
    users = fake_items_db[commons.skip : commons.skip + commons.limit]
    response.update({"users": users})
    return response

@app.get("/dependency/dependable/items/", tags=[Tags.dependency])
async def dependency_dependable_read_query(
    query_or_default: Annotated[str, Depends(query_or_cookie_extractor)],
):
    """
    This is to understand Dependable and dependent in dependency
    :param query_or_default:
    :return:
    """
    return {"q_or_cookie": query_or_default}

@app.get("/dependency/list/items/", dependencies=[Depends(verify_token), Depends(verify_key)])
async def dependency_list_read_items():
    """
    This is to understand list of dependencies.
    Here verify_token and verify_key only applicable in this route if you want to apply globally use in the app iteself.
    :return:
    """
    return [{"item": "Foo"}, {"item": "Bar"}]

@app.get("/dependency/yield/item/{item_id}/", tags=[Tags.dependency])
def dependency_yield_get_item(item_id: str, username: Annotated[str, Depends(get_username)]):
    if item_id not in yield_items:
        raise HTTPException(status_code=404, detail="Item not found")
    item = yield_items[item_id]
    if item["owner"] != username:
        raise OwnerError(username)
    return item

@app.get("/auth/login/", tags=[Tags.auth])
async def login_auth(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    This will help you to auth using OAuth2
    :param token:
    :return:
    """
    return token

@app.post("/token", tags=[Tags.auth])
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = BaseUserInDB(**user_dict)
    hashed_password = fake_password_hasher(form_data.password)
    if not hashed_password == user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": user.username, "token_type": "bearer"}

@app.post("/jwt/token", tags=[Tags.auth])
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")



@app.get("/users/me", tags=[Tags.auth])
async def read_users_me(
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
):
    return current_user