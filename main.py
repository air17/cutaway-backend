from datetime import datetime, timedelta
from os import path, mkdir
from typing import List, Optional
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer

import crud
import models
import pictures
import schemas
from database import engine, SessionLocal
from settings import STATIC_PATH

models.Base.metadata.create_all(bind=engine)

description = """**Attention!** You should add authorization token to every request in headers like this:
*headers={"Authorization": "Bearer YOUR_TOKEN"}*.

You can get token making POST request to /token."""

app = FastAPI(title="Cutaway", version="alpha", description=description)

if not path.exists(STATIC_PATH):
    mkdir(STATIC_PATH)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


# FastAPI specific function which ensures closing DB connection after each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "d10cfab38898a2a79d1a546677284b8d1cf9c7f66a0ac39459784f4cb3775751"
ALGORITHM = "HS256"


async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user


def authenticate_google_user(email: str, google_auth: str):
    # TODO: Check google OpenID corresponds to the email
    if google_auth and email:
        return True
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=365)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token", response_model=schemas.Token)
async def get_access_token(user_credentials: schemas.UserAuth, db: Session = Depends(get_db)):
    """
    You can get access token here.

    - **email**: Email of the user
    - **google_auth**: Token received from Google OpenID. Can be any non-empty string for now.
    """
    if not authenticate_google_user(user_credentials.email, user_credentials.google_auth):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or google token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = crud.get_user(db, user_email=user_credentials.email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="This email is not registered",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.UserFull)
def get_users(current_user: schemas.UserFull = Depends(get_current_user)):
    return current_user


@app.get("/users", response_model=List[schemas.UserBase])
def get_users(db: Session = Depends(get_db), _=Depends(get_current_user), skip: int = 0, limit: int = 1000):
    """
    Get all the users:

    - **skip**: skip first N users
    - **limit**: limit number of users retrieved (default 1000)
    """
    return crud.get_users(db, skip, limit)


@app.get("/users/top", response_model=List[Optional[schemas.UserShort]])
def get_top_users(db: Session = Depends(get_db), _=Depends(get_current_user), limit: int = 5):
    return crud.get_top_users(db, limit)


@app.get("/users/{username}", response_model=List[Optional[schemas.UserShort]])
def get_users_by_username(username, _=Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_users_by_username(db, username)


@app.get("/user/{username}", response_model=Optional[schemas.UserFull])
def get_user_details_by_username(username: str, _=Depends(get_current_user), db: Session = Depends(get_db)):
    user = crud.get_user(db, username=username)
    if not user:
        return JSONResponse("User not found", 404)
    return user


@app.post("/users", response_model=schemas.Status, responses={409: {"model": schemas.Status}})
def create_user(user: schemas.UserBase, db: Session = Depends(get_db)):
    if crud.get_user(db, username=user.username):
        return JSONResponse(push_status(False, f"User @{user.username} already exists"), 409)
    elif crud.get_user(db, user_email=user.email):
        return JSONResponse(push_status(False, "The user with such email already exists"), 409)
    crud.create_user(db, user)
    return push_status(True, f"User @{user.username} created")


@app.post("/user/follow/{user_id}", response_model=schemas.Status, responses={409: {"model": schemas.Status}})
def follow_user(user_id: int,
                current_user: schemas.UserShort = Depends(get_current_user), db: Session = Depends(get_db)):
    follower_id = current_user.id
    if user_id == follower_id:
        return JSONResponse(push_status(False, f"You cannot follow yourself"), 409)
    if crud.make_follower(db, follower_id=follower_id, followed_id=user_id):
        return push_status(True, f"User {follower_id} followed user {user_id}")
    else:
        return JSONResponse(push_status(False, "The user is already being followed"), 409)


@app.delete("/user/unfollow/{user_id}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def unfollow_user(user_id: int,
                  current_user: schemas.UserShort = Depends(get_current_user),  db: Session = Depends(get_db)):
    follower_id = current_user.id
    if crud.delete_follower(db, follower_id=follower_id, followed_id=user_id):
        return push_status(True, f"You unfollowed user {user_id}")
    else:
        return JSONResponse(push_status(False, f"The user is not being followed"), 404)


@app.post("/files", response_model=schemas.Status, responses={400: {"model": schemas.Status},
                                                              404: {"model": schemas.Status},
                                                              422: {"model": schemas.Status}})
def add_picture(pic_type: str, file: UploadFile = File(...),
                user: schemas.UserFull = Depends(get_current_user), db: Session = Depends(get_db)):
    if pic_type in ("avatar", "background"):
        if pictures.is_valid(file.file):
            if pic_type == "avatar":
                if pictures.is_square(file.file):
                    if user.user_pic:
                        pictures.delete(user.user_pic, pic_type)
                else:
                    return JSONResponse(push_status(False, "The picture should be squared"), 422)
            elif pic_type == "background":
                if pictures.is_square(file.file) or pictures.is_landscape(file.file):
                    if user.bg_pic:
                        pictures.delete(user.bg_pic, pic_type)
                else:
                    return JSONResponse(push_status(False, "The picture should be squared or landscape"), 422)

            filename = pictures.generate_name(user.id)
            pictures.save(file.file, filename, pic_type)
            crud.add_picture_to_db(db, filename, pic_type, user.id)
            return push_status(True, f"{pic_type} changed successfully".capitalize())
        else:
            return JSONResponse(push_status(False, "The file is not a valid picture"), 400)
    else:
        return JSONResponse(push_status(False, "The pic_type should be avatar or background"), 400)


@app.patch("/user/{username}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def edit_user(username: str, user: schemas.UserEdit,
              current_user: schemas.UserBase = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.username != username:
        return JSONResponse(push_status(False, f"You cannot edit other profiles"), 403)
    if crud.edit_user(db, username, user):
        return push_status(True, f"User @{username} edited")
    else:
        return JSONResponse(push_status(False, f"User @{username} not found"), 404)


@app.delete("/user/{username}", response_model=schemas.Status,
            responses={404: {"model": schemas.Status}, 403: {"model": schemas.Status}})
def delete_user(username: str, passphrase: str = "", db: Session = Depends(get_db)):
    if passphrase == "imanicetelegrambotmadebykarchx":
        if not crud.delete_user(db, username):
            return JSONResponse(push_status(False, f"User @{username} not found"), 404)
        else:
            return push_status(True, f"User @{username} deleted")
    else:
        return JSONResponse(push_status(False, f"You are not allowed"), 403)


@app.delete("/user/{username}/link/{link}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def delete_link(username: str, link: str,
                current_user: schemas.UserShort = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.username != username:
        return JSONResponse(push_status(False, f"You cannot edit other profiles"), 403)
    if crud.delete_user_link(db, link, current_user.id):
        return push_status(True, f"{link} link of user @{username} deleted")
    else:
        return JSONResponse(push_status(False, "Link not found for user @" + username), 404)


def push_status(status: bool, message: str) -> dict:
    return {"push_status": status, "message": message}
