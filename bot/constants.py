"""
Loads bot configuration from YAML files.
By default, this simply loads the default
configuration located at `config-default.yml`.
If a file called `config.yml` is found in the
project directory, the default configuration
is recursively updated with any settings from
the custom configuration. Any settings left
out in the custom user configuration will stay
their default values from `config-default.yml`.
"""



import logging
import os
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


def _env_var_constructor(loader, node):
    """
    Implements a custom YAML tag for loading optional environment
    variables. If the environment variable is set, returns the
    value of it. Otherwise, returns `None`.

    Example usage in the YAML configuration:

        # Optional app configuration. Set `MY_APP_KEY` in the environment to use it.
        application:
            key: !ENV 'MY_APP_KEY'
    """

    default = None

    # Check if the node is a plain string value
    if node.id == "scalar":
        value = loader.construct_scalar(node)
        key = str(value)
    else:
        # The node value is a list
        value = loader.construct_sequence(node)

        if len(value) >= 2:
            # If we have at least two values, then we have both a key and a default value
            default = value[1]
            key = value[0]
        else:
            # Otherwise, we just have a key
            key = value[0]

    return os.getenv(key, default)


def _join_var_constructor(loader, node):
    """
    Implements a custom YAML tag for concatenating other tags in
    the document to strings. This allows for a much more DRY configuration
    file.
    """

    fields = loader.construct_sequence(node)
    return "".join(str(x) for x in fields)


yaml.SafeLoader.add_constructor("!ENV", _env_var_constructor)
yaml.SafeLoader.add_constructor("!JOIN", _join_var_constructor)

# Pointing old tag to !ENV constructor to avoid breaking existing configs
yaml.SafeLoader.add_constructor("!REQUIRED_ENV", _env_var_constructor)

with open("config.yml", encoding="UTF-8") as f:
    _CONFIG_YAML = yaml.safe_load(f)


def _recursive_update(original, new):
    """
    Helper method which implements a recursive `dict.update`
    method, used for updating the original configuration with
    configuration specified by the user.
    """

    for key, value in original.items():
        if key not in new:
            continue

        if isinstance(value, Mapping):
            if not any(isinstance(subvalue, Mapping) for subvalue in value.values()):
                original[key].update(new[key])
            _recursive_update(original[key], new[key])
        else:
            original[key] = new[key]


if Path("config.yml").exists():
    log.info("Found `config.yml` file, loading constants from it.")
    with open("config.yml", encoding="UTF-8") as f:
        user_config = yaml.safe_load(f)
    _recursive_update(_CONFIG_YAML, user_config)


def check_required_keys(keys):
    """
    Verifies that keys that are set to be required are present in the
    loaded configuration.
    """
    for key_path in keys:
        lookup = _CONFIG_YAML
        try:
            for key in key_path.split("."):
                lookup = lookup[key]
                if lookup is None:
                    raise KeyError(key)
        except KeyError:
            log.critical(
                f"A configuration for `{key_path}` is required, but was not found. "
                "Please set it in `config.yml` or setup an environment variable and try again."
            )
            raise


try:
    required_keys = _CONFIG_YAML["config"]["required_keys"]
except KeyError:
    pass
else:
    check_required_keys(required_keys)


class YAMLGetter(type):
    """
    Implements a custom metaclass used for accessing
    configuration data by simply accessing class attributes.
    Supports getting configuration from up to two levels
    of nested configuration through `section` and `subsection`.

    `section` specifies the YAML configuration section (or "key")
    in which the configuration lives, and must be set.

    `subsection` is an optional attribute specifying the section
    within the section from which configuration should be loaded.

    Example Usage:

        # config.yml
        bot:
            prefixes:
                direct_message: ''
                guild: '!'

        # config.py
        class Prefixes(metaclass=YAMLGetter):
            section = "bot"
            subsection = "prefixes"

        # Usage in Python code
        from config import Prefixes
        def get_prefix(bot, message):
            if isinstance(message.channel, PrivateChannel):
                return Prefixes.direct_message
            return Prefixes.guild

    """

    subsection = None
    sub_subsection = None

    def __getattr__(cls, name):
        name = name.lower()

        try:
            if cls.sub_subsection is not None:
                return _CONFIG_YAML[cls.section][cls.subsection][cls.sub_subsection][
                    name
                ]
            elif cls.subsection is not None:
                return _CONFIG_YAML[cls.section][cls.subsection][name]
            return _CONFIG_YAML[cls.section][name]
        except KeyError:
            return None
            # dotted_path = '.'.join(
            #     (cls.section, cls.subsection, name)
            #     if cls.subsection is not None else (cls.section, name)
            # )
            # log.critical(
            #     f"Tried accessing configuration variable at `{dotted_path}`, but it could not be found.")
            # raise

    def __getitem__(cls, name):
        return cls.__getattr__(name)

    def __iter__(cls):
        """Return generator of key: value pairs of current constants class' config values."""
        for name in cls.__annotations__:
            yield name, getattr(cls, name)


# Dataclasses
class Bot(metaclass=YAMLGetter):
    section = "bot"

    prefix: str
    token: str


class Database(metaclass=YAMLGetter):
    section = "database"

    pgsql_string: str
    mongodb_string: str


class Guilds(metaclass=YAMLGetter):
    section = "guilds"

    cc: int


class Categories(metaclass=YAMLGetter):
    section = "categories"

    verification: int
    reports: int


class Channels(metaclass=YAMLGetter):
    section = "channels"

    staff_room: int
    selfies: int
    artwork: int
    pets: int

    storage: int
    adults_chat: int


class Threads(metaclass=YAMLGetter):
    section = "threads"

    bot_questions: int


class Whitelists(metaclass=YAMLGetter):
    section = "whitelists"

    media_channels: List[int]


class Roles(metaclass=YAMLGetter):
    section = "roles"

    mod: int
    artist: int
    verified: int

    patreon_t1: int
    patreon_t2: int
    patreon_role_ids: List[int]

    adults_access: int


class People(metaclass=YAMLGetter):
    section = "people"

    bharat: int
    owner: int


class Keys(metaclass=YAMLGetter):
    section = "keys"

    openai_key: str


# Paths
BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))
