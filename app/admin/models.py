from hashlib import sha256

from sqlalchemy import Column, Integer, String

from app.core.database.sqlalchemy_base import BaseModel


class AdminModel(BaseModel):
    __tablename__ = "admin_model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=True)

    def check_password(self, password: str) -> bool:
        return self.password == sha256(password.encode("utf-8")).hexdigest()

    def set_password(self, password: str) -> None:
        self.password = sha256(password.encode("utf-8")).hexdigest()
