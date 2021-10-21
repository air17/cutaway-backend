from os import path, mkdir
from typing import List, Optional
from fastapi import Depends, FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import crud
import models
import pictures
import schemas
from database import engine, SessionLocal
from settings import STATIC_PATH

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

if not path.exists(STATIC_PATH):
    mkdir(STATIC_PATH)
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


# FastAPI specific function which ensures closing connection after each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/users", response_model=List[schemas.UserBase])
def get_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 1000):
    return crud.get_users(db, skip, limit)


@app.get("/users/{username}", response_model=List[schemas.UserShort])
def get_users_by_username(username, db: Session = Depends(get_db)):
    return crud.get_users_by_username(db, username)


@app.get("/user/{email}", response_model=Optional[schemas.User])
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_email=email)
    if user:
        user.links = transform_links(crud.get_user_links(db, user.id))
        user.additional_links = transform_links(crud.get_user_links(db, user.id, additional=True))
        return user
    else:
        JSONResponse("User not found", 404)


@app.post("/users", response_model=schemas.Status, responses={409: {"model": schemas.Status}})
def create_user(user: schemas.UserBase, db: Session = Depends(get_db)):
    if crud.get_user(db, username=user.username):
        return JSONResponse(push_status(False, f"User @{user.username} already exists"), 409)
    elif crud.get_user(db, user_email=user.email):
        return JSONResponse(push_status(False, "The user with such email already exists"), 409)
    crud.create_user(db, user)
    return push_status(True, f"User @{user.username} created")


@app.post("/files", response_model=schemas.Status, responses={400: {"model": schemas.Status},
                                                              404: {"model": schemas.Status},
                                                              422: {"model": schemas.Status}})
def create_picture(username: str, pic_type: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = crud.get_user(db, username=username)
    if pic_type in ("avatar", "background"):
        if user:
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
                else:
                    raise Exception("Wrong pic_type")
                filename = pictures.generate_name(user.id)
                pictures.save(file.file, filename, pic_type)
                crud.add_picture_to_db(db, filename, pic_type, user.id)
                return push_status(True, f"{pic_type} changed successfully".capitalize())
            else:
                return JSONResponse(push_status(False, "The file is not a valid picture"), 400)
        else:
            return JSONResponse(push_status(False, f"User @{username} not found"), 404)
    else:
        return JSONResponse(push_status(False, "The pic_type should be avatar or background"), 400)


@app.patch("/user/{username}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def edit_user(username: str, user: schemas.UserEdit, db: Session = Depends(get_db)):
    if crud.edit_user(db, username, user):
        return push_status(True, f"User @{username} edited")
    else:
        return JSONResponse(push_status(False, f"User @{username} not found"), 404)


@app.delete("/user/{username}", response_model=schemas.Status,
            responses={404: {"model": schemas.Status}, 403: {"model": str}})
def delete_user(username: str, passphrase="", db: Session = Depends(get_db)):
    if passphrase == "imanicetelegrambotmadebykarchx":
        if not crud.delete_user(db, username):
            return JSONResponse(push_status(False, f"User @{username} not found"), 404)
        else:
            return push_status(True, f"User @{username} deleted")
    else:
        return JSONResponse(push_status(False, f"You are not allowed"), 403)


@app.delete("/user/{username}/link/{link}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def delete_link(username: str, link: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, username=username)
    if user:
        if crud.delete_user_link(db, link, user.id):
            return push_status(True, f"{link} link of user @{username} deleted")
        else:
            return JSONResponse(push_status(False, "Link not found for user @" + username), 404)
    else:
        return JSONResponse(push_status(False, "User not found"), 404)


def transform_links(links: List[models.Link]) -> dict:
    result = {}
    for link in links:
        result.update({link.name: link.link})
    return result


def push_status(status: bool, message: str) -> dict:
    return {"push_status": status, "message": message}
