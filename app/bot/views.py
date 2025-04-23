from random import choice

from app.app import app, setup_app
from app.bot.models import AnswerStatusEnum, TelegramUserModel
from app.bot.schemas import CallbackQuery, Chat, Message
from app.bot.utils import escape_markdown_v2

setup_app()
bot = app.bot_api
app.database.connect()


async def generate_question_keyboard(
    call_or_chat: CallbackQuery | Chat,
    user: TelegramUserModel,
) -> None:
    if isinstance(call_or_chat, CallbackQuery):
        groups = await app.accessors.game_accessor.all_questions(
            call_or_chat.message.chat,
        )
        if not groups:
            await bot.send_message(
                call_or_chat.message.chat,
                "Нет вопросов в текущем раунде",
            )
            return
    else:
        groups = await app.accessors.game_accessor.all_questions(call_or_chat)
        if not groups:
            await bot.send_message(call_or_chat, "Нет вопросов в текущем раунде")
            return

    lines = []
    keyboard = []

    for idx, group in enumerate(groups, start=1):
        theme = group[0].theme
        lines.append(f"{idx}. {theme.title}")

        row = []
        for qtt in sorted(group, key=lambda x: x.question.hard_level):
            price = qtt.question.hard_level * 100

            if qtt.status == AnswerStatusEnum.ANSWERED:
                row.append(("-X-X-", "answered"))
            else:
                row.append(
                    (f"{idx}) {price}", f"btn_choice:{qtt.round_id}:{qtt.question_id}"),
                )
        keyboard.append(row)

    if isinstance(call_or_chat, CallbackQuery):
        await bot.edit_message_text(
            call_or_chat.message.chat.id,
            call_or_chat.message.message_id,
            f"Итак, начнём!\n\nВыбирает тему @{user.username}:\n" + "\n".join(lines),
            keyboard=keyboard,
        )
    else:
        await bot.send_message(
            call_or_chat,
            f"А мы продолжаем!\n\nВыбирает тему @{user.username}:\n" + "\n".join(lines),
            keyboard=keyboard,
        )


async def summarize_the_results(chat: Chat, game_id: int) -> None:
    profiles = await app.accessors.game_accessor.all_profiles(game_id)

    profiles = sorted(profiles, key=lambda p: p.score, reverse=True)
    lines = []
    for i, profile in enumerate(profiles):
        lines.append(f"@{profile.user.username} — {profile.score}")
        await app.accessors.game_accessor.summarize(profile, i == 0)

    await bot.send_message(
        chat,
        "Что ж, наша игра подходит к концу, и наш общий счёт:\n\n" + "\n".join(lines),
    )


@bot.connect_handler(commands=["start"])
async def start(message: Message) -> None:
    if message.chat.type == "private":
        await bot.send_message(
            message.chat,
            "Привет, это бот `Своя игра`, добавь меня в игру и мы сыграем вместе",
        )
        return

    if await app.accessors.game_accessor.get_active_game(message.chat) is not None:
        await bot.send_message(message.chat, "В этом чате уже есть активная игра")
        return

    master = await app.accessors.user_accessor.get_or_create(message.from_)
    await app.accessors.game_accessor.create(message.chat.id, master.id)
    await bot.send_message(
        message.chat,
        "Новая игра\n\nНет\nСвоя игра!",
        [
            [("Начать игру", "start_game")],
            [("Присоединиться", "connect_to_game")],
        ],
    )


@bot.connect_handler(commands=["stop"])
async def stop(message: Message) -> None:
    game = await app.accessors.game_accessor.get_active_game(message.chat)
    if game is None:
        return

    await app.accessors.game_accessor.complete(game)

    if game.master_id == message.from_.id:
        await bot.send_message(
            message.chat,
            "Игра завершена досрочно"
        )


@bot.connect_callback_handler("start_game")
async def start_game_handler(call: CallbackQuery) -> None:
    if (
        await app.accessors.game_accessor.get(
            call.message.chat.id,
            call.from_.id,
        )
        is None
    ):
        await bot.answer_callback_query(
            call,
            "Сори, только для ведущего!",
            show_alert=True,
        )
        return
    await bot.answer_callback_query(call)
    await app.accessors.game_accessor.next_round(call.message.chat)
    users = await app.accessors.game_accessor.all_users(call.message.chat)
    user = await app.accessors.game_accessor.set_choice_user(
        call.message.chat,
        choice(users),
    )

    await generate_question_keyboard(call, user)


