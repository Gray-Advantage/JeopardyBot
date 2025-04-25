FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project
COPY pyproject.toml uv.lock ./

RUN uv sync --compile-bytecode --no-cache --no-dev
ENV PATH="/project/.venv/bin:$PATH"

COPY . .

CMD python -m app.poller.poller
