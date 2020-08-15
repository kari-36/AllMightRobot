# Copyright (C) 2018 - 2020 MrYacha. All rights reserved. Source code available under the AGPL.
#
# This file is part of SophieBot.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import os

from importlib import import_module
from typing import Any, Optional, TYPE_CHECKING

from sophie.utils.config import config
from sophie.utils.loader import LOADED_MODULES, LOADED_COMPONENTS
from sophie.utils.logging import log
from .db import __setup__ as setup_db, get_current_version, set_version

if TYPE_CHECKING:
    from asyncio.events import AbstractEventLoop

typed_loaded = {
    'module': LOADED_MODULES,
    'component': LOADED_COMPONENTS
}


def __setup__(loop: AbstractEventLoop) -> Any:
    loop.run_until_complete(setup_db())
    loop.run_until_complete(migrate_check())


async def migrate_check() -> Any:
    for loaded in [*LOADED_MODULES.values(), *LOADED_COMPONENTS.values()]:
        log.debug(f"Running migration check for {loaded['name']} {loaded['type']}...")
        latest_version = set_latest_version(loaded)
        if latest_version:
            await migrate(loaded, latest_version)
        await set_current_version(loaded)


def set_latest_version(loaded: dict) -> Optional[int]:
    if not os.path.exists(loaded['path'] + '/migrate'):
        log.debug(f"Not found migrate dir for {loaded['name']}, skipping.")
        return None

    version_file_path = loaded['path'] + '/migrate/version.txt'

    if not os.path.exists(version_file_path):
        log.error(f"Not found database version file for {loaded['name']}")
        exit(3)

    with open(version_file_path) as f:
        latest_version = int(f.read())

    typed_loaded[loaded['type']][loaded['name']]['latest_db_version'] = latest_version

    return latest_version


async def set_current_version(loaded: dict) -> Optional[int]:
    current_version = await get_current_version(loaded['name'], loaded['type'])
    typed_loaded[loaded['type']][loaded['name']]['current_db_version'] = current_version
    return current_version


async def migrate(loaded: dict, latest_version: int) -> Any:
    current_version = await get_current_version(loaded['name'], loaded['type'])
    # Check if loaded was never migrated before
    if current_version is None:
        log.info(f"Database version is not set for {loaded['name']} {loaded['type']}, setting it...")
        if os.path.exists(loaded['path'] + '/migrate/new.py'):
            log.debug(f"Running new.py for {loaded['name']} {loaded['type']}...")
            import_module(loaded['package_path'] + '.migrate.new')
            log.debug('...Done')
        else:
            log.debug(f"new.py not found for {loaded['name']} {loaded['type']}, skipping.")

        await set_version(loaded['name'], loaded['type'], loaded['latest_db_version'])
        log.info('...Done')
        return

    if not config.advanced.migrator:
        log.warning('Migrator is disabled, skipping...')
        return

    while current_version < latest_version:
        new_version = current_version + 1
        log.debug(f"Migrating {loaded['name']} {loaded['type']} to {new_version} version...")

        package = loaded['package_path'] + f'.migrate.{new_version}'
        log.debug(f"Importing {package}...")
        import_module(package)
        log.debug('...Done')

        await set_version(loaded['name'], loaded['type'], new_version)