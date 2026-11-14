# hive-rc-auto

A bot for managing Resource Credit (RC) delegations to multiple Hive accounts.

Also a Streamlit site for Podping and Pingslurp statistics. The running site is deployed from the Docker image in this repo.

## Development

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
uv sync
cp sample.env .env   # then fill in real values
uv run pytest tests/test_rc_delegation/test_rc_delegation.py::test_mill tests/test_rc_delegation/test_rc_account_model.py
```

Run the dashboard from `src` so Streamlit finds `pages/` and the icon path:

```bash
cd src && uv run streamlit run Podping.py
```

Run the RC bot from `src`:

```bash
cd src && uv run python bot.py
```

Notebooks are optional:

```bash
uv sync --group notebooks
```

## Docker

`docker compose build` builds both services from `python:3.14-slim`. The image workdir is `/app`, with `bot.py` and `Podping.py` on the path, matching the compose commands. There is no GitHub Actions workflow in this repo; image rebuilds still come from whatever is watching the Dockerfile (Docker Hub's GitHub integration, historically).
