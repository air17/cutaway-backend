import os
import shutil
from io import BytesIO

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from database import Base


@pytest.fixture(scope="session", autouse=True)
def cleanup(request: pytest.FixtureRequest):
    # Setting up test database

    engine = create_engine(
        "sqlite:///./test.db", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Delete temporary db and static folder after finish
    def remove_test_files():
        os.remove("test.db")
        shutil.rmtree("static")
    request.addfinalizer(remove_test_files)


# Making a test client with imported app
client = TestClient(app)


# Tests
def test_create_user():
    for i in range(5):
        data = {"email": f"user{i}@example.com",
                "first_name": f"John{i}",
                "last_name": f"Doe{i}",
                "username": f"test{i}"
               }
        response = client.post("/users", json=data)
        assert response.status_code == 200
        assert response.json().get("push_status") is True
    data = {"email": f"user0@example.com",
            "first_name": f"John",
            "last_name": f"Doe",
            "username": f"noway"
            }
    response = client.post("/users", json=data)
    assert response.status_code == 409
    assert response.json().get("push_status") is False

    data["username"] = "test1"
    response = client.post("/users", json=data)
    assert response.status_code == 409


def test_edit_user():
    data = {
      "first_name": "John",
      "last_name": "Doe",
      "username": "test2_edit",
      "about": "About me",
      "links": {
        "telegram": "@test"
      },
      "additional_links": {
        "GitHub": "github.com/test"
      }
    }

    response = client.patch("/user/test2", json=data)
    assert response.json().get("push_status") is True

    response = client.patch("/user/test2_edit", json={"links": {"telegram": "@tested"}})
    assert response.json().get("push_status") is True

    response = client.patch("/user/test2", json=data)
    assert response.json().get("push_status") is False


def test_get_user_details_by_username():
    response = client.get("/user/noway")
    assert response.status_code == 404

    response = client.get("/user/test2_edit")
    assert response.json().get("first_name") == "John"
    assert response.json().get("links").get("telegram") == "@tested"


def test_delete_user():
    passphrase = "imanicetelegrambotmadebykarchx"
    response = client.delete(f"/user/test4?passphrase={passphrase}")
    assert response.json().get("push_status") is True

    response = client.delete(f"/user/test4?passphrase={passphrase}")
    assert response.json().get("push_status") is False

    response = client.delete("/user/test4?passphrase=1234")
    assert response.status_code == 403

    response = client.delete("/user/test1")
    assert response.status_code == 403


def test_get_users():
    response = client.get("/users")
    assert len(response.json()) == 4
    assert response.json()[3].get("first_name") == "John3"
    response = client.get("/users?limit=2")
    assert len(response.json()) == 2


def test_get_users_by_username():
    response = client.get("/users/edi")
    assert response.json()[0].get("first_name") == "John"


def test_delete_link():
    response = client.delete("/user/test2/link/telegram")
    assert response.json().get("push_status") is False
    assert response.status_code == 404

    response = client.delete("/user/test2_edit/link/telegram")
    assert response.json().get("push_status") is True

    response = client.delete("/user/test2_edit/link/telegram")
    assert response.json().get("push_status") is False


def test_follow():
    response = client.post("/user/follow/0?follower_id=1")
    assert response.json().get("push_status") is True

    response = client.post("/user/follow/0?follower_id=1")
    assert response.json().get("push_status") is False

    response = client.post("/user/follow/0?follower_id=0")
    assert response.json().get("push_status") is False


def test_unfollow():
    response = client.delete("/user/unfollow/0?follower_id=1")
    assert response.json().get("push_status") is True

    response = client.delete("/user/unfollow/0?follower_id=1")
    assert response.status_code == 404


def test_get_top_users():
    client.post("/user/follow/3?follower_id=0")
    client.post("/user/follow/3?follower_id=1")
    client.post("/user/follow/3?follower_id=2")
    client.post("/user/follow/0?follower_id=3")
    client.post("/user/follow/1?follower_id=3")

    response = client.get("/users/top?limit=5")
    assert len(response.json()) == 3
    assert response.json()[0].get("first_name") == "John"

    response = client.get("/users/top?limit=2")
    assert len(response.json()) == 2


class TestPicture:
    text_file = BytesIO(b"Text")
    text_file.seek(0)

    @staticmethod
    def get_test_pic(x: int, y: int) -> BytesIO:
        image_file = BytesIO()
        image_file.name = "test_pic.png"
        Image.new("RGB", (x, y)).save(image_file)
        image_file.seek(0)
        return image_file

    def test_add_picture(self):
        # Test a square valid picture as avatar
        response = client.post("/files?username=test1&pic_type=avatar",
                               files={"file": self.get_test_pic(100, 100)})
        assert response.json().get("push_status") is True

        # Test a square valid picture as avatar again to replace
        response = client.post("/files?username=test1&pic_type=avatar",
                               files={"file": self.get_test_pic(700, 700)})
        assert response.json().get("push_status") is True

        # Test a square valid picture as background
        response = client.post("/files?username=test1&pic_type=background",
                               files={"file": self.get_test_pic(100, 100)})
        assert response.json().get("push_status") is True

        # Test a valid landscape picture as avatar
        response = client.post("/files?username=test1&pic_type=avatar",
                               files={"file": self.get_test_pic(200, 100)})
        assert response.status_code == 422

        # Test a valid landscape picture as background
        response = client.post("/files?username=test1&pic_type=background",
                               files={"file": self.get_test_pic(200, 100)})
        assert response.json().get("push_status") is True

        # Test a valid portrait picture as avatar
        response = client.post("/files?username=test1&pic_type=avatar",
                               files={"file": self.get_test_pic(100, 200)})
        assert response.status_code == 422

        # Test a valid portrait picture as background
        response = client.post("/files?username=test1&pic_type=background",
                               files={"file": self.get_test_pic(100, 200)})
        assert response.status_code == 422

        # Test wrong pic_type
        response = client.post("/files?username=test1&pic_type=test",
                               files={"file": self.get_test_pic(100, 100)})
        assert response.status_code == 400

        # Test wrong user
        response = client.post("/files?username=user&pic_type=avatar",
                               files={"file": self.get_test_pic(100, 100)})
        assert response.status_code == 404

        # Test empty file as avatar
        response = client.post("/files?username=test1&pic_type=avatar",
                               files={"file": self.text_file})
        assert response.status_code == 400
