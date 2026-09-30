# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher: Base ROM scanners
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

# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
from __future__ import annotations

import abc
import logging
import re
import typing

# --- AKL packages ---
from akl import report, api, platforms
from akl.utils import io, kodi, text

from akl.api import ROMObj

logger = logging.getLogger(__name__)


class ROMCandidateABC(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def get_ROM(self) -> ROMObj:
        return None
    
    @abc.abstractmethod
    def get_sort_value(self) -> str:
        return None


class MultiDiscInfo:
    def __init__(self, ROM_FN: io.FileName):
        self.ROM_FN = ROM_FN
        self.isMultiDisc = False
        self.setName = ''
        self.discName = ROM_FN.getBase()
        self.extension = ROM_FN.getExt()
        self.order = 0

    @staticmethod
    def get_multidisc_info(ROM_FN: io.FileName) -> MultiDiscInfo:
        MDSet = MultiDiscInfo(ROM_FN)
        
        # --- Parse ROM base_noext into tokens ---
        tokens = text.get_ROM_basename_tokens(ROM_FN.getBaseNoExt())

        # --- Check if ROM belongs to a multidisc set and get set name and order ---
        # Algortihm:
        # 1) Iterate list of tokens
        # 2) If a token marks a multidisk ROM extract set order
        # 3) Define the set basename by removing the multidisk token
        MultDiscFound = False
        for index, token in enumerate(tokens):
            # --- Redump ---
            matchObj = re.match(r'\(Dis[ck] ([0-9]+)\)', token)
            if matchObj:
                logger.debug('get_multidisc_info() ### Matched Redump multidisc ROM ###')
                tokens_idx = list(range(0, len(tokens)))
                tokens_idx.remove(index)
                tokens_nodisc_idx = list(tokens_idx)
                tokens_mdisc = [tokens[x] for x in tokens_nodisc_idx]
                MultDiscFound = True
                break

            # --- TOSEC/Trurip ---
            matchObj = re.match(r'\(Dis[ck] ([0-9]+) of ([0-9]+)\)', token)
            if matchObj:
                logger.debug('get_multidisc_info() ### Matched TOSEC/Trurip multidisc ROM ###')
                tokens_idx = list(range(0, len(tokens)))
                tokens_idx.remove(index)
                tokens_nodisc_idx = list(tokens_idx)
                # logger.debug('text_get_multidisc_info() tokens_idx         = {0}'.format(tokens_idx))
                # logger.debug('text_get_multidisc_info() index              = {0}'.format(index))
                # logger.debug('text_get_multidisc_info() tokens_nodisc_idx  = {0}'.format(tokens_nodisc_idx))
                tokens_mdisc = [tokens[x] for x in tokens_nodisc_idx]
                MultDiscFound = True
                break

        if MultDiscFound:
            MDSet.isMultiDisc = True
            MDSet.setName = ' '.join(tokens_mdisc) + MDSet.extension
            MDSet.order = int(matchObj.group(1))
            logger.debug('get_multidisc_info() base_noext   "{0}"'.format(ROM_FN.getBaseNoExt()))
            logger.debug('get_multidisc_info() tokens       {0}'.format(tokens))
            logger.debug('get_multidisc_info() tokens_mdisc {0}'.format(tokens_mdisc))
            logger.debug('get_multidisc_info() setName      "{0}"'.format(MDSet.setName))
            logger.debug('get_multidisc_info() discName     "{0}"'.format(MDSet.discName))
            logger.debug('get_multidisc_info() extension    "{0}"'.format(MDSet.extension))
            logger.debug('get_multidisc_info() order        {0}'.format(MDSet.order))

        return MDSet


# #################################################################################################
# #################################################################################################
# ROM scanners
# #################################################################################################
# #################################################################################################
class ScannerStrategyABC(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self,
                 source_id: str,
                 webservice_host: str,
                 webservice_port: int,
                 progress_dialog: kodi.ProgressDialog):
        
        self.scanner_settings = {}
        self.progress_dialog = progress_dialog
        
        self.scanned_roms: typing.List[ROMObj] = []
        self.marked_dead_roms: typing.List[ROMObj] = []
        
        self.source_id = source_id
        
        self.webservice_host = webservice_host
        self.webservice_port = webservice_port
        
        self.load_settings()

        super(ScannerStrategyABC, self).__init__()
  
    # --------------------------------------------------------------------------------------------
    # Core methods
    # --------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def get_name(self) -> str:
        return ''
    
    @abc.abstractmethod
    def get_scanner_addon_id(self) -> str:
        return ''

    def get_scanner_settings(self) -> dict:
        return self.scanner_settings
    
    def amount_of_scanned_roms(self) -> int:
        return len(self.scanned_roms)
  
    def amount_of_dead_roms(self) -> int:
        return len(self.marked_dead_roms)
    
    #
    # Configure this scanner.
    #
    @abc.abstractmethod
    def configure(self) -> bool:
        return True

    #
    # Scans for new roms based on the type of launcher.
    #
    @abc.abstractmethod
    def scan(self):
        pass

    #
    # Cleans up ROM source.
    # Remove Remove dead/missing ROMs ROMs
    #
    @abc.abstractmethod
    def cleanup(self):
        pass
        
    #
    # This method will call the AKL webservice to retrieve previously stored scanner settings for a
    # specific source in the database.
    #
    def load_settings(self):
        if self.source_id is None:
            return
        try:
            scanner_settings = api.client_get_source_scanner_settings(
                self.webservice_host,
                self.webservice_port,
                self.source_id)
            
            self.scanner_settings = scanner_settings
        except Exception:
            logger.exception('Failure while loading scanner settings')
            self.scanner_settings = {}
        
    #
    # This method will call the AKL webservice to store scanner settings for a
    # specific source in the database.
    #
    def store_settings(self):
        scanner_settings = self.get_scanner_settings()
        post_data = {
            'source_id': self.source_id,
            'addon_id': self.get_scanner_addon_id(),
            'settings': scanner_settings
        }
        is_stored = api.client_post_scanner_settings(self.webservice_host, self.webservice_port, post_data)
        if not is_stored:
            kodi.notify_error('Failed to store scanner settings')
     
    def store_scanned_roms(self):
        roms = [*(r.get_data_dic() for r in self.scanned_roms)]
        post_data = {
            'source_id': self.source_id,
            'roms': roms
        }
        is_stored = api.client_post_scanned_roms(self.webservice_host, self.webservice_port, post_data)
        if not is_stored:
            kodi.notify_error('Failed to store scanned ROMs')

    def remove_dead_roms(self):
        dead_rom_ids = [*(r.get_id() for r in self.marked_dead_roms)]
        post_data = {
            'source_id': self.source_id,
            'rom_ids': dead_rom_ids
        }
        is_removed = api.client_post_dead_roms(self.webservice_host, self.webservice_port, post_data)
        if not is_removed:
            kodi.notify_error('Failed to remove dead ROMs')


class NullScanner(ScannerStrategyABC):
    
    def get_name(self) -> str:
        return 'NULL'
    
    def get_scanner_addon_id(self) -> str:
        return ''
    
    def configure(self):
        return True
    
    def scan(self):
        pass

    def cleanup(self):
        pass


class RomScannerStrategy(ScannerStrategyABC):
    __metaclass__ = abc.ABCMeta

    def __init__(self,
                 reports_dir: io.FileName,
                 source_id: str,
                 webservice_host: str,
                 webservice_port: int,
                 progress_dialog: kodi.ProgressDialog):
        
        self.reports_dir = reports_dir
        super(RomScannerStrategy, self).__init__(source_id, webservice_host, webservice_port, progress_dialog)

    # --------------------------------------------------------------------------------------------
    # Scanner configuration wizard methods
    # --------------------------------------------------------------------------------------------
    #
    # Builds up the settings for a Scanner
    # Returns True if Scanner was sucesfully built.
    # Returns False if Scanner was not built (user canceled the dialogs or some other
    # error happened).
    #
    def configure(self) -> bool:
        logger.debug('RomScannerStrategy::build() Starting ...')
                
        # --- Call hook before wizard ---
        if not self._configure_pre_wizard_hook():
            return False

        # Empty scanner settings, then start new config wizard
        if not self.scanner_settings:
            # --- Scanner configuration code ---
            wizard = kodi.WizardDialog_Dummy(None, 'addon_id', self.get_scanner_addon_id())
            # >> Call Child class wizard builder method
            wizard = self._configure_get_wizard(wizard)
            # >> Run wizard
            self.scanner_settings = wizard.runWizard(self.scanner_settings)
            if not self.scanner_settings:
                return False
        else:
            if not self.edit():
                return False
            if not kodi.dialog_yesno('Save scanner changes?'):
                return False

        # --- Call hook after wizard ---
        if not self._configure_post_wizard_hook():
            return False

        return True

    def edit(self) -> bool:
        # Edit mode. Show options dialog
        edit_options = self._configure_get_edit_options()
        if edit_options is None:
            logger.debug('No edit options. Cancelling')
            return False

        edit_dialog = kodi.OrdDictionaryDialog()
        t = f'Edit {self.get_name()} settings'
        selected_option = edit_dialog.select(t, edit_options)
        
        if selected_option is None:
            return True  # short circuit
        
        selected_option()  # execute
        return self.edit()  # recursive call
        
    def scan(self, suppress_empty_warning=False):
               
        # --- Open ROM scanner report file ---
        launcher_report = report.FileReporter(self.reports_dir, self.get_name(), report.LogReporter())
        launcher_report.open()
        
        # >> Check if we already have existing ROMs
        launcher_report.write('Loading existing ROMs ...')
        try:
            roms = api.client_get_roms_in_source(self.webservice_host, self.webservice_port, self.source_id)
        except Exception:
            logger.exception('Failure retrieving existing ROMs')
            roms = []
        
        num_roms = len(roms)
        launcher_report.write(f'{num_roms} ROMs currently in database for this source.')
        
        launcher_report.write('Collecting candidates ...')
        candidates = self._getCandidates(launcher_report)
        num_candidates = len(candidates) if candidates else 0
        launcher_report.write(f'{num_candidates} candidates found')
        
        launcher_report.write('Checking for dead ROMs ...')
        dead_roms = self._getDeadRoms(candidates, roms)
        num_dead_roms = len(dead_roms)

        if num_dead_roms > 0:
            kodi.notify(f'{num_dead_roms} dead ROMs found')
            logger.info(f'{num_dead_roms} dead ROMs found')
        else:
            logger.info('No dead ROMs found')
        
        self.marked_dead_roms = dead_roms
        
        # --- Prepare list of candidates to be processed ----------------------------------------------
        # List has candidates. List already sorted alphabetically.
        candidates = sorted(candidates, key=lambda c: c.get_sort_value())
        new_roms = self._processFoundItems(candidates, roms, launcher_report)
        
        if not new_roms and not dead_roms and roms:
            return

        num_new_roms = len(new_roms)
        roms = roms + new_roms
        self.scanned_roms = new_roms

        launcher_report.write('******************** ROM scanner finished. Report ********************')
        launcher_report.write('Files checked       {0:6d}'.format(num_candidates))
        launcher_report.write('Dead ROMs           {0:6d}'.format(num_dead_roms))
        launcher_report.write('New ROMs            {0:6d}'.format(num_new_roms))
        
        if len(roms) == 0:
            launcher_report.write('WARNING ROMs has no ROMs!')
            launcher_report.close()

            if not suppress_empty_warning:
                kodi.dialog_OK(
                    'No ROMs found! Make sure ROM set directory and file extensions are correct.'
                )

            return
        
        if num_new_roms == 0:
            kodi.notify(f'Added no new ROMs. ROM set has {len(roms)} ROMs')
        else:
            kodi.notify(f'Added {num_new_roms} new ROMs')

        # --- Close ROM scanner report file ---
        launcher_report.write('*** END of the ROM scanner report ***')
        launcher_report.close()

    def cleanup(self):
        launcher_report = report.FileReporter(self.reports_dir, self.get_name(), report.LogReporter())
        launcher_report.open()
        launcher_report.write('Dead ROM Cleaning operation')
        
        try:
            roms = api.client_get_roms_in_source(self.webservice_host, self.webservice_port, self.source_id)
        except Exception:
            logger.exception('Failure retrieving existing ROMs')
            roms = []
        
        if roms is None:
            launcher_report.close()
            logger.info('No roms available to cleanup')
            return {}
              
        num_roms = len(roms)
        launcher_report.write(f'{num_roms} ROMs currently in database for this source.')
        
        launcher_report.write('Collecting candidates ...')
        candidates = self._getCandidates(launcher_report)
        num_candidates = len(candidates)
        logger.info(f'{num_candidates} candidates found')

        launcher_report.write('Checking for dead ROMs ...')
        dead_roms = self._getDeadRoms(candidates, roms)
        num_dead_roms = len(dead_roms)

        if num_dead_roms > 0:
            kodi.notify(f'{num_dead_roms} dead ROMs found')
            logger.info(f'{num_dead_roms} dead ROMs found')
        else:
            logger.info('No dead ROMs found')

        self.marked_dead_roms = dead_roms
        launcher_report.close()
        return roms
    
    #
    # Creates a new scanner using a wizard of dialogs.
    # Child concrete classes must implement this method.
    #
    @abc.abstractmethod
    def _configure_get_wizard(self, wizard) -> kodi.WizardDialog:
        pass

    @abc.abstractmethod
    def _configure_get_edit_options(self) -> dict:
        pass
    
    # ~~~ Pre & Post configuration hooks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @abc.abstractmethod
    def _configure_pre_wizard_hook(self):
        return True

    @abc.abstractmethod
    def _configure_post_wizard_hook(self):
        return True

    # ---------------------------------------------------------------------------------------------
    # Execution methods
    # ---------------------------------------------------------------------------------------------
    # ~~~ Scan for new files (*.*) and put them in a list ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @abc.abstractmethod
    def _getCandidates(self, launcher_report: report.Reporter) -> typing.List[ROMCandidateABC]:
        return []

    # --- Get dead entries -----------------------------------------------------------------
    @abc.abstractmethod
    def _getDeadRoms(self, candidates: typing.List[ROMCandidateABC], roms: typing.List[ROMObj]) -> typing.List[ROMObj]:
        return []

    # ~~~ Now go processing item by item ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @abc.abstractmethod
    def _processFoundItems(self,
                           candidates: typing.List[ROMCandidateABC],
                           roms: typing.List[ROMObj],
                           launcher_report: report.Reporter) -> typing.List[ROMObj]:
        return []

    def configuration_get_extensions_from_launchers(self, input, item_key, scanner_settings):
        if input:
            return input
        extensions = scanner_settings[item_key] if item_key in scanner_settings else ''
        if extensions != '':
            return extensions
        
        if self.source_id:
            extensions_by_launchers = []
            launchers = api.client_get_source_launchers(self.webservice_host, self.webservice_port, self.source_id)
            for key, launcher_settings in launchers.items():
                if 'application' in launcher_settings:
                    app = launcher_settings['application']
                    appPath = io.FileName(app)
                    launcher_extensions = platforms.emudata_get_program_extensions(appPath.getBase())
                    if launcher_extensions != '':
                        extensions_by_launchers.append(launcher_extensions)
                        
                if 'scanners' in launcher_settings:
                    if 'romext' in launcher_settings['scanners']:
                        extensions_by_launchers = launcher_settings['scanners']['romext'].split('|')
                
            if len(extensions_by_launchers) > 0:
                extensions = '|'.join(extensions_by_launchers)
            else:
                extensions = ''
            
        return extensions
