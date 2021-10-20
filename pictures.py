import uuid
from os import remove
from PIL import Image, UnidentifiedImageError


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


def save(file, filename, pic_type) -> str:
    pic: Image.Image = Image.open(file)
    if pic_type == "avatar":
        pic = pic.resize((512, 512))
        filename = "static/avatars/" + filename
    elif pic_type == "background":
        pic = pic.resize((1024, int(1024 / (pic.width / pic.height))))
        filename = "static/bg-pictures/" + filename
    pic.save(filename, "JPEG")
    return filename


def delete(pic_path) -> bool:
    remove(pic_path)
    return True


def generate_name(user_id):
    random_string = uuid.uuid4().hex
    return f"{user_id}_{random_string}.jpg"
