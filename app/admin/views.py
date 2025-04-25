from http import HTTPStatus

from aiohttp_session import new_session

from app.admin.mixins import AuthRequiredMixin
from app.admin.schemes import (
    AdminResponseSchema,
    AdminSchema,
    OkResponseSchema,
    QuestionResponseSchema,
    ThemeResponseSchema,
)
from app.admin.utils import error_json_response, json_response, validate_json
from app.app import View, app


class AdminLoginView(View):
    @validate_json(AdminSchema)
    async def post(self):
        data: AdminSchema = self.request["data"]

        admin = await app.accessors.admin_accessor.get_by_email(data.email)
        if admin is None or not admin.check_password(data.password):
            return error_json_response(
                HTTPStatus.FORBIDDEN,
                message="Incorrect email or password",
            )

        session = await new_session(request=self.request)
        session["admin_email"] = data.email

        return json_response(AdminResponseSchema.model_validate(admin))


class AdminCurrentView(AuthRequiredMixin, View):
    async def get(self):
        return json_response(AdminResponseSchema.model_validate(self.request.admin))


class ThemesView(AuthRequiredMixin, View):
    async def get(self):
        themes = await app.accessors.theme_accessor.get_all_themes()
        themes_data = [
            ThemeResponseSchema.model_validate(theme).model_dump() for theme in themes
        ]
        return json_response(
            OkResponseSchema(status="ok", data={"themes": themes_data})
        )


class QuestionsView(AuthRequiredMixin, View):
    async def get(self):
        theme_id = self.request.query.get("theme_id")
        if theme_id:
            questions = await app.accessors.theme_accessor.get_questions_by_theme(
                int(theme_id)
            )
        else:
            questions = await app.accessors.theme_accessor.get_all_questions()
        questions_data = [
            QuestionResponseSchema.model_validate(question).model_dump()
            for question in questions
        ]
        return json_response(
            OkResponseSchema(status="ok", data={"questions": questions_data})
        )