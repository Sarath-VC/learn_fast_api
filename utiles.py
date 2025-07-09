from typing import Annotated
from fastapi import Depends, Cookie, Header
from fastapi.exceptions import HTTPException
from datetime import timedelta, datetime, timezone
import jwt

from schemas import BaseUserIn, BaseUserInDB, BaseUser
from exceptions import OwnerError
from context_manager import MySuperContextManager
from varaibles import fake_users_db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES



def check_valid_id(id: str):
    if not id.startswith(("isbn-", "imdb-")):
        raise ValueError('Invalid ID format, it must start with "isbn-" or "imdb-"')
    return id

def fake_password_hasher(raw_password: str):
    return "fakehashed" + raw_password


def fake_save_user(user_in: BaseUserIn):
    hashed_password = fake_password_hasher(user_in.password)
    user_in_db = BaseUserInDB(**user_in.dict(), hashed_password=hashed_password)
    print("User saved! ..not really")
    return user_in_db


async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

def query_extractor(q: str | None = None):
    return q

def query_or_cookie_extractor(q: Annotated[str, Depends(query_extractor)],
                              last_query: Annotated[str | None, Cookie()] = None,):

    """
    This is to understand dependency injection over dependency injection
    :param q: Dependency from query_extractor
    :param last_query: is a Cookie
    :return:
    """
    if not q:
        return last_query
    return q

async def verify_token(x_token: Annotated[str, Header()]):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def verify_key(x_key: Annotated[str, Header()]):
    if x_key != "fake-super-secret-key":
        raise HTTPException(status_code=400, detail="X-Key header invalid")
    return x_key

# async def get_db():
#     """
#     You could use this to create a database session and close it after finishing.
#     Only the code prior to and including the yield statement is executed before creating a response:
#     :return:
#     """
#     db = DBSession()
#     try:
#         yield db
#     finally:
#         db.close()

def get_username():
    try:
        yield "Rick"
    except OwnerError as e:
        raise HTTPException(status_code=400, detail=f"Owner error: {e}")


async def get_db():
    with MySuperContextManager() as db:
        yield db


def fake_decode_token(token):
    return BaseUser(
        username=token + "fakedecoded", email="john@example.com", full_name="John Doe"
    )

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return BaseUserInDB(**user_dict)

def fake_decode_token(token):
    # This doesn't provide any security at all
    # Check the next version
    user = get_user(fake_users_db, token)
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

