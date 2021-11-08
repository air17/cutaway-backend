from typing import List, Optional, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session
import schemas
import models


def transform_links(links: List[models.Link]) -> dict:
    result = {}
    for link in links:
        result.update({link.name: link.link})
    return result


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
        raise Exception("Search query not specified")
    user = db.execute(statement).scalar_one_or_none()
    if user:
        user.followers_number = get_followers_number(db, user.id)
        user.links = transform_links(get_user_links(db, user.id))
        user.additional_links = transform_links(get_user_links(db, user.id, additional=True))
    return user


def get_users(db: Session, skip: int = 0, limit: int = 1000) -> List[models.User]:
    statement = select(models.User).offset(skip).limit(limit)
    users = db.execute(statement).scalars().all()
    for user in users:
        user.followers_number = get_followers_number(db, user.id)
    return users


def get_top_users(db: Session, limit: int = 5) -> List[models.User]:
    statement = f"""
    SELECT user_id
    FROM followers
    GROUP BY user_id
    ORDER BY count(*) DESC
    LIMIT {limit}"""

    top_users_ids: list = db.execute(statement).scalars().all()
    top_users = []
    for user_id in top_users_ids:
        top_users.append(get_user(db, user_id=user_id))
    return top_users


def get_users_by_username(db: Session, username: str) -> List[models.User]:
    statement = select(models.User)\
                .filter(models.User.username.like(f"%{username}%"))\
                .limit(100)
    return db.execute(statement).scalars().all()


def create_user(db: Session, user: schemas.UserBase) -> models.User:
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def edit_user(db: Session, username: str, user: schemas.UserEdit):

    def add_links(link_dict: Dict[str, str], user_id: int, additional=False) -> None:
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
    updated = False  # indicates that link is updated instead of created
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


def add_picture_to_db(db: Session, filename: str, pic_type: str, user_id: int) -> bool:
    user = get_user(db, user_id=user_id)
    if pic_type == "avatar":
        user.user_pic = "static/avatars/"+filename
    elif pic_type == "background":
        user.bg_pic = "static/bg-pictures/"+filename
    else:
        raise Exception("Wrong pic_type")
    db.commit()
    return True


def get_followers_number(db, user_id) -> int:
    statement = f"SELECT count(*) FROM followers WHERE user_id={user_id}"
    return db.execute(statement).scalar_one()


def make_follower(db, follower_id, followed_id):
    statement = select(models.Followers).where(models.Followers.user_id == followed_id,
                                               models.Followers.follower_id == follower_id)
    follow = db.execute(statement).scalar_one_or_none()
    if not follow:
        new_follower = models.Followers(user_id=followed_id, follower_id=follower_id)
        db.add(new_follower)
        db.commit()
        return True
    else:
        return False


def delete_follower(db, follower_id, followed_id):
    statement = select(models.Followers).where(models.Followers.user_id == followed_id,
                                               models.Followers.follower_id == follower_id)
    follow = db.execute(statement).scalar_one_or_none()
    if follow:
        db.delete(follow)
        db.commit()
        return True
    else:
        return False
