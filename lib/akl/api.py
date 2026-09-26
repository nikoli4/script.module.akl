# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher: API
#
# Copyright (c) Chrisism <crizizz@gmail.com>
# Copyright (c) 2016-2019 Wintermute0110 <wintermute0110@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

#
# API client to connect to AKL server to retrieve ROM data.
#

# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
from __future__ import annotations

import abc
import logging
import typing

# AKL modules
from akl.utils import net, io
from akl import constants

logger = logging.getLogger(__name__)

VERBOSE = False


###############################################################
# CLIENT METHODS
###############################################################
def client_get_rom(host: str, port: int, rom_id: str) -> ROMObj:
    uri = f'http://{host}:{port}/query/rom/?id={rom_id}'
    rom_data = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(rom_data)
    return ROMObj(rom_data)


def client_get_roms_in_source(host: str, port: int, source_id: str) -> typing.List[ROMObj]:
    uri = f'http://{host}:{port}/query/source/roms/?id={source_id}'
    rom_data = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(rom_data)
    roms = []
    for rom_entry in rom_data:
        roms.append(ROMObj(rom_entry))
    return roms


def client_get_roms_in_collection(host: str, port: int, rom_collection_id: str) -> typing.List[ROMObj]:
    uri = f'http://{host}:{port}/query/romcollection/roms/?id={rom_collection_id}'
    rom_data = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(rom_data)
    roms = []
    for rom_entry in rom_data:
        roms.append(ROMObj(rom_entry))
    return roms


def client_get_source_launchers(host: str, port: int, source_id: str) -> dict:
    uri = f'http://{host}:{port}/query/source/launchers/?id={source_id}'
    launchers = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(launchers)
    return launchers


def client_get_collection_launchers(host: str, port: int, rom_collection_id: str) -> dict:
    uri = f'http://{host}:{port}/query/romcollection/launchers/?id={rom_collection_id}'
    launchers = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(launchers)
    return launchers


def client_get_launcher_settings(host: str, port: int, launcher_id: str) -> dict:
    uri = f'http://{host}:{port}/query/launcher/settings/?launcher_id={launcher_id}'
    launcher_settings = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(launcher_settings)
    return launcher_settings


def client_get_source_scanner_settings(host: str, port: int, source_id: str) -> dict:
    uri = f'http://{host}:{port}/query/source/scanner/settings/?id={source_id}'
    scanner_settings = net.get_URL_as_json(uri)
    if VERBOSE:
        logger.debug(VERBOSE)
    return scanner_settings


