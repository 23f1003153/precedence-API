
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow browser-based cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ENV_FILE = Path(__file__).parent / ".env"
CONFIG_FILE = Path(__file__).parent / "config.development.yaml"

# Convert string values to the required data types.
def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


@app.get("/effective-config")
def effective_config(
    set: list[str] = Query(default=[])
):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML.
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}
        config.update(yaml_config)

    # Layer 3: .env file.
    env_file = dotenv_values(ENV_FILE)

    for key, value in env_file.items():
        if value is None:
            continue

        if key == "NUM_WORKERS":
            config["workers"] = coerce("workers", value)
        elif key.startswith("APP_"):
            name = key[4:].lower()
            config[name] = coerce(name, value)

    # Layer 4: actual OS environment variables.
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            name = key[4:].lower()
            config[name] = coerce(name, value)

    # Layer 5: repeated CLI-style query overrides.
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key == "num_workers":
            key = "workers"

        config[key] = coerce(key, value)

    # Never expose the actual API key.
    config["api_key"] = "****"

    return config
