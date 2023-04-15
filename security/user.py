from pydantic import BaseModel, PrivateAttr
from pymongo.collection import Collection
from security.access_level import AccessLevel


class User(BaseModel):
    username: str
    email: str
    fullname: str
    disabled: bool = False
    _access_level: AccessLevel = PrivateAttr(AccessLevel.CLIENT)

    @property
    def access_level(self) -> AccessLevel:
        return self._access_level

    @access_level.setter
    def access_level(self, value: AccessLevel):
        self._access_level = value

    def dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "fullname": self.fullname,
            "disabled": self.disabled,
            "access_level": self.access_level.value,
        }


class RegisteredUser(User):
    hashed_password: str

    @classmethod
    def get(cls, collection: Collection, username: str) -> 'RegisteredUser | None':
        user = collection.find_one({"username": username})
        if user:
            return cls(**user)

    def dict(self):
        dict_val = super().dict()
        dict_val["hashed_password"] = self.hashed_password
        return dict_val