def client_post_launcher_settings(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/launcher/'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200


def client_post_scanner_settings(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/scanner/'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200


def client_post_scanned_roms(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/roms/added'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200


def client_post_dead_roms(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/roms/dead'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200


def client_post_scraped_rom(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/rom/updated'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200


def client_post_scraped_roms(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/roms/updated'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200

def client_post_scraped_system(host: str, port: int, data: dict) -> bool:
    uri = f'http://{host}:{port}/store/system/updated'
    if VERBOSE:
        logger.debug(f'POST REQUEST: {data}')
    response_data, code = net.post_JSON_URL(uri, data)
    if VERBOSE:
        logger.debug(f'RESPONSE: {response_data}')
    return code == 200

###############################################################
# CLIENT OBJECTS
###############################################################
class MetaDataObj(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, entity_data: dict = None):
        if entity_data is None:
            entity_data = {}
        self.entity_data = entity_data

    def get_id(self) -> str:
        return self.entity_data['id'] if 'id' in self.entity_data else None
    
    def get_data_dic(self):
        return self.entity_data

    def get_custom_attribute(self, key, default_value=None):
        return self.entity_data[key] if key in self.entity_data else default_value

    # --- Metadata --------------------------------------------------------------------------------
    def get_name(self):
        return self.entity_data['m_name'] if 'm_name' in self.entity_data else None

    def get_releaseyear(self):
        return self.entity_data['m_year'] if 'm_year' in self.entity_data else None

    def get_genre(self) -> str:
        return self.entity_data['m_genre'] if 'm_genre' in self.entity_data else None

    def get_developer(self) -> str:
        return self.entity_data['m_developer'] if 'm_developer' in self.entity_data else None

    def get_rating(self):
        return int(self.entity_data['m_rating']) if self.entity_data['m_rating'] else None

    def get_plot(self):
        return self.entity_data['m_plot'] if 'm_plot' in self.entity_data else None
        
    def get_number_of_players(self):
        return self.entity_data['m_nplayers']

    def get_number_of_players_online(self):
        return self.entity_data['m_nplayers_online']

    def get_esrb_rating(self):
        return self.entity_data['m_esrb']
        
    def get_pegi_rating(self):
        return self.entity_data['m_pegi']
        
    def has_asset(self, asset_id: str) -> bool:
        asset = self.get_asset(asset_id)
        return asset is not None and asset != ''

    def get_asset(self, asset_id: str) -> str:
        return self.entity_data['assets'][asset_id] if asset_id in self.entity_data['assets'] else None
    
    def set_name(self, name):
        self.entity_data['m_name'] = name

    def set_releaseyear(self, releaseyear):
        self.entity_data['m_year'] = releaseyear

    def set_genre(self, genre):
        self.entity_data['m_genre'] = genre

    def set_developer(self, developer):
        self.entity_data['m_developer'] = developer

    def set_rating(self, rating):
        try:
            self.entity_data['m_rating'] = int(rating)
        except Exception:
            self.entity_data['m_rating'] = ''

    def set_plot(self, plot):
        self.entity_data['m_plot'] = plot
    
    def set_number_of_players(self, amount):
        self.entity_data['m_nplayers'] = amount
        
    def set_number_of_players_online(self, amount):
        self.entity_data['m_nplayers_online'] = amount

    def set_esrb_rating(self, esrb):
        self.entity_data['m_esrb'] = esrb

    def set_pegi_rating(self, pegi):
        self.entity_data['m_pegi'] = pegi
        
    def set_asset(self, asset_id: str, asset_path: str):
        self.entity_data['assets'][asset_id] = asset_path


class ROMObj(MetaDataObj):

    def get_identifier(self) -> str:
        identifier = self.get_scanned_data_element('identifier')
        name = self.get_name()
        
        if identifier:
            return identifier
        if name:
            return name
        return f'ROM_{self.get_id()}'

    def get_scanned_by(self) -> str:
        return self.entity_data['scanned_by_id'] if 'scanned_by_id' in self.entity_data else None
                   
    def get_scanned_data(self) -> dict:
        return self.entity_data['scanned_data'] if 'scanned_data' in self.entity_data else {}

    def get_scanned_data_element(self, key: str):
        scanned_data = self.get_scanned_data()
        return scanned_data[key] if key in scanned_data else None
    
    def get_scanned_data_element_as_file(self, key: str):
        scanned_data = self.get_scanned_data()
        scanned_value = scanned_data[key] if key in scanned_data else None
        
        if scanned_value is None or scanned_value == '':
            return None
        return io.FileName(scanned_value)
    
    def set_scanned_data(self, data: dict):
        self.entity_data['scanned_data'] = data
       
    def set_scanned_data_element(self, key: str, data):
        self.entity_data['scanned_data'][key] = data
    
    def set_platform(self, platform):
        self.entity_data['platform'] = platform

    def get_platform(self):
        return self.entity_data['platform']
    
    def get_tags(self) -> typing.List[str]:
        if 'tags' not in self.entity_data:
            return []
        return self.entity_data['tags']

    def set_tags(self, tags: typing.List[str]):
        self.entity_data['tags'] = tags

    def get_asset_path(self, assetinfo_id: str) -> io.FileName:
        asset_paths = self.entity_data['asset_paths'] if 'asset_paths' in self.entity_data else {}
        asset_path_str = asset_paths[assetinfo_id] if assetinfo_id in asset_paths else None
        
        if asset_path_str is None or asset_path_str == '':
            return None
        return io.FileName(asset_path_str)
     
    def get_all_asset_paths(self) -> typing.List[io.FileName]:
        asset_paths = self.entity_data['asset_paths'].values() if 'asset_paths' in self.entity_data else []
        asset_path_FNs = [io.FileName(pth) for pth in asset_paths]
        return asset_path_FNs
    
    def update_with_nfo_file(self, nfo_file_path: io.FileName):
        logger.debug('ROMObj.update_with_nfo_file() Loading "{0}"'.format(nfo_file_path.getPath()))
        if not nfo_file_path.exists():
            logger.debug("ROMObj.update_with_nfo_file() NFO file not found '{0}'".format(nfo_file_path.getPath()))
            return
        
        xml_doc = nfo_file_path.readXml()
        if xml_doc is None:
            return
        
        item_title = xml_doc.find('title')
        item_year = xml_doc.find('year')
        item_genre = xml_doc.find('genre')
        item_nplayers = xml_doc.find('nplayers')
        item_esrb = xml_doc.find('esrb')
        item_pegi = xml_doc.find('pegi')
        item_rating = xml_doc.find('rating')
        item_plot = xml_doc.find('plot')
        item_trailer = xml_doc.find('trailer')
        item_developer = xml_doc.find('developer')
        if not item_developer:
            item_developer = xml_doc.find('publisher')
        
        if item_title is not None:
            self.set_name(item_title.text)
        if item_year is not None:
            self.set_releaseyear(item_year.text)
        if item_genre is not None:
            self.set_genre(item_genre.text)
        if item_developer is not None:
            self.set_developer(item_developer.text)
        if item_rating is not None:
            self.set_rating(item_rating.text)
        if item_plot is not None:
            self.set_plot(item_plot.text)
        if item_nplayers is not None:
            self.set_number_of_players(item_nplayers.text)
        if item_esrb is not None:
            self.set_esrb_rating(item_esrb.text)
        if item_pegi is not None:
            self.set_pegi_rating(item_pegi.text)
        if item_trailer is not None:
            self.set_asset(constants.ASSET_TRAILER_ID, item_trailer.text)
     
    @staticmethod
    def get_data_template() -> dict:
        return {
            'id': '',
            'm_name': '',
            'm_year': '',
            'm_genre': '',
            'm_developer': '',
            'm_rating': '',
            'm_plot': '',
            'm_nplayers': '',
            'm_nplayers_online': '',
            'm_esrb': '',
            'm_pegi': '',
            'platform': '',
            'scanned_by_id': '',
            'scanned_data': {},
            'assets': {},
            'asset_paths': {},
            'tags': []
        }
