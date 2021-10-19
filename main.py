from typing import List, Optional

import fastapi
from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

import crud
import models
import schemas
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = fastapi.FastAPI()


# FastAPI specific function which ensures closing connection after each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/users", response_model=List[schemas.UserBase])
def get_users(db: Session = Depends(get_db)):
    return crud.get_users(db)


@app.get("/user/{email}", response_model=Optional[schemas.User])
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_email=email)
    user.links = transform_links(crud.get_user_links(db, user.id))
    user.additional_links = transform_links(crud.get_user_links(db, user.id, additional=True))
    return user


@app.post("/users", response_model=schemas.Status, responses={409: {"model": schemas.Status}})
def create_user(user: schemas.UserBase, db: Session = Depends(get_db)):
    if crud.get_user(db, username=user.username):
        return JSONResponse({"push_status": False,
                            "message": f"User @{user.username} already exists"}, 409)
    elif crud.get_user(db, user_email=user.email):
        return JSONResponse({"push_status": False,
                            "message": f"Email {user.email} already exists"}, 409)
    crud.create_user(db, user)
    return {"push_status": True, "message": f"User @{user.username} created"}


@app.patch("/user/{username}", response_model=schemas.Status, responses={404: {"model": schemas.Status}})
def edit_user(username: str, user: schemas.UserEdit, db: Session = Depends(get_db)):
    if crud.edit_user(db, username, user):
        return {"push_status": True, "message": f"User @{username} edited"}
    else:
        return JSONResponse({"push_status": False, "message": f"User @{username} not found"}, 404)


@app.delete("/user/{username}", response_model=schemas.Status,
            responses={404: {"model": schemas.Status}, 403: {"model": str}})
def delete_user(username: str, passphrase="", db: Session = Depends(get_db)):
    if passphrase == "imanicetelegrambotmadebykarchx":
        if not crud.delete_user(db, username):
            return JSONResponse({"push_status": False, "message": "User not found"}, 404)
        else:
            return {"push_status": True, "message": "User @" + username + " deleted"}
    else:
        raise fastapi.HTTPException(403, "You are not allowed to delete users")


@app.delete("/user/{username}/link/{link}", response_model=schemas.Status,
                                            responses={404: {"model": schemas.Status}})
def delete_link(username: str, link: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, username=username)
    if user:
        if crud.delete_user_link(db, link, user.id):
            return {"push_status": True, "message": link + " link of user @" + username + " deleted"}
        else:
            return JSONResponse({"push_status": False, "message": "Link not found for user @" + username}, 404)
    else:
        return JSONResponse({"push_status": False, "message": "User not found"}, 404)


def transform_links(links: List[models.Link]) -> dict:
    result = {}
    for link in links:
        result.update({link.name: link.link})
    return result
