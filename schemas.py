from typing import Optional, Dict
from pydantic import BaseModel, EmailStr


class Link(BaseModel):
    name: str
    link: str


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    username: str

    class Config:
        orm_mode = True


class UserShort(UserBase):
    id: int
    user_pic: Optional[str]
    followers_number: Optional[int]


class UserFull(UserBase):
    id: int
    google_id: Optional[str]
    about: Optional[str]
    user_pic: Optional[str]
    bg_pic: Optional[str]
    links: Optional[Dict[str, str]]
    additional_links: Optional[Dict[str, str]]


class UserEdit(BaseModel):
    email: Optional[EmailStr]
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    google_id: Optional[str]
    about: Optional[str]
    links: Optional[Dict[str, str]]
    additional_links: Optional[Dict[str, str]]


class Status(BaseModel):
    push_status: bool
    message: str
