import argparse
import asyncio
import contextlib
import importlib
import inspect
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
from sqlalchemy import delete, select
from typing_extensions import TypedDict

from app.app import setup_app
from app.core.accessor import transaction
from app.core.database.database import BaseModel

app = setup_app()
app.database.connect()


class FieldsDict(TypedDict):
    pass


class FixtureItem(TypedDict):
    model: str
    fields: dict[str, Any]


MODEL_MAP: dict[str, type[BaseModel]] = {}


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def find_db_files(start_dir: str) -> list[str]:
    db_files: list[str] = []

    for root, _dirs, files in os.walk(start_dir):
        if "models.py" in files:
            db_files.append(str(Path(root) / "models.py"))

    return db_files


def import_modules(
    db_files: list[str],
    start_dir: str,
    logger: "logging.Logger",
) -> None:
    for db_file in db_files:
        rel_path: str = os.path.relpath(db_file, start_dir)
        module_name: str = "app." + rel_path.replace(os.sep, ".")[:-3]

        try:
            importlib.import_module(module_name)
        except ImportError:
            logger.exception("Ошибка импорта модуля %s", module_name)


def get_model_classes() -> dict[str, type[BaseModel]]:
    model_classes: dict[str, type[BaseModel]] = {}

    for module_name, module in sys.modules.items():
        if module_name.startswith("app."):
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseModel)
                    and obj is not BaseModel
                ):
                    model_classes[obj.__tablename__] = obj

    return model_classes


async def dump_data(
    logger: "logging.Logger",
    model_map: dict[str, type[BaseModel]],
    file_path: str,
    models: list[str] | None = None,
) -> None:

    if models is None:
        models = list(model_map.keys())

    data: list[FixtureItem] = []

    async with app.accessors.base_accessor.session() as session:
        for model_name in models:
            if model_name not in model_map:
                logger.warning("Модель %s не найдена", model_name)
                continue

            model_class: type[BaseModel] = model_map[model_name]
            result = await session.execute(select(model_class))
            objects = result.scalars().all()

            for obj in objects:
                fields: dict[str, Any] = {
                    col.name: getattr(obj, col.name) for col in obj.__table__.columns
                }
                data.append({"model": model_name, "fields": fields})

    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(
            json.dumps(data, indent=4, ensure_ascii=False, cls=DateTimeEncoder),
        )

    logger.info("Данные успешно выгружены в %s", file_path)


async def load_data(
    logger: "logging.Logger",
    model_map: dict[str, type[BaseModel]],
    file_path: str,
    *,
    clear_before: bool = False,
) -> None:

    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()

    data: list[FixtureItem] = json.loads(content)

    data_by_model: defaultdict[str, list[FixtureItem]] = defaultdict(list)

    for item in data:
        model_name: str = item["model"]
        if model_name in model_map:
            item_fields: dict[str, Any] = item["fields"]
            for key, value in item_fields.items():
                if isinstance(value, str) and value:
                    with contextlib.suppress(ValueError):
                        item_fields[key] = datetime.fromisoformat(value)
            item["fields"] = item_fields
            data_by_model[model_name].append(item)
        else:
            logger.warning("Модель %s не найдена в базе данных", model_name)

    async with transaction(app.accessors.base_accessor) as session:
        if clear_before:
            for model_class in model_map.values():
                await session.execute(delete(model_class))
            logger.info("Все таблицы очищены перед загрузкой")

        for model_name, items in data_by_model.items():
            model_cls: type[BaseModel] = model_map[model_name]
            for item in items:
                fields: dict[str, Any] = item["fields"]
                obj: BaseModel = model_cls(**fields)
                session.add(obj)

    logger.info("Данные успешно загружены из %s", file_path)


async def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Утилита для работы с данными базы",
    )
    subparsers = parser.add_subparsers(dest="command")

    dump_parser: argparse.ArgumentParser = subparsers.add_parser(
        "dump",
        help="Выгрузить данные в JSON",
    )
    dump_parser.add_argument("file_path", type=str, help="Путь к JSON-файлу")
    dump_parser.add_argument(
        "--models",
        nargs="*",
        type=str,
        help="Список моделей (по умолчанию все)",
    )

    load_parser: argparse.ArgumentParser = subparsers.add_parser(
        "load",
        help="Загрузить данные из JSON",
    )
    load_parser.add_argument("file_path", type=str, help="Путь к JSON-файлу")
    load_parser.add_argument(
        "--clear",
        action="store_true",
        help="Очистить базу перед загрузкой",
    )

    args: argparse.Namespace = parser.parse_args()

    logger = logging.getLogger(__name__)

    start_dir: str = ".."
    db_files: list[str] = find_db_files(start_dir)
    import_modules(db_files, start_dir, logger)

    model_map = get_model_classes()

    if args.command == "dump":
        models: list[str] | None = args.models or None
        await dump_data(logger, model_map, args.file_path, models)
    elif args.command == "load":
        await load_data(logger, model_map, args.file_path, clear_before=args.clear)
    else:
        logger.info("Команда не указана. Используйте --help для справки")
        parser.print_help()

    await app.database.disconnect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())