# -*- coding: utf-8 -*-

# Advanced Kodi Launcher scraping engine.
#
# --- Information about scraping ---
# https://github.com/muldjord/skyscraper
# https://github.com/muldjord/skyscraper/blob/master/docs/SCRAPINGMODULES.md

# Copyright (c) Chrisism <crizizz@gmail.com>
# Copyright (c) 2016-2019 Wintermute0110 <wintermute0110@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.


# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
from __future__ import annotations

import logging
import typing
import abc
import time
from datetime import datetime
import os
import re
import json

# Kodi libs
import xbmcgui

# AKL libs
from akl.utils import kodi, io, net, text
from akl import constants, platforms, settings
from akl import api

from akl.api import ROMObj


# --- Scraper use cases ---------------------------------------------------------------------------
# THIS DOCUMENTATION IS OBSOLETE, IT MUST BE UPDATED TO INCLUDE THE SCRAPER DISK CACHE.
#
# The ScraperFactory class is resposible to create a ScraperStrategy object according to the
# addon settings and to keep a cached dictionary of Scraper objects.
#
# The actual scraping is done by the ScraperStrategy object, which has the logic to download
# images, rename them, etc., and to interact with the scraped object (ROM, Std Launchers).
#
# The Scraper objects only know of to pull information from websites or offline XML databases.
# Scraper objects do not need to reference Launcher or ROM objects. Pass to them the required
# properties like platform. Launcher and ROM objects are know by the ScraperStrategy but not
# by the Scraper objects.
#
# --- NOTES ---
# 1) There is one and only one global ScraperFactory object named g_scraper_factory.
#
# 2) g_scraper_factory keeps a list of instantiated scraper objects. Scrapers are identified
#    with a numerical list index. This is required to identify a concrete scraper object
#    from the addon settings.
#
# 3) g_scraper_factory must be able to report each scraper capabilities.
#
# 4) The actual object metadata/asset scraping is done by an scrap_strategy object instance.
#
# 5) progress_dialog_obj object instance is passed to the scrap_strategy instance.
#    In the ROM scanner the progress dialog is created in the scanner instance and 
#    changed by the scanner/scraper objects.
#
# --- Use case A: ROM scanner ---------------------------------------------------------------------
# The ROM scanner case also applies when the user selects "Rescrape ROM assets" in the Launcher
# context menu.
#
# --- Algorithm ---
# 1) Create a ScraperFactory global object g_scraper_factory.
# 1.1) For each scraper class one and only one object is instantiated and initialised.
#      This per-scraper unique object simplifies the coding of the scraper cache.
#      The unique scraper objects are stored inside the global g_scraper_factory and can
#      be reused.
#
# 2) Create a ScraperStrategy object with the g_scraper_factory object.
# 2.1) g_scraper_factory checks for unset artwork directories. Disable unconfigured assets.
# 2.2) Check for duplicate artwork directories. Disable assets for duplicated directories.
# 2.3) Read the addon settings and create the metadata scraper to process ROMs.
# 2.4) For each asset type not disabled create the asset scraper.
# 2.5) Finally, create and return the ScraperStrategy object.
#
# 3) For each ROM object scrape the metadata and assets with the ScraperStrategy object.
#
# --- Code example ---
# scrap_strategy.process_ROM() scrapes all enabled assets in sequence using all the
# configured scrapers (primary, secondary).
#
# g_scraper_factory = ScraperFactory(g_PATHS, g_settings)
# scrap_strategy = g_scraper_factory.create_scanner(launcher_obj, progress_dialog_obj)
# scrap_strategy.process_ROM(rom_obj, None))
#
# --- Use case B: ROM context menu ---------------------------------------------------------------
# In the ROM context menu the scraper object may be called multiple times by the recursive
# context menu.
#
# Scrapers should report the assets they support to build the dynamic context menu.
#
# The scraping mode when using the context menu is always manual.
#
# --- Use case C: Standalone Launcher context menu -----------------------------------------------
# In the Standalone Launcher context menu the situation is similar to the ROM context menu.
# The difference is that rom_obj is a Launcher object instance instead of a ROM object.
# -----------------------------------------------------------------------------------------------
class ScraperSettings(object):
    
    def __init__(self):
        self.scrape_metadata_policy = constants.SCRAPE_POLICY_TITLE_ONLY
        self.scrape_assets_policy = constants.SCRAPE_POLICY_LOCAL_ONLY
        
        self.search_term_mode = constants.SCRAPE_AUTOMATIC
        self.game_selection_mode = constants.SCRAPE_AUTOMATIC
        self.asset_selection_mode = constants.SCRAPE_AUTOMATIC
        
        self.metadata_IDs_to_scrape = constants.METADATA_IDS
        self.asset_IDs_to_scrape = constants.ROM_ASSET_ID_LIST
        
        self.overwrite_existing_meta = False
        self.overwrite_existing_assets = False
        
        self.ignore_scrap_title = False
        self.clean_tags = False
        self.update_nfo_files = False
        self.show_info_verbose = False
    
    def get_data_dic(self) -> dict:
        return self.__dict__
            
    @staticmethod
    def from_addon_settings():
        scraper_settings = ScraperSettings()
                                        
        scraper_settings.scrape_metadata_policy = settings.getSettingAsInt('scrape_metadata_policy')
        scraper_settings.scrape_assets_policy = settings.getSettingAsInt('scrape_assets_policy')
        scraper_settings.game_selection_mode = settings.getSettingAsInt('game_selection_mode')
        scraper_settings.asset_selection_mode = settings.getSettingAsInt('asset_selection_mode')
        
        scraper_settings.ignore_scrap_title = settings.getSettingAsBool('scan_ignore_scrap_title')
        scraper_settings.clean_tags = settings.getSettingAsBool('scan_clean_tags')
        scraper_settings.update_nfo_files = settings.getSettingAsBool('scan_update_NFO_files')
        
        return scraper_settings
        
    @staticmethod
    def from_settings_dict(settings: dict):
        scraper_settings = ScraperSettings()
            
        scraper_settings.scrape_metadata_policy = settings['scrape_metadata_policy']
        scraper_settings.scrape_assets_policy = settings['scrape_assets_policy']
        scraper_settings.search_term_mode = settings['search_term_mode']
        scraper_settings.game_selection_mode = settings['game_selection_mode']
        scraper_settings.asset_selection_mode = settings['asset_selection_mode']
        scraper_settings.metadata_IDs_to_scrape = settings['metadata_IDs_to_scrape']
        scraper_settings.asset_IDs_to_scrape = settings['asset_IDs_to_scrape']
        scraper_settings.overwrite_existing_meta = settings['overwrite_existing_meta']
        scraper_settings.overwrite_existing_assets = settings['overwrite_existing_assets']

        scraper_settings.ignore_scrap_title = settings['ignore_scrap_title']
        scraper_settings.clean_tags = settings['clean_tags']
        scraper_settings.update_nfo_files = settings['update_nfo_files']
        scraper_settings.show_info_verbose = settings['show_info_verbose']
        
        return scraper_settings
    

# This class is used to filter No-Intro BIOS ROMs and MAME BIOS, Devices and Mecanichal machines.
# No-Intro BIOSes are easy to filter, filename starts with '[BIOS]'
# MAME is more complicated. The Offline Scraper includes 3 JSON filenames
#   MAME_BIOSes.json
#   MAME_Devices.json
#   MAME_Mechanical.json
# used to filter MAME machines.
# This class is (will be) used in the ROM Scanner.
class FilterROM(object):
    def __init__(self, PATHS, settings, platform):
        self.logger = logging.getLogger(__name__)
        self.logger.debug('FilterROM.__init__() BEGIN...')
        
        self.PATHS = PATHS
        self.settings = settings
        self.platform = platform
        self.addon_dir = self.settings['scraper_akloffline_addon_code_dir']

        # If platform is MAME load the BIOS, Devices and Mechanical databases.
        if self.platform == platforms.PLATFORM_MAME_LONG:
            BIOS_path = os.path.join(self.addon_dir, 'data-AOS', 'MAME_BIOSes.json')
            Devices_path = os.path.join(self.addon_dir, 'data-AOS', 'MAME_Devices.json')
            Mechanical_path = os.path.join(self.addon_dir, 'data-AOS', 'MAME_Mechanical.json')
            BIOS_list = self._load_JSON(BIOS_path)
            Devices_list = self._load_JSON(Devices_path)
            Mechanical_list = self._load_JSON(Mechanical_path)
            # Convert lists to sets to execute efficiently 'x in y' operation.
            self.BIOS_set = {i for i in BIOS_list}
            self.Devices_set = {i for i in Devices_list}
            self.Mechanical_set = {i for i in Mechanical_list}

    def _load_JSON(self, filename):
        self.logger.debug('FilterROM::_load_JSON() Loading "{}"'.format(filename))
        with open(filename) as file:
            data = json.load(file)

        return data

    # Returns True if ROM is filtered, False otherwise.
    def ROM_is_filtered(self, basename):
        self.logger.debug('FilterROM::ROM_is_filtered() Testing "{}"'.format(basename))
        if not self.settings['scan_ignore_bios']:
            self.logger.debug('FilterROM::ROM_is_filtered() Filters disabled. Return False.')
            return False

        if self.platform == platforms.PLATFORM_MAME_LONG:
            if basename in self.BIOS_set:
                self.logger.debug('FilterROM::ROM_is_filtered() Filtered MAME BIOS "{}"'.format(basename))
                return True
            if basename in self.Devices_set:
                self.logger.debug('FilterROM::ROM_is_filtered() Filtered MAME Device "{}"'.format(basename))
                return True
            if basename in self.Mechanical_set:
                self.logger.debug('FilterROM::ROM_is_filtered() Filtered MAME Mechanical "{}"'.format(basename))
                return True
        else:
            # If it is not MAME it is No-Intro
            # Name of bios is: '[BIOS] Rom name example (Rev A).zip'
            BIOS_m = re.findall('\[BIOS\]', basename)
            if BIOS_m:
                self.logger.debug('FilterROM::ROM_is_filtered() Filtered No-Intro BIOS "{}"'.format(basename))
                return True

        return False

         