@bot.connect_callback_handler("connect_to_game")
async def connect_handler(call: CallbackQuery) -> None:
    if (
        await app.accessors.game_accessor.get(
            call.message.chat.id,
            call.from_.id,
        )
        is not None
    ):
        await bot.answer_callback_query(call, "Ты же ведущий...", show_alert=True)
        return

    if not await app.accessors.game_accessor.add_player(call.from_, call.message.chat):
        await bot.answer_callback_query(call, "Ты уже участвуешь!", show_alert=True)
        return

    users = await app.accessors.game_accessor.all_users(call.message.chat)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Новая игра\n"
        "\n"
        "Нет\n"
        "Своя игра!\n"
        "\n"
        "Наши участники:"
        "\n" + "\n".join(["- @" + user.username for user in users]),
        keyboard=[
            [("Начать игру", "start_game")],
            [("Присоединиться", "connect_to_game")],
        ],
    )


@bot.connect_callback_handler()
async def choice_button(call: CallbackQuery) -> None:
    if call.data.startswith("answered"):
        await bot.answer_callback_query(call)
        return

    if call.data.startswith("btn_choice"):
        game = await app.accessors.game_accessor.get_active_game(call.message.chat)
        round_id, question_id = map(int, call.data.split(":")[1:])

        if game.choice_user_id != call.from_.id:
            await bot.answer_callback_query(
                call,
                "Не ты выбираешь тему!",
                show_alert=True,
            )
            return

        await app.accessors.game_accessor.generate_users_answer_status(
            call.message.chat,
            question_id,
            round_id,
        )
        qst = await app.accessors.game_accessor.get_question_by_id(question_id)
        await bot.edit_message_text(
            call.message.chat.id,
            call.message.message_id,
            f"Окей, игрок @{call.from_.username}, выбрал вопрос:\n\n{qst.text}",
            keyboard=[
                [("Ответить", f"btn_answer:{round_id}:{question_id}")],
            ],
        )
    elif call.data.startswith("btn_answer"):
        round_id, question_id = map(int, call.data.split(":")[1:])
        game = await app.accessors.game_accessor.get_active_game(call.message.chat)

        if game.master_id == call.from_.id:
            await bot.answer_callback_query(
                call,
                "Ты ведущий! Помни об этом",
                show_alert=True,
            )

        if await app.accessors.game_accessor.has_answer(
            call.from_.id,
            round_id,
            question_id,
        ):
            await bot.answer_callback_query(call, "Ты уже ответил!", show_alert=True)
            return

        await app.accessors.game_accessor.set_active_user(
            call.message.chat,
            call.from_,
            call.from_.id,
            question_id,
            round_id,
        )
        qst = await app.accessors.game_accessor.get_question_by_id(question_id)
        await bot.edit_message_text(
            call.message.chat.id,
            call.message.message_id,
            f"Отвечает @{call.from_.username}\n"
            "\n"
            f"{qst.text}\n"
            "\n"
            "Следующие ваше сообщение будет считаться ответом",
        )
    else:
        result, user_id, game_id, reply, question_id = call.data.split(":")
        user_id, game_id, reply, question_id = list(
            map(int, [user_id, game_id, reply, question_id])
        )
        game = await app.accessors.game_accessor.get_by_id(game_id)
        round_ = await app.accessors.game_accessor.get_current_round(
            Chat(id=game.chat_id),
        )
        user = await app.accessors.user_accessor.get_by_id(user_id)
        qst = await app.accessors.game_accessor.get_question_by_user_round(
            user_id,
            question_id,
            round_,
        )
        score = qst.hard_level * round_.base_score

        await bot.edit_message_text(
            call.message.chat.id,
            call.message.message_id,
            call.message.text,
        )

        if result == "correct":
            await app.accessors.game_accessor.add_score(user_id, game_id, score)
            await bot.send_message(
                Chat(id=game.chat_id),
                f"Иии.. ваш ответ верен!\n+ {score} очков",
                reply_to_message_id=reply,
            )
            await app.accessors.game_accessor.set_choice_user(
                Chat(id=game.chat_id), user
            )
            await app.accessors.game_accessor.set_active_user_null(
                Chat(id=game.chat_id),
            )

            if await app.accessors.game_accessor.has_questions(round_):
                await generate_question_keyboard(Chat(id=game.chat_id), user)
            else:
                next_ = await app.accessors.game_accessor.next_round(
                    Chat(id=game.chat_id),
                )
                if next_ is False:
                    await summarize_the_results(Chat(id=game.chat_id), game_id)
                    return
        else:
            await app.accessors.game_accessor.add_score(user_id, game_id, -score)
            await bot.send_message(
                Chat(id=game.chat_id),
                f"Иии.. увы, ваш ответ неверен!\n- {score} очков",
                reply_to_message_id=reply,
            )
            await app.accessors.game_accessor.set_active_user_null(
                Chat(id=game.chat_id),
            )
            if await app.accessors.game_accessor.has_user_not_answered(
                round_.id,
                question_id,
            ):
                await bot.send_message(
                    Chat(id=game.chat_id),
                    f"Может кто-то другой ответит на вопрос?:\n\n{qst.text}",
                    keyboard=[
                        [("Ответить", f"btn_answer:{round_.id}:{question_id}")],
                    ],
                )
                return

            await bot.send_message(
                Chat(id=game.chat_id),
                "Пу пу пу, никто не ответил, правильно\n"
                "\n"
                "А правильный ответ был\n"
                f"{qst.answer}",
            )

            if await app.accessors.game_accessor.has_questions(round_):
                await generate_question_keyboard(Chat(id=game.chat_id), user)
            else:
                next_ = await app.accessors.game_accessor.next_round(
                    Chat(id=game.chat_id),
                )
                if next_ is False:
                    await summarize_the_results(Chat(id=game.chat_id), game_id)
                    return

    await bot.answer_callback_query(call)


