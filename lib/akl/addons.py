# -*- coding: utf-8 -*-

# AKL addon utilities

# Copyright (c) chrisism
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

#
# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
from __future__ import annotations

import argparse
import json

# AKL libraries
from akl import constants
from akl.utils import io


def create_launch_command(host: str, port: int, addon_id: str,
                          entity_type: int, entity_id: str) -> dict:
    return {
        '--cmd': 'launch',
        '--type': constants.AddonType.LAUNCHER.name,
        **_default_command_parameters(host, port, addon_id, entity_type, entity_id)
    }


def create_configure_scan_command(host: str, port: int, addon_id: str,
                                  entity_type: int, entity_id: str,
                                  platform: str = None) -> dict:
    command = {
        '--cmd': 'configure',
        '--type': constants.AddonType.SCANNER.name,
        **_default_command_parameters(host, port, addon_id, entity_type, entity_id)
    }

    if platform:
        command['--platform'] = platform

    return command


def create_scan_command(host: str, port: int, addon_id: str,
                        entity_type: int, entity_id: str) -> dict:
    return {
        '--cmd': 'scan',
        '--type': constants.AddonType.SCANNER.name,
        **_default_command_parameters(host, port, addon_id, entity_type, entity_id)
    }


def create_configure_launch_command(host: str, port: int, addon_id: str,
                                    entity_type: int, entity_id: str,
                                    system_name: str = None) -> dict:
    command = {
        '--cmd': 'configure',
        '--type': constants.AddonType.LAUNCHER.name,
        **_default_command_parameters(host, port, addon_id, entity_type, entity_id)
    }

    if system_name:
        command['--system_name'] = system_name

    return command


def create_scraper_command(host: str, port: int, addon_id: str,
                           entity_type: int, entity_id: str,
                           settings) -> dict:
    return {
        '--cmd  ': 'scrape',
        '--type': constants.AddonType.SCRAPER.name,
        '--settings': io.parse_to_json_arg(settings),
        **_default_command_parameters(host, port, addon_id, entity_type, entity_id)
    }
def create_system_scraper_command(
        host: str,
        port: int,
        addon_id: str,
        entity_type: int,
        entity_id: str,
        settings,
        platform: str,
        system_name: str,
        asset_paths: dict) -> dict:

    return {
        '--cmd': 'scrape_system',
        '--type': constants.AddonType.SCRAPER.name,
        '--settings': io.parse_to_json_arg(settings),
        '--platform': platform,
        '--system_name': system_name,
        '--asset_paths': io.parse_to_json_arg(asset_paths),
        **_default_command_parameters(
            host,
            port,
            addon_id,
            entity_type,
            entity_id
        )
    }

def _default_command_parameters(host: str, port: int, addon_id: str,
                                entity_type: int, entity_id: str) -> dict:
    return {
        '--server_host': host,
        '--server_port': port,
        '--akl_addon_id': addon_id,
        '--entity_type': entity_type,
        '--entity_id': entity_id
    }


###############################################################
# CLIENT OBJECTS
###############################################################
class AklAddonArguments(object):

    LAUNCH = 0
    SCAN = 1
    SCRAPE = 2
    CONFIGURE_LAUNCHER = 3
    CONFIGURE_SCANNER = 4
    SCRAPE_SYSTEM = 5

    def __init__(self, addon_name: str):
        self.addon_name = addon_name

        self.parser = argparse.ArgumentParser(prog=addon_name)
        self.parser.add_argument('--cmd', help="Command to execute", choices=['launch', 'scan', 'scrape', 'scrape_system', 'configure'])
        self.parser.add_argument('--type', help="Plugin type", choices=['LAUNCHER', 'SCANNER', 'SCRAPER'],
                                 default=constants.AddonType.LAUNCHER.name)
        self.parser.add_argument('--server_host', type=str, help="Host")
        self.parser.add_argument('--server_port', type=int, help="Port")
        self.parser.add_argument('--rom_id', type=str, help="ROM ID")
        self.parser.add_argument('--source_id', type=str, help="Source ID")
        self.parser.add_argument('--entity_id', type=str, help="Entity ID")
        self.parser.add_argument('--entity_type', type=int, help="Entity Type (ROM|ROMCOLLECTION|SOURCE)")
        self.parser.add_argument('--akl_addon_id', type=str, help="Addon configuration ID")
        self.parser.add_argument('--settings', type=json.loads, help="Specific run setting")
        self.parser.add_argument(
            '--platform',
            type=str,
            help="Canonical AKL platform"
        )
        self.parser.add_argument(
            '--system_name',
            type=str,
            help="User-defined system/display name"
        )
        self.parser.add_argument(
            '--asset_paths',
            type=json.loads,
            help="System artwork destination paths"
        )

    def parse(self):
        self.args = self.parser.parse_args()

    def get_usage(self):
        return self.parser.usage

    def get_type(self):
        return self.args.type

    def get_command(self):
        if self.args.type == constants.AddonType.LAUNCHER.name and self.args.cmd == 'launch':
            return AklAddonArguments.LAUNCH
        elif self.args.type == constants.AddonType.LAUNCHER.name and self.args.cmd == 'configure':
            return AklAddonArguments.CONFIGURE_LAUNCHER
        elif self.args.type == constants.AddonType.SCANNER.name and self.args.cmd == 'scan':
            return AklAddonArguments.SCAN
        elif self.args.type == constants.AddonType.SCANNER.name and self.args.cmd == 'configure':
            return AklAddonArguments.CONFIGURE_SCANNER
        elif self.args.type == constants.AddonType.SCRAPER.name and self.args.cmd == 'scrape':
            return AklAddonArguments.SCRAPE
        elif (
            self.args.type == constants.AddonType.SCRAPER.name
            and self.args.cmd == 'scrape_system'
        ):
            return AklAddonArguments.SCRAPE_SYSTEM

        return None

    def get_webserver_host(self):
        return self.args.server_host

    def get_webserver_port(self):
        return self.args.server_port

    def get_akl_addon_id(self):
        return self.args.akl_addon_id

    def get_entity_id(self):
        if self.args.rom_id:
            return self.args.rom_id
        if self.args.source_id:
            return self.args.source_id
        return self.args.entity_id

    def get_entity_type(self):
        if self.args.rom_id:
            return constants.OBJ_ROM
        if self.args.source_id:
            return constants.OBJ_SOURCE
        return self.args.entity_type

    def get_settings(self):
        return self.args.settings

    def get_platform(self):
        return self.args.platform

    def get_system_name(self):
        return self.args.system_name

    def get_asset_paths(self):
        return self.args.asset_paths

    def get_help(self):
        return self.parser.format_help()
