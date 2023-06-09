from pydantic import BaseModel


class Contact(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str

    def notify(self):
        pass

    def __hash__(self):
        return hash(self.__str__())
