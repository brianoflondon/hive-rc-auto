FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /tmp/project

# Install third-party dependencies before the application code so this layer
# stays cached when only the source changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/hive_rc_auto ./src/hive_rc_auto
RUN uv sync --frozen --no-dev --no-editable

# Compose runs `python bot.py` and `streamlit run Podping.py` from the workdir.
# Those entrypoints, pages/, and the package live next to each other.
WORKDIR /app
COPY src/ /app/