#
# Main scraping logic.
#
class ScrapeStrategy(object):
    
    # --- Class variables ------------------------------------------------------------------------
    # --- Metadata actions ---
    ACTION_META_NONE = 0
    ACTION_META_TITLE_ONLY = 100
    ACTION_META_NFO_FILE = 200
    ACTION_META_SCRAPER = 300

    # --- Asset actions ---
    ACTION_ASSET_NONE = 0
    ACTION_ASSET_LOCAL_ASSET = 100
    ACTION_ASSET_SCRAPER = 200

    SCRAPE_ROM = 'ROM'
    SCRAPE_LAUNCHER = 'Launcher'

    # --- Constructor ----------------------------------------------------------------------------
    # @param settings: [dict] Addon settings.
    def __init__(self,
                 webservice_host: str,
                 webservice_port: int,
                 scraper_settings: ScraperSettings,
                 scraper: Scraper,
                 progress_dialog: kodi.ProgressDialog):
        
        self.logger = logging.getLogger(__name__)
        self.logger.debug('ScrapeStrategy.__init__() Initializing ScrapeStrategy...')
        
        self.webservice_host = webservice_host
        self.webservice_port = webservice_port
        self.scraper_settings = scraper_settings
                
        # default set to given scraper so that reference exists
        self.meta_scraper_obj: Scraper = scraper
        self.asset_scraper_obj: Scraper = scraper
        
        # Check if scraper is ready for operation (missing API keys, etc.). If not disable scraper.
        # Display error reported in status_dic as Kodi dialogs.
        status_dic = kodi.new_status_dic('No error')
        if scraper is not None:
            scraper.check_before_scraping(status_dic)
            if not status_dic['status']:
                kodi.dialog_OK(status_dic['msg'])
                self.scraper_settings.scrape_metadata_policy = constants.SCRAPE_ACTION_NONE
                self.scraper_settings.scrape_assets_policy = constants.SCRAPE_ACTION_NONE
        
        if self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_TITLE_ONLY or \
            self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_LOCAL_ONLY or \
                self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_ACTION_NONE:
            self.meta_scraper_obj = Null_Scraper()
        if self.scraper_settings.scrape_assets_policy == constants.SCRAPE_ACTION_NONE:
            self.asset_scraper_obj = Null_Scraper()
                
        self.meta_and_asset_scraper_same = self.meta_scraper_obj is self.asset_scraper_obj
        self.pdialog = progress_dialog
        self.pdialog_verbose = scraper_settings.show_info_verbose
        
        self.logger.debug('========================== Applied scraper settings ==========================')
        self.logger.debug('Metadata policy:      {}'.format(self._translate(scraper_settings.scrape_metadata_policy)))
        self.logger.debug('Search term input:    {}'.format(self._translate(scraper_settings.search_term_mode)))
        self.logger.debug('Game selection:       {}'.format(self._translate(scraper_settings.game_selection_mode)))
        self.logger.debug('Metadata IDs:         {}'.format(', '.join(scraper_settings.metadata_IDs_to_scrape)))
        self.logger.debug('Assets policy:        {}'.format(self._translate(scraper_settings.scrape_assets_policy)))
        self.logger.debug('Asset selection:      {}'.format(self._translate(scraper_settings.asset_selection_mode)))
        self.logger.debug('Asset IDs:            {}'.format(', '.join(scraper_settings.asset_IDs_to_scrape)))
        self.logger.debug('Overwrite existing:')
        self.logger.debug(' - Metadata           {}'.format('Yes' if scraper_settings.overwrite_existing_meta else 'No'))
        self.logger.debug(' - Assets             {}'.format('Yes' if scraper_settings.overwrite_existing_assets else 'No'))
        self.logger.debug('Ignore scrape title:  {}'.format('Yes' if scraper_settings.ignore_scrap_title else 'No'))
        self.logger.debug('Update NFO files:     {}'.format('Yes' if scraper_settings.update_nfo_files else 'No'))
        self.logger.debug('==============================================================================')
 
    def process_roms(self, entity_type: int, entity_id) -> typing.List[ROMObj]:
        try:
            if entity_type == constants.OBJ_SOURCE:
                roms = api.client_get_roms_in_source(self.webservice_host, self.webservice_port, entity_id)
            else:
                roms = api.client_get_roms_in_collection(self.webservice_host, self.webservice_port, entity_id)
        except Exception:
            self.logger.exception('Failure while retrieving ROMs from database')
            return
        
        num_items = len(roms)
        num_items_checked = 0
        self.pdialog.startProgress('Scraping multiple ROMs', num_items)
        self.logger.debug('============================== Scraping ROMs ==============================')
        
        all_paths = []
        for rom in roms:
            all_paths.extend(rom.get_all_asset_paths())
        self._cache_assets(all_paths)
        
        for rom in roms:
            self.pdialog.updateProgress(num_items_checked)
            num_items_checked = num_items_checked + 1
            ROM_name = rom.get_identifier()
            self.pdialog.updateMessage(f'Scraping ROM {ROM_name}...')
            try:
                self._process_ROM(rom)
            except Exception:
                self.logger.exception(f'Could not scrape "{ROM_name}"')
                kodi.notify_warn(f'Could not scrape "{ROM_name}"')
            
            # ~~~ Check if user pressed the cancel button ~~~
            if self.pdialog.isCanceled():
                self.pdialog.endProgress()
                self.logger.info('User pressed Cancel button when scraping ROMs. ROM scraping stopped.')
                if kodi.dialog_yesno('Stopping ROM scraping. Store currently scraped items anyway?'):
                    return roms
                return None
        
        self.pdialog.endProgress()
        return roms
    
    def process_single_rom(self, rom_id: str) -> ROMObj:
        self.logger.debug('ScrapeStrategy.process_single_rom() Load and scrape a single ROM...')
        try:
            rom = api.client_get_rom(self.webservice_host, self.webservice_port, rom_id)
        except Exception:
            self.logger.exception('Failure while retrieving ROM from database')
            return
        
        ROM_name = rom.get_identifier()
        msg = 'Scraping ROM {}...'.format(ROM_name)
        self.pdialog.startProgress(msg)
        self._cache_assets(rom.get_all_asset_paths())
        try:
            self._process_ROM(rom)
        except Exception:
            self.logger.exception(f'Could not scrape "{ROM_name}"')
            kodi.notify_warn(f'Could not scrape "{ROM_name}"')
            return None
        
        return rom
    
    def _process_ROM(self, rom: ROMObj):
        self.logger.debug('ScrapeStrategy._process_ROM() Determining metadata and asset actions...')
                        
        if self.scraper_settings.scrape_metadata_policy != constants.SCRAPE_ACTION_NONE:
            self._process_ROM_metadata_begin(rom)
        
        if self.scraper_settings.scrape_assets_policy != constants.SCRAPE_ACTION_NONE:
            self._process_ROM_assets_begin(rom)

        # --- If metadata or any asset is scraped then select the game among the candidates ---
        # Note that the metadata and asset scrapers may be different. If so, candidates
        # must be selected for both scrapers.
        #
        # If asset scraper is needed and metadata and asset scrapers are the same.
        # Do nothing because both scraper objects are really the same object and candidate has been
        # set internally in the scraper object. Unless candidate selection was skipped for metadata.
        status_dic = kodi.new_status_dic('No error')

        ROM_path = rom.get_scanned_data_element_as_file('file')
        if ROM_path:
            search_term = text.format_ROM_name_for_scraping(ROM_path.getBaseNoExt())
        else:
            search_term = rom.get_name()
            
        if self.scraper_settings.search_term_mode == constants.SCRAPE_MANUAL:
            search_term = kodi.dialog_keyboard('Search term', search_term)
            
        self.logger.debug('ScrapeStrategy._process_ROM() Getting candidates for game')
        meta_candidate_set = False
        if self.scraper_settings.scrape_metadata_policy != constants.SCRAPE_ACTION_NONE:
            if self.metadata_action == ScrapeStrategy.ACTION_META_SCRAPER:
                self._get_candidate(rom, search_term, self.meta_scraper_obj, status_dic)
                meta_candidate_set = True
        
        asset_candidate_set = False
        if self.scraper_settings.scrape_assets_policy != constants.SCRAPE_ACTION_NONE:
            if self.meta_and_asset_scraper_same and meta_candidate_set:
                self.logger.debug('Asset candidate game same as metadata candidate. Doing nothing.')
                asset_candidate_set = True
            else:
                self._get_candidate(rom, search_term, self.asset_scraper_obj, status_dic)
                asset_candidate_set = True
                
        if not meta_candidate_set:
            self.logger.debug('Metadata candidate game is not set')
        if not asset_candidate_set:
            self.logger.debug('Asset candidate game is not set')
            
        if self.scraper_settings.scrape_metadata_policy != constants.SCRAPE_ACTION_NONE:
            self._process_ROM_metadata(rom)
        
        if self.scraper_settings.scrape_assets_policy != constants.SCRAPE_ACTION_NONE:
            self._process_ROM_assets(rom)
                 
    # Called by the ROM scanner. Fills in the ROM metadata.
    #
    # @param ROM: [Rom] ROM object.
    def _process_ROM_metadata(self, rom: ROMObj):
        self.logger.debug('ScrapeStrategy::scanner_process_ROM_metadata() Processing metadata action...')
        if self.metadata_action == ScrapeStrategy.ACTION_META_NONE:
            return
                
        if self.metadata_action == ScrapeStrategy.ACTION_META_TITLE_ONLY:
            if self.pdialog_verbose:
                self.pdialog.updateMessage('Formatting ROM name...')
            ROM_path = rom.get_scanned_data_element_as_file('file')
            if ROM_path:
                rom.set_name(text.format_ROM_title(ROM_path.getBaseNoExt(), self.scraper_settings.clean_tags))

        elif self.metadata_action == ScrapeStrategy.ACTION_META_NFO_FILE:
            ROM_path = rom.get_scanned_data_element_as_file('file')
            if ROM_path: 
                NFO_file = io.FileName(ROM_path.getPathNoExt() + '.nfo')
            else:
                NFO_file = io.FileName(rom.get_identifier() + '.nfo')
        
            if self.pdialog_verbose:
                self.pdialog.updateMessage('Loading NFO file {0}'.format(self.NFO_file.getPath()))
            rom.update_with_nfo_file(NFO_file)

        elif self.metadata_action == ScrapeStrategy.ACTION_META_SCRAPER:
            self._scrap_ROM_metadata(rom)
        else:
            raise ValueError('Invalid metadata_action value {0}'.format(self.metadata_action))

    # Called by the ROM scanner. Fills in the ROM assets.
    #
    # @param rom: [ROM] ROM data object. Mutable and edited by assignment.
    def _process_ROM_assets(self, rom: ROMObj):
        self.logger.debug('Processing asset actions...')
        
        if all(asset_action == ScrapeStrategy.ACTION_ASSET_NONE for asset_action in self.asset_action_list.values()):
            return
        
        # --- Process asset by asset actions ---
        # --- Asset scraping ---
        for asset_id in self.scraper_settings.asset_IDs_to_scrape:
            asset_name = asset_id.capitalize()
            if self.asset_action_list[asset_id] == ScrapeStrategy.ACTION_ASSET_NONE:
                self.logger.debug(f'Skipping asset scraping for {asset_name}')
                continue    
            elif not self.scraper_settings.overwrite_existing_assets and rom.has_asset(asset_id):
                self.logger.debug(f'Asset {asset_name} already exists. Skipping (no overwrite)')
                continue
            elif self.asset_action_list[asset_id] == ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET:
                self.logger.debug(f'Using local asset for {asset_name}')
                local_asset = self.local_asset_list[asset_id]
                if local_asset:
                    rom.set_asset(asset_id, local_asset.getPath())
            elif self.asset_action_list[asset_id] == ScrapeStrategy.ACTION_ASSET_SCRAPER:
                asset_path = self._scrap_ROM_asset(asset_id, self.local_asset_list[asset_id], rom)
                if asset_path is None:
                    self.logger.debug(f'No asset scraped. Skipping {asset_name}')
                    continue
                rom.set_asset(asset_id, asset_path.getPath())
            else:
                raise ValueError(f'Asset ID {asset_id} unknown action {self.asset_action_list[asset_id]}')

        romdata = rom.get_data_dic()
        # --- Print some debug info ---
        self.logger.debug('Set Title     file "{}"'.format(romdata['assets'][constants.ASSET_TITLE_ID]))
        self.logger.debug('Set Snap      file "{}"'.format(romdata['assets'][constants.ASSET_SNAP_ID]))
        self.logger.debug('Set Boxfront  file "{}"'.format(romdata['assets'][constants.ASSET_BOXFRONT_ID]))
        self.logger.debug('Set Boxback   file "{}"'.format(romdata['assets'][constants.ASSET_BOXBACK_ID]))
        self.logger.debug('Set Cartridge file "{}"'.format(romdata['assets'][constants.ASSET_CARTRIDGE_ID]))
        self.logger.debug('Set Fanart    file "{}"'.format(romdata['assets'][constants.ASSET_FANART_ID]))
        self.logger.debug('Set Banner    file "{}"'.format(romdata['assets'][constants.ASSET_BANNER_ID]))
        self.logger.debug('Set Clearlogo file "{}"'.format(romdata['assets'][constants.ASSET_CLEARLOGO_ID]))
        self.logger.debug('Set Flyer     file "{}"'.format(romdata['assets'][constants.ASSET_FLYER_ID]))
        self.logger.debug('Set Map       file "{}"'.format(romdata['assets'][constants.ASSET_MAP_ID]))
        self.logger.debug('Set Manual    file "{}"'.format(romdata['assets'][constants.ASSET_MANUAL_ID]))
        self.logger.debug('Set Trailer   file "{}"'.format(romdata['assets'][constants.ASSET_TRAILER_ID]))

        return rom

    # Determine the actions to be carried out by process_ROM_metadata()
    def _process_ROM_metadata_begin(self, rom: ROMObj):
        self.logger.debug('Determining metadata actions...')
  
        if self.meta_scraper_obj is None:
            self.logger.debug('No metadata scraper set, disabling metadata scraping.')
            self.metadata_action = ScrapeStrategy.ACTION_META_NONE
            return
        
        # --- Determine metadata action ----------------------------------------------------------
        # --- Test if NFO file exists ---  
        ROM_path = rom.get_scanned_data_element_as_file('file')
        if ROM_path:
            self.NFO_file = io.FileName(ROM_path.getPathNoExt() + '.nfo')
        else:
            self.NFO_file = io.FileName(rom.get_identifier() + '.nfo')
        
        NFO_file_found = True if self.NFO_file.exists() else False
        if NFO_file_found:
            self.logger.debug('NFO file found "{0}"'.format(self.NFO_file.getPath()))
        else:
            self.logger.debug('NFO file NOT found "{0}"'.format(self.NFO_file.getPath()))

        # Action depends configured metadata policy and wheter the NFO files was found or not.
        if self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_TITLE_ONLY:
            self.logger.debug('Metadata policy: Read NFO file OFF | Scraper OFF')
            self.logger.debug('Metadata policy: Only cleaning ROM name.')
            self.metadata_action = ScrapeStrategy.ACTION_META_TITLE_ONLY

        elif self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_LOCAL_ONLY:
            self.logger.debug('Metadata policy: Read NFO file ON | Scraper OFF')
            if NFO_file_found:
                self.logger.debug('Metadata policy: NFO file found.')
                self.metadata_action = ScrapeStrategy.ACTION_META_NFO_FILE
            else:
                self.logger.debug('Metadata policy: NFO file not found. Only cleaning ROM name')
                self.metadata_action = ScrapeStrategy.ACTION_META_TITLE_ONLY

        elif self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_LOCAL_AND_SCRAPE:
            self.logger.debug('Metadata policy: Read NFO file ON | Scraper ON')
            if NFO_file_found:
                self.logger.debug('Metadata policy: NFO file found. Scraper not used.')
                self.metadata_action = ScrapeStrategy.ACTION_META_NFO_FILE
            else:
                self.logger.debug('Metadata policy: NFO file not found. Using scraper.')
                self.metadata_action = ScrapeStrategy.ACTION_META_SCRAPER

        elif self.scraper_settings.scrape_metadata_policy == constants.SCRAPE_POLICY_SCRAPE_ONLY:
            self.logger.debug('Metadata policy: Read NFO file OFF | Scraper ON')
            self.logger.debug('Metadata policy: Using metadata scraper {}'.format(self.meta_scraper_obj.get_name()))
            self.metadata_action = ScrapeStrategy.ACTION_META_SCRAPER

        else:
            raise ValueError('Invalid scrape_metadata_policy value {0}'.format(self.scraper_settings.scrape_metadata_policy))
  
    # Determine the actions to be carried out by _process_ROM_assets()
    def _process_ROM_assets_begin(self, rom: ROMObj):
        self.logger.debug('Determining asset actions...')
        
        if self.asset_scraper_obj is None:
            self.logger.debug('No asset scraper set, disabling asset scraping.')
            self.asset_action_list = {asset_id: ScrapeStrategy.ACTION_ASSET_NONE for asset_id in self.scraper_settings.asset_IDs_to_scrape}
            return
        
        # --- Determine Asset action -------------------------------------------------------------
        # --- Search for local artwork/assets ---
        # Always look for local assets whatever the scanner settings. For unconfigured assets
        # local_asset_list will have the default database value empty string ''.
        self.local_asset_list = self._get_local_assets(rom, self.scraper_settings.asset_IDs_to_scrape) 
        self.asset_action_list = {}
        
        # Print information to the log
        if self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_LOCAL_ONLY:
            self.logger.debug('Asset policy: Local images ON | Scraper OFF')
        elif self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_LOCAL_AND_SCRAPE:
            self.logger.debug('Asset policy: Local images ON | Scraper ON')
        elif self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_SCRAPE_ONLY:
            self.logger.debug('Asset policy: Local images OFF | Scraper ON')
        else:
            raise ValueError('Invalid scrape_assets_policy value {0}'.format(self.scraper_settings.scrape_assets_policy))
        # Process asset by asset (only enabled ones)
        for asset_info_id in self.scraper_settings.asset_IDs_to_scrape:
            # Local artwork.
            if not self.scraper_settings.overwrite_existing_assets and rom.has_asset(asset_info_id):
                self.logger.debug(f'ROM has {asset_info_id} assigned. Overwrite existing disabled.')
                self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_NONE
            elif self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_LOCAL_ONLY:
                if self.local_asset_list[asset_info_id]:
                    self.logger.debug(f'Local {asset_info_id} FOUND')
                else:
                    self.logger.debug(f'Local {asset_info_id} NOT found.')
                self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET
            # Local artwork + Scrapers.
            elif self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_LOCAL_AND_SCRAPE:
                if self.local_asset_list[asset_info_id]:
                    self.logger.debug('Local {0} FOUND'.format(asset_info_id))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET
                elif self.asset_scraper_obj.supports_asset_ID(asset_info_id):
                    # Scrape only if scraper supports asset.
                    self.logger.debug('Local {0} NOT found. Scraping.'.format(asset_info_id))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_SCRAPER
                else:
                    self.logger.debug('Local {0} NOT found. No scraper support.'.format(asset_info_id))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET
            # Scrapers.
            elif self.scraper_settings.scrape_assets_policy == constants.SCRAPE_POLICY_SCRAPE_ONLY:
                # Scraper does not support asset but local asset found.
                if not self.asset_scraper_obj.supports_asset_ID(asset_info_id) and self.local_asset_list[asset_info_id]:
                    self.logger.debug('Scraper {} does not support {}. Using local asset.'.format(
                        self.asset_scraper_obj.get_name(), asset_info_id))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET
                # Scraper does not support asset and local asset not found.
                elif not self.asset_scraper_obj.supports_asset_ID(asset_info_id) and not self.local_asset_list[asset_info_id]:
                    self.logger.debug('Scraper {} does not support {}. Local asset not found.'.format(
                        self.asset_scraper_obj.get_name(), asset_info_id))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_LOCAL_ASSET
                # Scraper supports asset. Scrape wheter local asset is found or not.
                elif self.asset_scraper_obj.supports_asset_ID(asset_info_id):
                    self.logger.debug('Scraping {} with {}.'.format(asset_info_id, self.asset_scraper_obj.get_name()))
                    self.asset_action_list[asset_info_id] = ScrapeStrategy.ACTION_ASSET_SCRAPER
                else:
                    raise ValueError('Logical error')

    # Get a candidate game in the ROM scanner.
    # Returns nothing.
    def _get_candidate(self, rom: ROMObj, search_term: str, scraper_obj: Scraper, status_dic):
        # --- Update scanner progress dialog ---
        if self.pdialog_verbose:
            scraper_text = 'Searching games with scraper {}...'.format(scraper_obj.get_name())
            self.pdialog.updateMessage(scraper_text)
        
        rom_platform = rom.get_platform()
        self.logger.debug('Searching games with scraper {} for platform {}'.format(scraper_obj.get_name(), rom_platform))

        # * The scanner uses the cached ROM candidate always.
        # * If the candidate is empty it means it was previously searched and the scraper
        #   found no candidates. In this case, the context menu must be used to manually
        #   change the search string and set a valid candidate.
        rom_identifier = rom.get_identifier()
        
        if scraper_obj.check_candidates_cache(rom_identifier, rom_platform):
            self.logger.debug('ROM "{}" in candidates cache.'.format(rom_identifier))
            candidate = scraper_obj.retrieve_from_candidates_cache(rom_identifier, rom_platform)
            if not candidate:
                self.logger.debug('Candidate game is empty. ROM will not be scraped again by the scanner.')
            use_from_cache = True
        else:
            self.logger.debug('ROM "{}" NOT in candidates cache.'.format(rom_identifier))
            use_from_cache = False
        self.logger.debug('use_from_cache "{}"'.format(use_from_cache))

        if use_from_cache:
            scraper_obj.set_candidate_from_cache(rom_identifier, rom_platform)
        else:
            # Clear all caches to remove preexiting information, just in case user is rescraping.
            scraper_obj.clear_cache(rom_identifier, rom_platform)

            # --- Call scraper and get a list of games ---                
            candidates = scraper_obj.get_candidates(search_term, rom, rom_platform, status_dic)
            # * If the scraper produced an error notification show it and continue scanner operation.
            # * Note that if many errors/exceptions happen (for example, network is down) then
            #   the scraper will disable itself after a number of errors and only a limited number
            #   of messages will be displayed.
            # * In the scanner treat any scraper error message as a Kodi OK dialog.
            # * Once the error is displayed reset status_dic
            if not status_dic['status']:
                if status_dic['dialog'] == kodi.KODI_MESSAGE_CANCEL:
                    self.pdialog.cancel()
                    return
                self.pdialog.close()
                # Close error message dialog automatically 1 minute to keep scanning.
                yesno_msg = f"{status_dic['msg']}\nStop scraping?"
                if kodi.dialog_yesno_timer(yesno_msg, 60000):
                    status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                    return
                status_dic = kodi.new_status_dic('No error')
                self.pdialog.reopen()
            # * If candidates is None some kind of error/exception happened.
            # * None is also returned if the scraper is disabled (also no error in status_dic).
            # * Set the candidate to None in the scraper object so later calls to get_metadata()
            #   and get_assets() do not fail (they will return None immediately).
            # * It will NOT be introduced in the cache to be rescraped. Objects with None value are
            #   never introduced in the cache.
            if candidates is None:
                self.logger.debug('Error getting the candidate (None).')
                scraper_obj.set_candidate(rom_identifier, rom_platform, None)
                return
            # * If candidates list is empty scraper operation was correct but no candidate was
            # * found. In this case set the candidate in the scraper object to an empty
            # * dictionary and introduce it in the cache.
            if not candidates:
                self.logger.debug('Found no candidates after searching.')
                scraper_obj.set_candidate(rom_identifier, rom_platform, dict())
                return
            self.logger.debug('Scraper {} found {} candidate/s'.format(scraper_obj.get_name(), len(candidates)))

            # --- Choose game to download metadata ---
            if self.scraper_settings.game_selection_mode == constants.SCRAPE_MANUAL:
                self.logger.debug('Metadata manual scraping')
                if len(candidates) == 1:
                    self.logger.debug('get_candidates() returned 1 game. Automatically selected.')
                    select_candidate_idx = 0
                else:
                    # Display game list found so user choses.
                    self.logger.debug('Metadata manual scraping. User chooses game.')
                    self.pdialog.close()
                    game_name_list = [candidate['display_name'] for candidate in candidates]
                    select_candidate_idx = kodi.ListDialog().select(
                        title='Select game for ROM {}'.format(rom_identifier), options_list=game_name_list)
                    if select_candidate_idx is None:
                        raise constants.AddonError('Cancelled game selection')
                    if select_candidate_idx < 0:
                        select_candidate_idx = 0
                    self.pdialog.reopen()
            elif self.scraper_settings.game_selection_mode == constants.SCRAPE_AUTOMATIC:
                self.logger.debug('Metadata automatic scraping. Selecting first result.')
                select_candidate_idx = 0
            else:
                raise ValueError('Invalid game_selection_mode {}'.format(self.scraper_settings.game_selection_mode))
            candidate = candidates[select_candidate_idx]

            # --- Set candidate. This will introduce it in the cache ---
            scraper_obj.set_candidate(rom_identifier, rom_platform, candidate)

    # Scraps ROM metadata in the ROM scanner.
    def _scrap_ROM_metadata(self, rom: ROMObj):
        self.logger.debug('ScrapeStrategy._scanner_scrap_ROM_metadata() Scraping metadata...')

        # --- Update scanner progress dialog ---
        if self.pdialog_verbose:
            scraper_text = 'Scraping metadata with {}...'.format(self.meta_scraper_obj.get_name())
            self.pdialog.updateMessage(scraper_text)

        # --- If no candidates available just clean the ROM Title and return ---
        if not self.meta_scraper_obj.candidate:
            self.logger.debug('Medatada candidate is empty (no candidates found). Cleaning ROM name only.')
            ROM_file = rom.get_scanned_data_element_as_file('file')
            if ROM_file:
                rom.set_name(text.format_ROM_title(ROM_file.getBaseNoExt(), self.scraper_settings.clean_tags))
            # Update the empty NFO file to mark the ROM as scraped and avoid rescraping
            # if collection is scanned again.
            return

        # --- Grab metadata for selected game and put into ROM ---
        status_dic = kodi.new_status_dic('No error')
        game_data = self.meta_scraper_obj.get_metadata(status_dic)
        if not status_dic['status']:
            if status_dic['dialog'] == kodi.KODI_MESSAGE_CANCEL:
                self.pdialog.cancel()
                return

            self.pdialog.close()
            # Close error message dialog automatically 1 minute to keep scanning.
            yesno_msg = f"{status_dic['msg']}\nStop scraping?"
            if kodi.dialog_yesno_timer(yesno_msg, 60000):
                status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                return
            self.pdialog.reopen()
            return

        scraper_applied = self._apply_candidate_on_metadata(game_data, rom)
        self.logger.debug(f"Scraper applied? {scraper_applied}")
        
    #
    # Returns a valid filename of the downloaded scrapped image, filename of local image
    # or empty string if scraper finds nothing or download failed.
    #
    # @param asset_info_id [str]
    # @param local_asset_path: [FileName]
    # @param rom: [Rom object]
    # @return: [str] Filename string with the asset path.
    def _scrap_ROM_asset(self, asset_info_id: str, local_asset_path: io.FileName, rom: ROMObj):
        # --- Cached frequent used things ---
        asset_dir_FN = rom.get_asset_path(asset_info_id)
        if not asset_dir_FN:
            self.logger.warning(f'ROM is missing asset dir for asset#{asset_info_id}')
            return None
            
        asset_path_noext_FN = asset_dir_FN + text.str_to_filename_str(rom.get_identifier())
        asset_name = asset_info_id.capitalize()
       
        t = 'Scraping {} with scraper {} ------------------------------'
        self.logger.debug(t.format(asset_info_id, self.asset_scraper_obj.get_name()))
        status_dic = kodi.new_status_dic('No error')
        
        # By default always use local image if found in case scraper fails.
        ret_asset_path = local_asset_path
        self.logger.debug('local_asset_path "{}"'.format(local_asset_path))
        self.logger.debug('asset_path_noext "{}"'.format(asset_path_noext_FN.getPath()))

        # --- If no candidates available just clean the ROM Title and return ---
        if self.asset_scraper_obj.candidate is None:
            self.logger.debug('Asset candidate is None (previous error). Doing nothing.')
            return ret_asset_path
        if not self.asset_scraper_obj.candidate:
            self.logger.debug('Asset candidate is empty (no candidates found). Doing nothing.')
            return ret_asset_path

        # --- If scraper does not support particular asset return inmediately ---
        if not self.asset_scraper_obj.supports_asset_ID(asset_info_id):
            self.logger.debug('Scraper {} does not support asset {}.'.format(
                self.asset_scraper_obj.get_name(), asset_info_id))
            return ret_asset_path

        # --- Update scanner progress dialog ---
        if self.pdialog_verbose:
            scraper_text = 'Getting {} images from {}...'.format(
                asset_info_id, self.asset_scraper_obj.get_name())
            self.pdialog.updateMessage(scraper_text)

        # --- Grab list of images/assets for the selected candidate ---
        assetdata_list = self.asset_scraper_obj.get_assets(asset_info_id, status_dic)
        if not status_dic['status']:
            if status_dic['dialog'] == kodi.KODI_MESSAGE_CANCEL:
                self.pdialog.cancel()
                return
            self.pdialog.close()
            # Close error message dialog automatically 1 minute to keep scanning.
            yesno_msg = f"{status_dic['msg']}\nStop scraping?"
            if kodi.dialog_yesno_timer(yesno_msg, 60000):
                status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                return
            status_dic = kodi.new_status_dic('No error')
            self.pdialog.reopen()
        if assetdata_list is None or not assetdata_list:
            # If scraper returns no images return current local asset.
            self.logger.debug('{} {} found no images.'.format(self.asset_scraper_obj.get_name(), asset_info_id))
            return ret_asset_path
        # self.logger.debug('{} scraper returned {} images.'.format(asset_name, len(assetdata_list)))

        # --- Semi-automatic scraping (user choses an image from a list) ---
        if self.scraper_settings.asset_selection_mode == constants.SCRAPE_MANUAL:
            # If there is a local image add it to the list and show it to the user
            local_asset_in_list_flag = False
            if local_asset_path:
                local_asset = {
                    'asset_ID': asset_info_id,
                    'display_name': 'Current local image',
                    'url_thumb': local_asset_path.getPath(),
                }
                assetdata_list.insert(0, local_asset)
                local_asset_in_list_flag = True

            # Convert list returned by scraper into a list the select window uses.
            ListItem_list = []
            for item in assetdata_list:
                listitem_obj = xbmcgui.ListItem(label=item['display_name'], label2=item['url_thumb'])
                listitem_obj.setArt({'icon': item['url_thumb']})
                ListItem_list.append(listitem_obj)
            # ListItem_list has 1 or more elements at this point.
            # If assetdata_list has only 1 element do not show select dialog. Note that the
            # length of assetdata_list is 1 only if scraper returned 1 image and a local image
            # does not exist. If the scraper returned no images this point is never reached.
            if len(ListItem_list) == 1:
                image_selected_index = 0
            else:
                self.pdialog.close()
                image_selected_index = xbmcgui.Dialog().select(
                    'Select {0} asset'.format(asset_name), list=ListItem_list, useDetails=True)
                self.logger.debug('{0} dialog returned index {1}'.format(asset_info_id, image_selected_index))
                if image_selected_index < 0:
                    image_selected_index = 0
                self.pdialog.reopen()
            # User chose to keep current asset.
            if local_asset_in_list_flag and image_selected_index == 0:
                self.logger.debug('User chose local asset. Returning.')
                return ret_asset_path
        # --- Automatic scraping. Pick first image. ---
        elif self.scraper_settings.asset_selection_mode == constants.SCRAPE_AUTOMATIC:
            image_selected_index = 0
        else:
            raise constants.AddonError('Invalid asset_selection_mode {0}'.format(self.scraper_settings.asset_selection_mode))

        # --- Download scraped image --------------------------------------------------------------
        selected_asset = assetdata_list[image_selected_index]

        # --- Resolve asset URL ---
        self.logger.debug('Resolving asset URL...')
        if self.pdialog_verbose:
            scraper_text = 'Scraping {0} with {1} (Resolving URL...)'.format(
                asset_info_id, self.asset_scraper_obj.get_name())
            self.pdialog.updateMessage(scraper_text)
        image_url, image_url_log = self.asset_scraper_obj.resolve_asset_URL(
            selected_asset, status_dic)
        if not status_dic['status']:
            if status_dic['dialog'] == kodi.KODI_MESSAGE_CANCEL:
                self.pdialog.cancel()
                return
            self.pdialog.close()
            # Close error message dialog automatically 1 minute to keep scanning.
            yesno_msg = f"{status_dic['msg']}\nStop scraping?"
            if kodi.dialog_yesno_timer(yesno_msg, 60000):
                status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                return
            status_dic = kodi.new_status_dic('No error')
            self.pdialog.reopen()
        if image_url is None or not image_url:
            self.logger.debug('Error resolving URL')
            return ret_asset_path
        self.logger.debug('Resolved {0} to URL "{1}"'.format(asset_info_id, image_url_log))

        # --- Resolve URL extension ---
        self.logger.debug('Resolving asset URL extension...')
        image_ext = self.asset_scraper_obj.resolve_asset_URL_extension(
            selected_asset, image_url, status_dic)
        if not status_dic['status']:
            if status_dic['dialog'] == kodi.KODI_MESSAGE_CANCEL:
                self.pdialog.cancel()
                return
            self.pdialog.close()
            # Close error message dialog automatically 1 minute to keep scanning.
            yesno_msg = f"{status_dic['msg']}\nStop scraping?"
            if kodi.dialog_yesno_timer(yesno_msg, 60000):
                status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                return
            status_dic = kodi.new_status_dic('No error')
            self.pdialog.reopen()
        if image_ext is None or not image_ext:
            self.logger.debug('Error resolving URL')
            return ret_asset_path
        self.logger.debug(f'Resolved URL extension "{image_ext}"')

        # If remote file is of type 'url', then do not download. Return value directly.
        if image_ext == "url":
            return io.Url(image_url)
        
        # --- Download image ---
        if self.pdialog_verbose:
            scraper_text = f'Downloading {asset_info_id} from {self.asset_scraper_obj.get_name()}...'
            self.pdialog.updateMessage(scraper_text)
        image_local_path = asset_path_noext_FN.append('.' + image_ext)
        self.logger.debug(f'Download  "{image_url_log}"')
        self.logger.debug(f'Into file "{image_local_path.getPath()}"')
        try:
            image_local_path = self.asset_scraper_obj.download_image(image_url, image_local_path)
        except Exception:
            self.logger.exception('(Exception) In scraper.download_image.')
            self.pdialog.close()
            # Close error message dialog automatically 1 minute to keep scanning.
            if kodi.dialog_yesno_timer(f'Cannot download {asset_name} image (Timeout).\nStop scraping?', 60000):
                status_dic['msg'] = f'Cannot download {asset_name} image (Timeout)'
                status_dic['dialog'] = kodi.KODI_MESSAGE_CANCEL
                return
            self.pdialog.reopen()
        
        # --- Update Kodi cache with downloaded image ---
        # Recache only if local image is in the Kodi cache, this function takes care of that.
        # kodi_update_image_cache(image_path)

        # --- Check if downloaded image file is OK ---
        # For example, check if a PNG image is really a PNG, a JPG is really JPG, etc.
        # Check for 0 byte files and delete them.
        # Etc.
            
        # --- Return value is downloaded image ---
        return image_local_path

    # This function to be used in AKL 0.10.x series.
    #
    # @param gamedata: Dictionary with game data.
    # @param rom: ROM object to apply metadata.
    # @return: True if metadata is valid an applied, False otherwise.
    def _apply_candidate_on_metadata(self, gamedata: dict, rom: ROMObj):
        if not gamedata:
            return False

        # --- Put metadata into ROM/Launcher object ---
        rom_file = rom.get_scanned_data_element_as_file('file')
        if self.scraper_settings.ignore_scrap_title and rom_file:
            rom_name = text.format_ROM_title(rom_file.getBaseNoExt(), self.scraper_settings.clean_tags)
            rom.set_name(rom_name)
            self.logger.debug("User wants to ignore scraper name. Setting name to '{0}'".format(rom_name))
        else:
            rom_name = gamedata['title']
            rom.set_name(rom_name)
            self.logger.debug("User wants scrapped name. Setting name to '{0}'".format(rom_name))

        rom.set_releaseyear(gamedata['year'])
        rom.set_genre(gamedata['genre'])
        rom.set_developer(gamedata['developer'])
        rom.set_number_of_players(gamedata['nplayers'])
        rom.set_number_of_players_online(gamedata['nplayers_online'])
        rom.set_esrb_rating(gamedata['esrb'])
        rom.set_pegi_rating(gamedata['pegi'])
        rom.set_plot(gamedata['plot'])
        rom.set_tags(gamedata['tags'])

        return True
        
    #
    # Search for local assets and place found files into a list.
    # Returned list all has assets as defined in ROM_ASSET_LIST.
    #
    # ROM         -> Rom object
    # asset_infos -> list of assets to request
    #
    def _get_local_assets(self, rom: ROMObj, asset_info_ids: list):
        self.logger.debug('_get_local_assets() Searching for ROM local assets...')
        rom_identifier = text.str_to_filename_str(rom.get_identifier())
        local_assets = {}
        for asset_info_id in asset_info_ids:
            
            asset_exts = constants.IMAGE_EXTENSION_LIST
            if asset_info_id == constants.ASSET_MANUAL_ID:
                asset_exts = constants.MANUAL_EXTENSION_LIST
            if asset_info_id == constants.ASSET_TRAILER_ID:
                asset_exts = constants.TRAILER_EXTENSION_LIST
            search_exts = io.get_filesearch_extension_list(asset_exts)
            
            asset_path = rom.get_asset_path(asset_info_id)
            if asset_path is None:
                local_assets[asset_info_id] = None
                self.logger.warning('Asset Path not defined for ROM {0} asset {1:<9}'.format(rom_identifier, asset_info_id))
            else:
                local_asset = io.misc_search_file_cache(asset_path, rom_identifier, search_exts)
                if local_asset:
                    local_assets[asset_info_id] = local_asset
                    self.logger.debug('Found    {0:<9} "{1}"'.format(asset_info_id, local_asset))
                else:
                    local_assets[asset_info_id] = None
                    self.logger.debug('Missing  {0:<9}'.format(asset_info_id))

        return local_assets

    def _cache_assets(self, paths: typing.List[io.FileName]):
        duplicates = []
        for path in paths:
            if path is None:
                continue
            
            path_str = path.getPath()
            if path_str in duplicates or path_str == '':
                continue
            
            self.logger.debug('Caching directory "{}"'.format(path_str))
            io.misc_add_file_cache(path)
            duplicates.append(path_str)

    def store_scraped_rom(self, scraper_id: str, rom_id: str, rom: ROMObj):
        if rom is None:
            self.logger.warning('Skipping store action. No ROM data provided.')
            return
        
        post_data = {
            'rom_id': rom_id,
            'akl_addon_id': scraper_id,
            'rom': rom.get_data_dic(),
            'applied_settings': self.scraper_settings.get_data_dic()
        }
        is_stored = api.client_post_scraped_rom(self.webservice_host, self.webservice_port, post_data)
        if not is_stored:
            kodi.notify_error('Failed to store scraped ROM')
  
    def store_scraped_roms(self, scraper_id: str, entity_type: int, entity_id: str, scraped_roms: typing.List[ROMObj]):
        roms = [*(r.get_data_dic() for r in scraped_roms)]
        post_data = {
            'entity_type': int(entity_type),
            'entity_id': entity_id,
            'akl_addon_id': scraper_id,
            'roms': roms,
            'applied_settings': self.scraper_settings.get_data_dic()
        }
        is_stored = api.client_post_scraped_roms(self.webservice_host, self.webservice_port, post_data)
        if not is_stored:
            kodi.notify_error('Failed to store scraped ROMs')

    def store_scraped_system(
            self,
            scraper_id: str,
            romcollection_id: str,
            system: api.MetaDataObj):

        if system is None:
            self.logger.warning(
                'Skipping store action. No system data provided.'
            )
            return

        post_data = {
            'romcollection_id': romcollection_id,
            'akl_addon_id': scraper_id,
            'system': system.get_data_dic(),
            'applied_settings': self.scraper_settings.get_data_dic()
        }

        is_stored = api.client_post_scraped_system(
            self.webservice_host,
            self.webservice_port,
            post_data
        )

        if not is_stored:
            kodi.notify_error('Failed to store scraped system')

    def _translate(self, key):
        if key == constants.SCRAPE_ACTION_NONE:
            return 'No action'
        if key == constants.SCRAPE_POLICY_TITLE_ONLY:
            return 'Use title only'
        if key == constants.SCRAPE_POLICY_LOCAL_ONLY:
            return 'Use local files only'
        if key == constants.SCRAPE_POLICY_LOCAL_AND_SCRAPE:
            return 'Local / Scrape'
        if key == constants.SCRAPE_POLICY_SCRAPE_ONLY:
            return 'Scrape only'
        if key == constants.SCRAPE_MANUAL:
            return 'Manual selection'
        if key == constants.SCRAPE_AUTOMATIC:
            return 'Automatic selection'
        return key


