from pydantic import BaseModel


class AdminSchema(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True


class AdminResponseSchema(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class OkResponseSchema(BaseModel):
    status: str
    data: dict

    class Config:
        from_attributes = True


class ThemeSchema(BaseModel):
    title: str

    class Config:
        from_attributes = True


class ThemeResponseSchema(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class QuestionSchema(BaseModel):
    text: str
    answer: str
    hard_level: int
    theme_id: int

    class Config:
        from_attributes = True


class QuestionResponseSchema(BaseModel):
    id: int
    text: str
    answer: str
    hard_level: int
    theme_id: int

    class Config:
        from_attributes = True
