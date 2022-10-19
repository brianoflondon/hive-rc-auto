FROM python:3.9.4

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy using poetry.lock* in case it doesn't exist yet
COPY ./pyproject.toml ./poetry.lock* /app/

WORKDIR  /app/

RUN poetry install --no-root --only main

COPY ./src /app/

EXPOSE 8505

ENTRYPOINT ["streamlit", "run", "hive_rc_auto/main.py", "--server.port=8505", "--server.address=0.0.0.0"]
