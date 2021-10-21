import os.path
import uuid
from os import remove
from PIL import Image, UnidentifiedImageError

from settings import STATIC_PATH


def is_valid(file) -> bool:
    try:
        Image.open(file)
        return True
    except UnidentifiedImageError:
        return False


def is_square(file) -> bool:
    pic = Image.open(file)
    return pic.height == pic.width


def is_landscape(file) -> bool:
    pic = Image.open(file)
    return pic.height < pic.width


def normalize_size(pic: Image.Image, pic_type: str) -> Image.Image:
    if pic_type == "avatar":
        pic = pic.resize((512, 512))
    elif pic_type == "background":
        pic = pic.resize((1024, int(1024 / (pic.width / pic.height))))
    else:
        raise Exception
    return pic


def save(file, filename, pic_type) -> str:
    pic: Image.Image = Image.open(file)

    if pic_type == "avatar":
        filepath = STATIC_PATH+"/avatars/"
    elif pic_type == "background":
        filepath = STATIC_PATH+"/bg-pictures/"
    else:
        raise Exception

    normalize_size(pic, pic_type)

    if not os.path.exists(filepath):
        os.mkdir(filepath)

    pic.save(filepath + filename, "JPEG")

    return filepath + filename


def delete(pic_path: str, pic_type: str) -> bool:
    if pic_type == "avatar":
        path = os.path.join(STATIC_PATH, "bg-pictures", os.path.basename(pic_path))
    elif pic_type == "background":
        path = os.path.join(STATIC_PATH, "bg-pictures", os.path.basename(pic_path))
    else:
        raise Exception
    remove(path)
    return True


def generate_name(user_id):
    random_string = uuid.uuid4().hex
    return f"{user_id}_{random_string}.jpg"