#
# Abstract base class for all scrapers (offline or online, metadata or asset).
# The scrapers are Launcher and ROM agnostic. All the required Launcher/ROM properties are
# stored in the strategy object.
#
class Scraper(object):
    __metaclass__ = abc.ABCMeta

    # --- Class variables ------------------------------------------------------------------------
    # When then number of network error/exceptions is bigger than this threshold the scraper
    # is deactivated. This is useful in the ROM Scanner to not flood the user with error
    # messages in case something is wrong (for example, the internet connection is broken or
    # the number of API calls is exceeded).
    EXCEPTION_COUNTER_THRESHOLD = 5
    
    # Maximum amount of retries of certain requests
    RETRY_THRESHOLD = 4

    # Disk cache types. These string will be part of the cache file names.
    CACHE_CANDIDATES = 'candidates'
    CACHE_METADATA = 'metadata'
    CACHE_ASSETS = 'assets'
    CACHE_INTERNAL = 'internal'
    CACHE_LIST = [
        CACHE_CANDIDATES, CACHE_METADATA, CACHE_ASSETS, CACHE_INTERNAL,
    ]
    GLOBAL_CACHE_LIST = []
    
    JSON_indent = 1
    JSON_separators = (',', ':')

    # --- Constructor ----------------------------------------------------------------------------
    # @param cache_dir: [io.FileName] Path to scraper cache dir.
    def __init__(self, cache_dir: io.FileName):
        self.logger = logging.getLogger(__name__)
        self.verbose_flag = False
        self.dump_file_flag = False  # Dump DEBUG files only if this is true.
        self.dump_dir = None  # Directory to dump DEBUG files.
        self.debug_checksums_flag = False
        # Record the number of network error/exceptions. If this number is bigger than a
        # threshold disable the scraper.
        self.exception_counter = 0
        # If this is True the scraper is internally disabled. A disabled scraper alwats returns
        # empty data like the NULL scraper.
        self.scraper_disabled = False
        # Directory to store on-disk scraper caches.
        self.scraper_cache_dir = cache_dir
        if not self.scraper_cache_dir:
            self.scraper_cache_dir = kodi.getAddonDir().pjoin('cache', isdir=True)
        
        if isinstance(self.scraper_cache_dir, str):
            self.scraper_cache_dir = io.FileName(self.scraper_cache_dir, isdir=True)

        if not self.scraper_cache_dir.exists():
            self.scraper_cache_dir.makedirs()

        self.logger.info(f'Scraper cache dir set to: {self.scraper_cache_dir.getPath()}')
        self.last_http_call = datetime.now()
        
        # --- Disk caches ---
        self.disk_caches = {}
        self.disk_caches_loaded = {}
        self.disk_caches_dirty = {}
        for cache_name in Scraper.CACHE_LIST:
            self.disk_caches[cache_name] = {}
            self.disk_caches_loaded[cache_name] = False
            self.disk_caches_dirty[cache_name] = False
        # Candidate game is set with functions set_candidate_from_cache() or set_candidate()
        # and used by functions get_metadata() and get_assets()
        self.candidate = None

        # --- Global disk caches ---
        self.global_disk_caches = {}
        self.global_disk_caches_loaded = {}
        self.global_disk_caches_dirty = {}
        for cache_name in Scraper.GLOBAL_CACHE_LIST:
            self.global_disk_caches[cache_name] = {}
            self.global_disk_caches_loaded[cache_name] = False
            self.global_disk_caches_dirty[cache_name] = False

    # --- Methods --------------------------------------------------------------------------------
    # Scraper is much more verbose (even more than AKL Debug level).
    def set_verbose_mode(self, verbose_flag):
        self.logger.debug('Scraper.set_verbose_mode() verbose_flag {0}'.format(verbose_flag))
        self.verbose_flag = verbose_flag

    # Dump scraper data into files for debugging. Used in the development scripts.
    def set_debug_file_dump(self, dump_file_flag, dump_dir):
        self.logger.debug('Scraper.set_debug_file_dump() dump_file_flag {0}'.format(dump_file_flag))
        self.logger.debug('Scraper.set_debug_file_dump() dump_dir {0}'.format(dump_dir))
        self.dump_file_flag = dump_file_flag
        self.dump_dir = dump_dir

    # ScreenScraper needs the checksum of the file scraped. This function sets the checksums
    # externally for debugging purposes, for example when debugging the scraper with
    # fake filenames.
    def set_debug_checksums(self, debug_checksums, crc_str='', md5_str='', sha1_str='', size=0):
        self.logger.debug('Scraper.set_debug_checksums() debug_checksums {0}'.format(debug_checksums))
        self.debug_checksums_flag = debug_checksums
        self.debug_crc = crc_str
        self.debug_md5 = md5_str
        self.debug_sha1 = sha1_str
        self.debug_size = size

    # Dump dictionary as JSON file for debugging purposes.
    # This function is used internally by the scrapers if the flag self.dump_file_flag is True.
    def _dump_json_debug(self, file_name, data_dic):
        if not self.dump_file_flag:
            return
        file_path = os.path.join(self.dump_dir, file_name)
        if constants.SCRAPER_CACHE_HUMAN_JSON:
            json_str = json.dumps(data_dic, indent=4, separators=(', ', ' : '))
        else:
            json_str = json.dumps(data_dic)
        io.FileName(file_path).writeAll(json_str)

    def _dump_file_debug(self, file_name, page_data):
        if not self.dump_file_flag:
            return
        file_path = os.path.join(self.dump_dir, file_name)
        io.FileName(file_path).writeAll(page_data)
    
    @abc.abstractmethod
    def get_name(self):
        pass

    @abc.abstractmethod
    def get_filename(self):
        pass

    @abc.abstractmethod
    def supports_disk_cache(self):
        pass

    @abc.abstractmethod
    def supports_search_string(self):
        pass

    @abc.abstractmethod
    def supports_metadata_ID(self, metadata_ID):
        pass

    @abc.abstractmethod
    def supports_metadata(self):
        pass

    @abc.abstractmethod
    def supports_asset_ID(self, asset_ID):
        pass

    @abc.abstractmethod
    def supports_assets(self):
        pass

    # Check if the scraper is ready to work. For example, check if required API keys are
    # configured, etc. If there is some fatal errors then deactivate the scraper.
    #
    # @return: [dic] kodi_new_status_dic() status dictionary.
    @abc.abstractmethod
    def check_before_scraping(self, status_dic):
        pass

    # The *_candidates_cache_*() functions use the low level cache functions which are internal
    # to the Scraper object. The functions next are public, however.

    # Returns True if candidate is in disk cache, False otherwise.
    # Lazy loads candidate cache from disk.
    def check_candidates_cache(self, rom_identifier: str, platform):
        self.cache_key = rom_identifier
        self.platform = platform

        return self._check_disk_cache(Scraper.CACHE_CANDIDATES, self.cache_key)

    # Not necesary to lazy load the cache because before calling this function
    # check_candidates_cache() must be called.
    def retrieve_from_candidates_cache(self, rom_identifier: str, platform):
        self.cache_key = rom_identifier

        return self._retrieve_from_disk_cache(Scraper.CACHE_CANDIDATES, self.cache_key)

    def set_candidate_from_cache(self, rom_identifier: str, platform):
        self.cache_key = rom_identifier
        self.platform = platform
        self.candidate = self._retrieve_from_disk_cache(Scraper.CACHE_CANDIDATES, self.cache_key)

    def set_candidate(self, rom_identifier: str, platform, candidate: dict):
        self.cache_key = rom_identifier
        self.platform = platform
        self.candidate = candidate
        self.logger.debug('Scrape.set_candidate() Setting "{}" "{}"'.format(self.cache_key, platform))
        # Do not introduce None candidates in the cache so the game will be rescraped later.
        # Keep the None candidate in the object internal variables so later calls to 
        # get_metadata() and get_assets() will know an error happened.
        if candidate is None:
            return
        self._update_disk_cache(Scraper.CACHE_CANDIDATES, self.cache_key, candidate)
        self.logger.debug('Scrape.set_candidate() Added "{}" to cache'.format(self.cache_key))

    # When the user decides to rescrape an item that was in the cache make sure all
    # the caches are purged.
    def clear_cache(self, rom_identifier: str, platform):
        self.cache_key = rom_identifier
        self.platform = platform
        self.logger.debug('Scraper.clear_cache() Clearing caches "{}" "{}"'.format(
            self.cache_key, platform))
        for cache_type in Scraper.CACHE_LIST:
            if self._check_disk_cache(cache_type, self.cache_key):
                self._delete_from_disk_cache(cache_type, self.cache_key)

    # Only write to disk non-empty caches.
    # Only write to disk dirty caches. If cache has not been modified then do not write it.
    def flush_disk_cache(self, pdialog: kodi.ProgressDialog = None):
        # If scraper does not use disk cache (notably AKL Offline) return.
        if not self.supports_disk_cache():
            self.logger.debug('Scraper.flush_disk_cache() Scraper {} does not use disk cache.'.format(
                self.get_name()))
            return

        # Create progress dialog.
        num_steps = len(Scraper.CACHE_LIST)  # + len(Scraper.GLOBAL_CACHE_LIST)
        step_count = 0
        if pdialog is not None:
            pdialog.startProgress('Flushing scraper disk caches...', num_steps)

        # --- Scraper caches ---
        self.logger.debug('Scraper.flush_disk_cache() Saving scraper {} disk cache...'.format(
            self.get_name()))
        for cache_type in Scraper.CACHE_LIST:
            if pdialog is not None:
                pdialog.updateProgress(step_count)
                step_count += 1

            # Skip unloaded caches
            if not self.disk_caches_loaded[cache_type]:
                self.logger.debug('Skipping {} (Unloaded)'.format(cache_type))
                continue
            # Skip empty caches
            if not self.disk_caches[cache_type]:
                self.logger.debug('Skipping {} (Empty)'.format(cache_type))
                continue
            # Skip clean caches.
            if not self.disk_caches_dirty[cache_type]:
                self.logger.debug('Skipping {} (Clean)'.format(cache_type))
                continue

            # Get JSON data.
            json_data = json.dumps(
                self.disk_caches[cache_type], ensure_ascii=False, sort_keys=True,
                indent=Scraper.JSON_indent, separators=Scraper.JSON_separators)

            # Write to disk
            json_file_path, json_fname = self._get_scraper_file_name(cache_type, self.platform)
            file = io.FileName(json_file_path)
            file.writeAll(json_data)
            
            # self.logger.debug('Saved "{}"'.format(json_file_path))
            self.logger.debug('Saved "<SCRAPER_CACHE_DIR>/{}"'.format(json_fname))

            # Cache written to disk is clean gain.
            self.disk_caches_dirty[cache_type] = False

        # --- Global caches ---
        # self.logger.debug('Scraper.flush_disk_cache() Saving scraper {} global disk cache...'.format(
        #         self.get_name()))
        # for cache_type in Scraper.GLOBAL_CACHE_LIST:
        #     if pdialog is not None:
        #         pdialog.updateProgress(step_count)
        #         step_count += 1

        #     # Skip unloaded caches
        #     if not self.global_disk_caches_loaded[cache_type]:
        #         self.logger.debug('Skipping global {} (Unloaded)'.format(cache_type))
        #         continue
        #     # Skip empty caches
        #     if not self.global_disk_caches[cache_type]:
        #         self.logger.debug('Skipping global {} (Empty)'.format(cache_type))
        #         continue
        #     # Skip clean caches.
        #     if not self.global_disk_caches_dirty[cache_type]:
        #         self.logger.debug('Skipping global {} (Clean)'.format(cache_type))
        #         continue

        #     # Get JSON data.
        #     json_data = json.dumps(
        #         self.global_disk_caches[cache_type], ensure_ascii = False, sort_keys = True,
        #         indent = Scraper.JSON_indent, separators = Scraper.JSON_separators)

        #     # Write to disk
        #     json_file_path, json_fname = self._get_global_file_name(cache_type)
        #     file = io.open(json_file_path, 'w', encoding = 'utf-8')
        #     file.write(unicode(json_data))
        #     file.close()
        #     # self.logger.debug('Saved global "{}"'.format(json_file_path))
        #     self.logger.debug('Saved global "<SCRAPER_CACHE_DIR>/{}"'.format(json_fname))

        #     # Cache written to disk is clean gain.
        #     self.global_disk_caches_dirty[cache_type] = False
        if pdialog is not None:
            pdialog.endProgress()

    # Search for candidates and return a list of dictionaries _new_candidate_dic().
    #
    # * This function is never cached. What is cached is the chosen candidate games.
    # * If no candidates found by the scraper return an empty list and status is True.
    # * If there is an error/exception (network error, bad data returned) return None,
    #   the cause is printed in the log, status is False and the status dictionary contains
    #   a user notification.
    # * The number of network error/exceptions is recorded internally by the scraper. If the
    #   number of errors is **bigger than a threshold**, **the scraper is deactivated** (no more
    #   errors reported in the future, just empty data is returned).
    # * If the scraper is overloaded (maximum number of API/web requests) it is considered and
    #   error and the scraper is internally deactivated immediately. The error message associated
    #   with the scraper overloading must be printed once like any other error.
    #
    # @param search_term: [str] String to be searched.
    # @param rom: [ROMObj] Scraper gets the known metadata set to use in searching candidates
    # @param platform: [str] AKL platform.
    # @param status_dic: [dict] kodi_new_status_dic() status dictionary.
    # @return: [list] or None.
    @abc.abstractmethod
    def get_candidates(self, search_term, rom: ROMObj, platform, status_dic):
        pass

    # Returns the metadata for a candidate (search result).
    #
    # * See comments in get_candidates()
    #
    # @param status_dic: [dict] kodi_new_status_dic() status dictionary.
    # @return: [dict] Dictionary self._new_gamedata_dic(). If no metadata found (very unlikely)
    #          then a dictionary with default values is returned. If there is an error/exception
    #          None is returned, the cause printed in the log and status_dic has a message to show.
    @abc.abstractmethod
    def get_metadata(self, status_dic):
        pass

    # Returns a list of assets for a candidate (search result).
    #
    # * See comments in get_candidates()
    #
    # @param status_dic: [dict] kodi_new_status_dic() status dictionary.
    # @return: [list] List of _new_assetdata_dic() dictionaries. If no assets found then an empty
    #          list is returned. If there is an error/exception None is returned, the cause printed
    #          in the log and status_dic has a message to show.
    @abc.abstractmethod
    def get_assets(self, asset_info_id: str, status_dic):
        pass

    # When returning the asset list with get_assets(), some sites return thumbnails images
    # because the real assets are on a single dedicated page. For this sites, resolve_asset_URL()
    # returns the true, full size URL of the asset.
    #
    # Other scrapers, for example MobyGames, return both the thumbnail and the true asset URLs
    # in get_assets(). In such case, the implementation of this method is trivial.
    #
    # @param selected_asset:
    # @param status_dic: [dict] kodi_new_status_dic() status dictionary.
    # @return: [tuple of strings] or None
    #          First item, string with the URL to download the asset.
    #          Second item, string with the URL for printing in logs. URL may have sensitive
    #          information in some scrapers.
    #          None is returned in case of error and status_dic updated.
    @abc.abstractmethod
    def resolve_asset_URL(self, selected_asset, status_dic):
        pass

    # Get the URL image extension. In some scrapers the type of asset cannot be obtained by
    # the asset URL and must be resolved to save the asset in the filesystem.
    #
    # @param selected_asset:
    # @param image_url:
    # @param status_dic: [dict] kodi_new_status_dic() status dictionary.
    # @return: [str] String with the image extension in lowercase 'png', 'jpg', etc.
    #          None is returned in case or error/exception and status_dic updated.
    @abc.abstractmethod
    def resolve_asset_URL_extension(self, selected_asset, image_url, status_dic):
        pass

    # Downloads an image from the given url to the local path.
    # Can overwrite this method in scraper implementation to support extra actions, like
    # request throttling.
    def download_image(self, image_url, image_local_path):
        # net_download_img() never prints URLs or paths.
        net.download_img(image_url, image_local_path)
        return image_local_path

    # Not used now. candidate['id'] is used as hash value for the whole candidate dictionary.
    # candidate['id'] must be unique for each game.
    # def _dictionary_hash(self, my_dict):
    #     return hash(frozenset(sorted(my_dict.items())))

    # Nested dictionaries are not allowed. All the dictionaries here must be "hashable".
    # If your dictionary is not nested, you could make a frozenset with the dict's items
    # and use hash():
    #
    # hash(frozenset(sorted(my_dict.items())))
    #
    # This is much less computationally intensive than generating the JSON string
    # or representation of the dictionary.
    # See https://stackoverflow.com/questions/5884066/hashing-a-dictionary
    def _new_candidate_dic(self):
        return {
            'id': '',
            'display_name': '',
            'platform': '',
            'scraper_platform': '',
            'order': 0,
        }

    def _new_gamedata_dic(self):
        return {
            'title': '',
            'year': '',
            'genre': '',
            'developer': '',
            'nplayers': '',
            'nplayers_online': '',
            'esrb': '',
            'pegi': '',
            'plot': '',
            'tags': [],
            'extra': {}
        }

    # url_thumb is always returned by get_assets().
    # url is returned by resolve_asset_URL().
    # Note that some scrapers (MobyGames) return both url_thumb and url in get_assets(). Always
    # call resolve_asset_URL() for compabilitity with all scrapers.
    def _new_assetdata_dic(self):
        return {
            'asset_ID': None,
            'display_name': '',
            'url_thumb': '',
            'url': '',
            'downloadable': True
        }

    # This functions is called when an error that is not an exception and needs to increase
    # the scraper error limit happens.
    # All messages generated in the scrapers are KODI_MESSAGE_DIALOG.
    def _handle_error(self, status_dic, user_msg):
        # Print error message to the log.
        self.logger.error('Scraper._handle_error() user_msg "{}"'.format(user_msg))

        # Fill in the status dictionary so the error message will be propagated up in the
        # stack and the error message printed in the GUI.
        status_dic['status'] = False
        status_dic['dialog'] = kodi.KODI_MESSAGE_DIALOG
        status_dic['msg'] = user_msg
        
        # Record the number of error/exceptions produced in the scraper and disable the scraper
        # if the number of errors is higher than a threshold.
        self.exception_counter += 1
        if self.exception_counter > Scraper.EXCEPTION_COUNTER_THRESHOLD:
            err_m = 'Maximum number of errors exceeded. Disabling scraper.'
            self.logger.error(err_m)
            self.scraper_disabled = True
            # Replace error message witht the one that the scraper is disabled.
            status_dic['msg'] = err_m

    # This function is called when an exception in the scraper code happens.
    # All messages from the scrapers are KODI_MESSAGE_DIALOG.
    def _handle_exception(self, ex, status_dic, user_msg):
        self.logger.exception(f'(Exception) Message "{user_msg}"')
        self._handle_error(status_dic, user_msg)

    # --- Private disk cache functions -----------------------------------------------------------
    def _get_scraper_file_name(self, cache_type, platform):
        scraper_filename = self.get_filename()
        json_fname = scraper_filename + '__' + platform + '__' + cache_type + '.json'
        json_full_path = self.scraper_cache_dir.pjoin(json_fname).getPath()

        return json_full_path, json_fname

    def _lazy_load_disk_cache(self, cache_type):
        if not self.disk_caches_loaded[cache_type]:
            self._load_disk_cache(cache_type, self.platform)

    def _load_disk_cache(self, cache_type, platform):
        # --- Get filename ---
        json_file_path, json_fname = self._get_scraper_file_name(cache_type, platform)
        self.logger.debug('Scraper._load_disk_cache() Loading cache "{}"'.format(cache_type))

        # --- Load cache if file exists ---
        if os.path.isfile(json_file_path):
            file = open(json_file_path)
            file_contents = file.read()
            file.close()
            self.disk_caches[cache_type] = json.loads(file_contents)
            # self.logger.debug('Loaded "{}"'.format(json_file_path))
            self.logger.debug('Loaded "<SCRAPER_CACHE_DIR>/{}"'.format(json_fname))
        else:
            self.logger.debug('Cache file not found. Resetting cache.')
            self.disk_caches[cache_type] = {}
        self.disk_caches_loaded[cache_type] = True
        self.disk_caches_dirty[cache_type] = False

    # Returns True if item is in the cache, False otherwise.
    # Lazy loads cache files from disk.
    def _check_disk_cache(self, cache_type: str, cache_key: str):
        self._lazy_load_disk_cache(cache_type)

        return True if cache_key in self.disk_caches[cache_type] else False

    # _check_disk_cache() must be called before this.
    def _retrieve_from_disk_cache(self, cache_type: str, cache_key: str):
        return self.disk_caches[cache_type][cache_key]

    # _check_disk_cache() must be called before this.
    def _delete_from_disk_cache(self, cache_type: str, cache_key: str):
        del self.disk_caches[cache_type][cache_key]
        self.disk_caches_dirty[cache_type] = True

    # Lazy loading should be done here because the internal cache for ScreenScraper
    # could be updated withouth being loaded first with _check_disk_cache().
    def _update_disk_cache(self, cache_type: str, cache_key: str, data):
        self._lazy_load_disk_cache(cache_type)
        self.disk_caches[cache_type][cache_key] = data
        self.disk_caches_dirty[cache_type] = True

    # --- Private global disk caches -------------------------------------------------------------
    def _get_global_file_name(self, cache_type: str):
        json_fname = cache_type + '.json'
        json_full_path = self.scraper_cache_dir.pjoin(json_fname).getPath()

        return json_full_path, json_fname

    def _lazy_load_global_disk_cache(self, cache_type):
        if not self.global_disk_caches_loaded[cache_type]:
            self._load_global_cache(cache_type)

    def _load_global_cache(self, cache_type):
        # --- Get filename ---
        json_file_path, json_fname = self._get_global_file_name(cache_type)
        self.logger.debug('Scraper._load_global_cache() Loading cache "{}"'.format(cache_type))

        # --- Load cache if file exists ---
        if os.path.isfile(json_file_path):
            file = open(json_file_path)
            file_contents = file.read()
            file.close()
            self.global_disk_caches[cache_type] = json.loads(file_contents)
            # self.logger.debug('Loaded "{}"'.format(json_file_path))
            self.logger.debug('Loaded "<SCRAPER_CACHE_DIR>/{}"'.format(json_fname))
        else:
            self.logger.debug('Cache file not found. Resetting cache.')
            self.global_disk_caches[cache_type] = {}
        self.global_disk_caches_loaded[cache_type] = True
        self.global_disk_caches_dirty[cache_type] = False

    def _check_global_cache(self, cache_type):
        self._lazy_load_global_disk_cache(cache_type)

        return self.global_disk_caches[cache_type]

    # _check_global_cache() must be called before this.
    def _retrieve_global_cache(self, cache_type):
        return self.global_disk_caches[cache_type]

    # _check_global_cache() must be called before this.
    def _reset_global_cache(self, cache_type):
        self.global_disk_caches[cache_type] = {}
        self.global_disk_caches_dirty[cache_type] = True

    def _update_global_cache(self, cache_type, data):
        self._lazy_load_global_disk_cache(cache_type)
        self.global_disk_caches[cache_type] = data
        self.global_disk_caches_dirty[cache_type] = True

    # Generic waiting method to avoid too many requests
    # and website abuse. 
    def _wait_for_API_request(self, wait_time_in_miliseconds=1000):
        if wait_time_in_miliseconds == 0:
            return
        
        # Make sure we dont go over the TooManyRequests limit of 1 second.
        now = datetime.now()
        if (now - self.last_http_call).total_seconds() * 1000 < wait_time_in_miliseconds:
            self.logger.debug('Scraper._wait_for_API_request() Sleeping {}ms to avoid overloading...'.format(wait_time_in_miliseconds))
            time.sleep(wait_time_in_miliseconds / 1000)


# ------------------------------------------------------------------------------------------------
# NULL scraper, does nothing.
# ------------------------------------------------------------------------------------------------
class Null_Scraper(Scraper):
    def __init__(self):
        super(Null_Scraper, self).__init__(None)

    def get_name(self):
        return 'Null'

    def get_filename(self):
        return 'Null'

    def supports_disk_cache(self):
        return False

    def supports_search_string(self):
        return True

    def supports_metadata_ID(self, metadata_ID):
        return False

    def supports_metadata(self):
        return False

    def supports_asset_ID(self, asset_ID):
        return False

    def supports_assets(self):
        return False

    def check_before_scraping(self, status_dic):
        return status_dic

    # Null scraper never finds candidates.
    def get_candidates(self, search_term, rom_FN, rom_checksums_FN, platform, status_dic):
        return []

    # Null scraper never returns valid scraped metadata.
    def get_metadata(self, status_dic) -> dict:
        return self._new_gamedata_dic()

    def get_assets(self, asset_info_id, status_dic):
        return []

    def resolve_asset_URL(self, selected_asset, status_dic):
        return ('', '')

    def resolve_asset_URL_extension(self, selected_asset, image_url, status_dic):
        return ''

    def download_image(self, image_url, image_local_path):
        return None
