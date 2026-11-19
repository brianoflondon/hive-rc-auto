# hive-rc-auto

A bot for managing Resource Credit (RC) delegations to multiple Hive accounts.

Also a Streamlit site for Podping and Pingslurp statistics. The running site is deployed from the Docker image in this repo.

## Development

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
uv sync
cp sample.env .env   # then fill in real values
uv run pytest tests/test_rc_delegation/test_rc_delegation.py::test_mill tests/test_rc_delegation/test_rc_account_model.py
uv run ruff check
uv run ruff format
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

GitHub Actions builds `brianoflondon/hive-rc-auto` for `linux/amd64` and pushes it to Docker Hub on pushes to `main` and `develop`, on version tags, and when the workflow is run by hand. The image tag is the branch name (`main`, `develop`).

On a server, pull this repo and start the published image. Compose does not build locally. `IMAGE_TAG` in `.env` selects the tag and defaults to `main`.

```bash
git pull
docker compose pull
docker compose up -d
```

The image workdir is `/app`, with `bot.py` and `Podping.py` on the path, so the compose commands stay `python bot.py` and `streamlit run Podping.py`. `.env` is not baked into the image. Compose injects it at runtime.

`rc_bot` joins the external Docker network `repl-mongo_default`. Compose maps the replica-set names onto their Tailscale addresses, so `dave-v4vapp.tail400e5.ts.net` is `100.102.211.2` inside the container. That address is Dave itself. When Dave is the primary, the bot has to open port `27017` on the host from the Docker bridge (`172.16.0.0/12`). UFW drops that path unless it is allowed. Dave already allows this range to port `8501`. Mongo needs the same exception:

```sh
sudo ufw allow from 172.16.0.0/12 to any port 27017 proto tcp comment 'docker to local mongo'
```

Without that rule the bot reaches the other replica members, sees no primary, and exits.

To build the image on this machine instead:

```bash
docker build -t brianoflondon/hive-rc-auto:dev .
IMAGE_TAG=dev docker compose up -d
```