@bot.connect_handler()
async def start_game(message: Message) -> None:
    game = await app.accessors.game_accessor.get_active_game(message.chat)
    if game is None:
        return

    active_user = await app.accessors.game_accessor.get_active_user(message.chat)
    if active_user is None:
        return

    if message.from_.id == active_user.id:
        question = await app.accessors.game_accessor.get_question_by_message(message)
        round_ = await app.accessors.game_accessor.get_current_round(message.chat)

        if await app.accessors.game_accessor.is_answered(
            message.from_.id,
            question.id,
            round_.id,
        ):
            return

        await app.accessors.game_accessor.set_user_answered(
            message.from_.id,
            question.id,
            round_.id,
        )
        await app.accessors.game_accessor.set_question_answered(
            question.theme.id,
            question.id,
            round_.id,
        )

        try:
            await bot.send_message(
                Chat(id=game.master_id),
                f"Игрок @{escape_markdown_v2(message.from_.username)} выбрал вопрос:\n"
                "```\n"
                f"{question.text}"
                "```\n"
                "\n"
                "Ответ:\n"
                "```\n"
                f"{question.answer}"
                "```\n"
                "\n"
                "Ответ игрока:\n"
                "```\n"
                f"{message.text}"
                f"```",
                parse_mode="MarkdownV2",
                keyboard=[
                    [
                        (
                            "Верно",
                            f"correct:{message.from_.id}:{game.id}:{message.message_id}:{question.id}",
                        ),
                        (
                            "Неверно",
                            f"wrong:{message.from_.id}:{game.id}:{message.message_id}:{question.id}",
                        ),
                    ],
                ],
            )
        except RuntimeError as err:
            if "Forbidden: bot can't initiate conversation with a user" in str(err):
                await bot.send_message(
                    message.chat,
                    "Я не могу написать ведущему первым, "
                    "чтобы отправить на проверку ответ\n"
                    "\n"
                    "Ответ не засчитан",
                )

                await app.accessors.game_accessor.set_active_user_null(message.chat)

                if await app.accessors.game_accessor.has_questions(round_):
                    user = await app.accessors.user_accessor.get_by_id(message.from_.id)
                    await generate_question_keyboard(message.chat, user)
                else:
                    next_ = await app.accessors.game_accessor.next_round(
                        Chat(id=game.chat_id),
                    )
                    if next_ is False:
                        await summarize_the_results(message.chat, game.id)

                return

        await bot.send_message(
            message.chat,
            "Ваш ответ мы отправили ведущему на проверку",
            reply_to_message_id=message.message_id,
        )


if __name__ == "__main__":
    bot.mainloop()
