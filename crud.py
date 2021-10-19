from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
import schemas
import models


def get_user(db: Session,
             user_email: str = None,
             username: str = None,
             google_id: str = None,
             user_id: int = None
             ) -> Optional[models.User]:

    statement = select(models.User)
    if user_email:
        statement = statement.where(models.User.email == user_email)
    elif username:
        statement = statement.where(models.User.username == username)
    elif google_id:
        statement = statement.where(models.User.google_id == google_id)
    elif user_id is not None:
        statement = statement.where(models.User.id == user_id)
    else:
        raise Exception("No search query")
    return db.execute(statement).scalar_one_or_none()


def get_users(db: Session) -> List[models.User]:
    statement = select(models.User)
    return db.execute(statement).scalars().all()


def create_user(db: Session, user: schemas.UserBase) -> models.User:
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def edit_user(db: Session, username, user: schemas.UserEdit):

    def add_links(link_dict, user_id, additional=False):
        for link_name in list(link_dict.keys()):
            create_user_link(db, link_name, link_dict[link_name], user_id, additional)

    user_model = get_user(db, username=username)
    if user_model:
        # Update non nullable variables
        if user.email:
            user_model.email = user.email
        if user.first_name:
            user_model.first_name = user.first_name
        if user.last_name:
            user_model.last_name = user.last_name
        if user.username:
            user_model.username = user.username
        # Update nullable variables
        if user.google_id is not None:
            user_model.google_id = user.google_id
        if user.about is not None:
            user_model.about = user.about
        # TODO: upload pictures
        if user.user_pic is not None:
            user_model.user_pic = user.user_pic
        if user.bg_pic is not None:
            user_model.bg_pic = user.bg_pic
        db.commit()
        # Update links
        if user.links:
            add_links(user.links, user_model.id)
        if user.additional_links:
            add_links(user.additional_links, user_model.id, additional=True)
        return True
    else:
        return None


def get_user_links(db: Session, user_id: int, additional: bool = False) -> List[models.Link]:
    statement = select(models.Link).filter(models.Link.user_id == user_id,
                                           models.Link.additional == additional)
    return db.execute(statement).scalars().all()


def create_user_link(db: Session, name: str, address: str, user_id: int, additional=False):
    updated = False # indicates that link is updated instead of created
    # Check if link title doesn't exist for the user
    all_user_links = get_user_links(db, user_id) + get_user_links(db, user_id, additional=True)
    for link in all_user_links:
        if link.name == name:
            link.name = name
            link.link = address
            link.additional = additional
            updated = True
            break
    # Create a new record if doesn't exist
    if not updated:
        new_link = models.Link(name=name, link=address, user_id=user_id, additional=additional)
        db.add(new_link)
    db.commit()

    return {"success": True, "updated": updated}


def delete_user_link(db: Session, name: str, user_id: int) -> bool:
    statement = select(models.Link).filter(models.Link.user_id == user_id,
                                           models.Link.name == name)
    link = db.execute(statement).scalar_one_or_none()
    if link:
        db.delete(link)
        db.commit()
        return True
    else:
        return False


def delete_user(db: Session, username: str) -> bool:
    user = get_user(db, username=username)
    if user:
        db.delete(user)
        db.commit()
        return True
    else:
        return False
