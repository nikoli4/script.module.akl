# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher: Base launchers
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

import abc
import collections
import logging
import shlex
import typing

import xbmc

# --- AKL packages ---
from akl import settings, api
from akl.utils import io, kodi
from akl.executors import ExecutorSettings, ExecutorFactory, ExecutorFactoryABC, ExecutorABC

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------------------------------
# Helper methods
# -------------------------------------------------------------------------------------------------
def get_executor_factory(report_file_path: io.FileName) -> ExecutorFactoryABC:
    executorSettings = ExecutorSettings()
    executorSettings.lirc_state = settings.getSettingAsBool('lirc_state')
    executorSettings.show_batch_window = settings.getSettingAsBool('show_batch_window')
    executorSettings.windows_cd_apppath = settings.getSettingAsBool('windows_cd_apppath')
    executorSettings.windows_close_fds = settings.getSettingAsBool('windows_close_fds')
    
    executorFactory = ExecutorFactory(report_file_path, executorSettings)
    return executorFactory


class ExecutionSettings(object):
    is_non_blocking = True
    toggle_window = False
    display_launcher_notify = True
    media_state_action = 0  # id="media_state_action" default="0" values="Stop|Pause|Let Play"
    suspend_audio_engine = False
    suspend_screensaver = True
    suspend_joystick_engine = False
    delay_tempo = 1000


# -------------------------------------------------------------------------------------------------
# Abstract base class for launching anything that is supported.
# Implement classes that inherit this base class to support new ways of launching.
# -------------------------------------------------------------------------------------------------
class LauncherABC(object):
    __metaclass__ = abc.ABCMeta

    #
    # In an abstract class launcher_data is mandatory.
    #
    def __init__(self,
                 launcher_id: str,
                 rom_id: str,
                 webservice_host: str,
                 webservice_port: int,
                 executorFactory: ExecutorFactoryABC = None,
                 execution_settings: ExecutionSettings = None,
                 entity_type: int = None):

        self.launcher_settings = {
            'name': self.get_name()
        }
        
        self.launcher_id = launcher_id
        self.rom_id = rom_id
        self.entity_type = entity_type
        
        self.webservice_host = webservice_host
        self.webservice_port = webservice_port

        self.executorFactory = executorFactory
        self.execution_settings = execution_settings
        
        self.load_settings()
        
    # --------------------------------------------------------------------------------------------
    # Core methods
    # --------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def get_name(self) -> str:
        return ''
    
    def get_instance_name(self) -> str:
        if not self.launcher_settings:
            return ''
        return self.launcher_settings['name'] if 'name' in self.launcher_settings else ''
    
    @abc.abstractmethod
    def get_launcher_addon_id(self) -> str:
        return ''

    def get_launcher_settings(self) -> dict:
        return self.launcher_settings

    def configure_executor(self,
                           executorFactory: ExecutorFactoryABC,
                           execution_settings: ExecutionSettings):
        self.executorFactory = executorFactory
        self.execution_settings = execution_settings

    # --------------------------------------------------------------------------------------------
    # Launcher build wizard methods
    # --------------------------------------------------------------------------------------------
    #
    # Builds a new Launcher or edits an existing one.
    # Returns True if Launcher  was sucesfully built.
    # Returns False if Launcher was not built (user canceled the dialogs or some other
    # error happened).
    #
    def build(self) -> bool:
        logger.debug('LauncherABC::build() Starting ...')
                
        # --- Call hook before wizard ---
        if not self._build_pre_wizard_hook():
            return False

        # >> Call Child class wizard builder method
        if self.launcher_id is None:
            # --- Launcher build code (ask user about launcher stuff) ---
            wizard = kodi.WizardDialog_Dummy(None, 'addon_id', self.get_launcher_addon_id())
            wizard = kodi.WizardDialog_Keyboard(wizard, 'name', 'Launcher name')
            wizard = self._builder_get_wizard(wizard)
            # >> Run wizard
            self.launcher_args = wizard.runWizard(self.launcher_settings)
            if not self.launcher_settings:
                return False
        else:
            if not self.edit():
                return False
            if not kodi.dialog_yesno('Save launcher changes?'):
                return False
        
        # --- Call hook after wizard ---
        if not self._build_post_wizard_hook():
            return False
        return True

    def edit(self) -> bool:
        # Edit mode. Show options dialog
        edit_options = self._builder_get_edit_options()
        if edit_options is None:
            return False

        edit_dialog = kodi.OrdDictionaryDialog()
        t = f'Edit {self.get_name()} settings'
        selected_option = edit_dialog.select(t, edit_options)
        
        if selected_option is None:
            return True
        
        selected_option()  # execute
        return self.edit()  # recursive call
    
    #
    # Creates a new launcher using a wizard of dialogs.
    # Child concrete classes must implement this method.
    #
    @abc.abstractmethod
    def _builder_get_wizard(self, wizard) -> kodi.WizardDialog:
        pass

    @abc.abstractmethod
    def _builder_get_edit_options(self) -> dict:
        options = collections.OrderedDict()
        options[self._change_name] = f'Change display name ({self.get_instance_name()})'
        return options

    @abc.abstractmethod
    def _build_pre_wizard_hook(self):
        return True

    @abc.abstractmethod
    def _build_post_wizard_hook(self):
        return True

    def _builder_get_appbrowser_filter(self, item_key, launcher):
        if item_key in launcher:
            application = launcher[item_key]
            if application == 'JAVA':
                return '.jar'

        return '.bat|.exe|.cmd|.lnk' if io.is_windows() else ''

    def _change_name(self):
        current_name = self.get_instance_name()
        new_name = kodi.dialog_keyboard("Launcher name", current_name)
        if not new_name:
            return
        self.launcher_settings['name'] = new_name

    #
    # Wizard helper, when a user wants to set a custom value instead of the predefined list items.
    #
    def _builder_user_selected_custom_browsing(self, item_key, launcher):
        return launcher[item_key] == 'BROWSE'
    
    #
    # This method will call the AKL webservice to retrieve previously stored launcher settings.
    #
    def load_settings(self):
        if self.launcher_id is None:
            return
        try:
            self.launcher_settings = api.client_get_launcher_settings(self.webservice_host, self.webservice_port, self.launcher_id)
        except Exception:
            logger.exception('Failure while loading launcher settings')
            self.launcher_settings = {}
        
    #
    # This method will call the AKL webservice to store launcher settings
    # in the database with the given launcher id. If no launcher id specified
    # it will create a new instance.
    #
    def store_settings(self):
        launcher_settings = self.get_launcher_settings()
        post_data = {
            'launcher_id': self.launcher_id,
            'addon_id': self.get_launcher_addon_id(),
            'settings': launcher_settings
        }

        if self.entity_type is not None:
            post_data['entity_type'] = self.entity_type
            post_data['entity_id'] = self.rom_id

        is_stored = api.client_post_launcher_settings(self.webservice_host, self.webservice_port, post_data)
        if not is_stored:
            kodi.notify_error('Failed to store launchers settings')
           
    # ---------------------------------------------------------------------------------------------
    # Execution methods
    # ---------------------------------------------------------------------------------------------
    #
    # Launchs a custom launcher.
    # Arguments are those send through the URI.
    #
    @abc.abstractmethod
    def launch(self):
        logger.debug('LauncherABC::launch() Starting ...')

        name = self.get_name()
        args, kwargs = self.get_arguments()
        application = self.get_application()
        inst_name = self.get_instance_name()

        logger.debug(f'Name         = "{name}"')
        logger.debug(f'Instance     = "{inst_name}"')
        logger.debug(f'Application  = "{application}"')
        logger.debug(f'Arguments    = "{args}"')
        logger.debug(f'Keyword Args = "{kwargs}"')

        # --- Create executor object ---
        if self.executorFactory is None:
            logger.error('LauncherABC::launch() self.executorFactory is None')
            logger.error(f'Cannot create an executor for {name}')
            kodi.notify_error('LauncherABC::launch() self.executorFactory is None'
                              'This is a bug, please report it.')
            return
        
        executor = self.get_executor(application)
        if executor is None:
            logger.error(f'Cannot create an executor for {name}')
            kodi.notify_error('Cannot execute application')
            return
        logger.debug(f'Executor    = "{executor.__class__.__name__}"')

        # --- Execute app ---
        self._launch_pre_exec(self.get_name(), self.execution_settings.toggle_window)
        executor.execute(application, *args, **kwargs)
        self._launch_post_exec(self.execution_settings.toggle_window)

    @abc.abstractmethod
    def get_executor(self, application: str) -> ExecutorABC:
        """Returns the Executor instance to use when launching."""
        executor = self.executorFactory.create(application)
        return executor
    
    @abc.abstractmethod
    def get_application(self) -> str:
        return self.launcher_settings['application'] if 'application' in self.launcher_settings else None
    
    @abc.abstractmethod
    def get_arguments(self, *args, **kwargs) -> typing.Tuple[list, dict]:
        """
        Combines given arguments and arguments from the launcher_settings dictionary and
        returns them as a list or dictionary in case of keyworded arguments.
        Goes through all the argument and replaces any tokenized (e.g. $<token>$)
        with a corresponding value.
        """
        raw_args = self.launcher_settings['args'] if 'args' in self.launcher_settings else ''
        application = self.get_application()
        
        logger.info(f'get_arguments(): Launcher          "{self.get_name()}"')
        logger.info(f'get_arguments(): raw arguments     "{raw_args}"')
        
        arguments = shlex.split(raw_args, posix=True)
        arguments = arguments + list(args)

        # ROM based arguments replacements
        rom = api.client_get_rom(self.webservice_host, self.webservice_port, self.rom_id)
        rom_file = rom.get_scanned_data_element_as_file('file')
        if rom_file:
            # --- Escape quotes and double quotes in ROMFileName ---
            # >> This maybe useful to Android users with complex command line arguments
            if settings.getSettingAsBool('escape_romfile'):
                logger.info("get_arguments(): Escaping ROMFileName ' and \"")
                rom_file.escapeQuotes()

            rompath = rom_file.getDir()
            rombase = rom_file.getBase()
            rombase_noext = rom_file.getBaseNoExt()

            logger.info(f'get_arguments(): romfile      "{rom_file.getPath()}"')
            logger.info(f'get_arguments(): rompath      "{rompath}"')
            logger.info(f'get_arguments(): rombase      "{rombase}"')
            logger.info(f'get_arguments(): rombasenoext "{rombase_noext}"')

            arguments = self._replace_in_args(arguments, '$rom$', rom_file.getPath())
            arguments = self._replace_in_args(arguments, '$romfile$', rom_file.getPath())
            arguments = self._replace_in_args(arguments, '$rompath$', rompath)
            arguments = self._replace_in_args(arguments, '$rombase$', rombase)
            arguments = self._replace_in_args(arguments, '$rombasenoext$', rombase_noext)
            arguments = self._replace_in_args(arguments, '$ROM$', rom_file.getPath())
            arguments = self._replace_in_args(arguments, '$ROMFILE$', rom_file.getPath())
            arguments = self._replace_in_args(arguments, '$ROMPATH$', rompath)
            arguments = self._replace_in_args(arguments, '$ROMBASE$', rombase)
            arguments = self._replace_in_args(arguments, '$ROMBASENOEXT$', rombase_noext)

            kwargs = self._replace_in_kwargs(kwargs, '$rom$', rom_file.getPath())
            kwargs = self._replace_in_kwargs(kwargs, '$romfile$', rom_file.getPath())
            kwargs = self._replace_in_kwargs(kwargs, '$rompath$', rompath)
            kwargs = self._replace_in_kwargs(kwargs, '$rombase$', rombase)
            kwargs = self._replace_in_kwargs(kwargs, '$rombasenoext$', rombase_noext)
            kwargs = self._replace_in_kwargs(kwargs, '$ROM$', rom_file.getPath())
            kwargs = self._replace_in_kwargs(kwargs, '$ROMFILE$', rom_file.getPath())
            kwargs = self._replace_in_kwargs(kwargs, '$ROMPATH$', rompath)
            kwargs = self._replace_in_kwargs(kwargs, '$ROMBASE$', rombase)
            kwargs = self._replace_in_kwargs(kwargs, '$ROMBASENOEXT$', rombase_noext)

            if application:
                application = application.replace('$rom$', rom_file.getPath())
                application = application.replace('$romfile$', rom_file.getPath())
                application = application.replace('$rompath$', rompath)
                application = application.replace('$rombase$', rombase)
                application = application.replace('$rombasenoext$', rombase_noext)
                application = application.replace('$ROM$', rom_file.getPath())
                application = application.replace('$ROMFILE$', rom_file.getPath())
                application = application.replace('$ROMPATH$', rompath)
                application = application.replace('$ROMBASE$', rombase)
                application = application.replace('$ROMBASENOEXT$', rombase_noext)
                self.launcher_settings['application'] = application

            # >> Legacy names for argument substitution
            arguments = self._replace_in_args(arguments, '%rom%', rom_file.getPath())
            arguments = self._replace_in_args(arguments, '%ROM%', rom_file.getPath())

            kwargs = self._replace_in_kwargs(kwargs, '%rom%', rom_file.getPath())
            kwargs = self._replace_in_kwargs(kwargs, '%ROM%', rom_file.getPath())

        # Application based arguments replacements
        if application:
            app = io.FileName(application)
            apppath = app.getDir()

            logger.info('get_arguments(): application  "{0}"'.format(app.getPath()))
            logger.info('get_arguments(): appbase      "{0}"'.format(app.getBase()))
            logger.info('get_arguments(): apppath      "{0}"'.format(apppath))

            arguments = self._replace_in_args(arguments, '$apppath$', apppath)
            arguments = self._replace_in_args(arguments, '$appbase$', app.getBase())
            arguments = self._replace_in_args(arguments, '$APPPATH$', apppath)
            arguments = self._replace_in_args(arguments, '$APPBASE$', app.getBase())

            kwargs = self._replace_in_kwargs(kwargs, '$apppath$', apppath)
            kwargs = self._replace_in_kwargs(kwargs, '$appbase$', app.getBase())
            kwargs = self._replace_in_kwargs(kwargs, '$APPPATH$', apppath)
            kwargs = self._replace_in_kwargs(kwargs, '$APPBASE$', app.getBase())
        
        # Default arguments replacements
        arguments = self._replace_in_args(arguments, '$romID$', rom.get_id())
        arguments = self._replace_in_args(arguments, '$romtitle$', rom.get_name())

        kwargs = self._replace_in_kwargs(kwargs, '$romID$', rom.get_id())
        kwargs = self._replace_in_kwargs(kwargs, '$romtitle$', rom.get_name())

        # automatic substitution of rom values
        rom_data = rom.get_data_dic()
        for rom_key, rom_value in rom_data.items():
            try:
                arguments = self._replace_in_args(arguments, f"${str(rom_key)}$", str(rom_value))
            except Exception:
                pass
            try:
                kwargs = self._replace_in_kwargs(kwargs, f"${str(rom_key)}$", str(rom_value))
            except Exception:
                pass

        scanned_data = rom.get_scanned_data()
        for scanned_key, scanned_value in scanned_data.items():
            try:
                arguments = self._replace_in_args(arguments, f"${str(scanned_key)}$", str(scanned_value))
            except Exception:
                pass
            try:
                kwargs = self._replace_in_kwargs(kwargs, f"${str(scanned_key)}$", str(scanned_value))
            except Exception:
                pass
                
        # automatic substitution of launcher setting values
        for launcher_key, launcher_value in self.launcher_settings.items():
            try:
                arguments = self._replace_in_args(arguments, f"${str(launcher_key)}$", str(launcher_value))
            except Exception:
                pass
            try:
                kwargs = self._replace_in_kwargs(kwargs, f"${str(launcher_key)}$", str(launcher_value))
            except Exception:
                pass

        if not self.execution_settings.is_non_blocking:
            kwargs["non_blocking"] = self.execution_settings.is_non_blocking
        
        logger.debug(f'get_arguments(): final arguments "{arguments}"')
        logger.debug(f'get_arguments(): final keyworded arguments "{kwargs}"')
        return (arguments, kwargs)
        
    #
    # These two functions do things like stopping music before lunch, toggling full screen, etc.
    # Variables set in this function:
    # self.kodi_was_playing      True if Kodi player was ON, False otherwise
    # self.kodi_audio_suspended  True if Kodi audio suspended before launching
    #
    def _launch_pre_exec(self, title, toggle_screen_flag):
        logger.debug('LauncherABC::_launch_pre_exec() Starting ...')

        # --- User notification ---
        if self.execution_settings.display_launcher_notify:
            kodi.notify(f'Launching {title}')

        # --- Stop/Pause Kodi mediaplayer if requested in settings ---
        self.kodi_was_playing = False
        # id="media_state_action" default="0" values="Stop|Pause|Let Play"
        media_state_action = self.execution_settings.media_state_action
        media_state_str = ['Stop', 'Pause', 'Let Play'][media_state_action]
        logger.debug('_launch_pre_exec() media_state_action is "{}" ({})'.format(media_state_str, media_state_action))
        if media_state_action == 0 and xbmc.Player().isPlaying():
            logger.debug('_launch_pre_exec() Calling xbmc.Player().stop()')
            xbmc.Player().stop()
            xbmc.sleep(100)
            self.kodi_was_playing = True
        elif media_state_action == 1 and xbmc.Player().isPlaying():
            logger.debug('_launch_pre_exec() Calling xbmc.Player().pause()')
            xbmc.Player().pause()
            xbmc.sleep(100)
            self.kodi_was_playing = True

        # --- Force audio suspend if requested in "Settings" --> "Advanced"
        # >> See http://forum.kodi.tv/showthread.php?tid=164522
        self.kodi_audio_suspended = False
        if self.execution_settings.suspend_audio_engine:
            logger.debug('_launch_pre_exec() Suspending Kodi audio engine')
            xbmc.audioSuspend()
            xbmc.enableNavSounds(False)
            xbmc.sleep(100)
            self.kodi_audio_suspended = True
        else:
            logger.debug('_launch_pre_exec() DO NOT suspend Kodi audio engine')

        # --- Force joystick suspend if requested in "Settings" --> "Advanced"
        # >> See https://forum.kodi.tv/showthread.php?tid=287826&pid=2627128#pid2627128
        # >> See https://forum.kodi.tv/showthread.php?tid=157499&pid=1722549&highlight=input.enablejoystick#pid1722549
        # >> See https://forum.kodi.tv/showthread.php?tid=313615
        self.kodi_joystick_suspended = False
        if self.execution_settings.suspend_joystick_engine:
            logger.debug('_launch_pre_exec() Suspending Kodi joystick engine')
            response = kodi.jsonrpc_query("Settings.SetSettingValue", {"setting": "input.enablejoystick", "value": False})
            logger.debug(f"Response  '{response}'")
            self.kodi_joystick_suspended = True
            logger.error('_launch_pre_exec() Suspending Kodi joystick engine not supported on Kodi Krypton!')
        else:
            logger.debug('_launch_pre_exec() DO NOT suspend Kodi joystick engine')

        # --- Toggle Kodi windowed/fullscreen if requested ---
        if toggle_screen_flag:
            logger.debug('_launch_pre_exec() Toggling Kodi fullscreen')
            kodi.toggle_fullscreen()
        else:
            logger.debug('_launch_pre_exec() Toggling Kodi fullscreen DEACTIVATED in Launcher')

        # Disable screensaver
        if self.execution_settings.suspend_screensaver:
            kodi.disable_screensaver()
        else:
            screensaver_mode = kodi.get_screensaver_mode()
            logger.debug(f'_launch_pre_exec() Screensaver status "{screensaver_mode}"')

        # --- Pause Kodi execution some time ---
        delay_tempo_ms = self.execution_settings.delay_tempo
        logger.debug(f'_launch_pre_exec() Pausing {delay_tempo_ms} ms')
        xbmc.sleep(delay_tempo_ms)
        logger.debug('LauncherABC::_launch_pre_exec() function ENDS')

    def _launch_post_exec(self, toggle_screen_flag):
        logger.debug('LauncherABC::_launch_post_exec() Starting ...')

        # --- Stop Kodi some time ---
        delay_tempo_ms = self.execution_settings.delay_tempo
        logger.debug(f'_launch_post_exec() Pausing {delay_tempo_ms} ms')
        xbmc.sleep(delay_tempo_ms)

        # --- Toggle Kodi windowed/fullscreen if requested ---
        if toggle_screen_flag:
            logger.debug('_launch_post_exec() Toggling Kodi fullscreen')
            kodi.toggle_fullscreen()
        else:
            logger.debug('_launch_post_exec() Toggling Kodi fullscreen DEACTIVATED in Launcher')

        # --- Resume audio engine if it was suspended ---
        # Calling xmbc.audioResume() takes a loong time (2/4 secs) if audio was not properly suspended!
        # Also produces this in Kodi's log:
        # WARNING: CActiveAE::StateMachine - signal: 0 from port: OutputControlPort not handled for state: 7
        #   ERROR: ActiveAE::Resume - failed to init
        if self.kodi_audio_suspended:
            logger.debug('_launch_post_exec() Kodi audio engine was suspended before launching')
            logger.debug('_launch_post_exec() Resuming Kodi audio engine')
            xbmc.audioResume()
            xbmc.enableNavSounds(True)
            xbmc.sleep(100)
        else:
            logger.debug('_launch_post_exec() DO NOT resume Kodi audio engine')

        # --- Resume joystick engine if it was suspended ---
        if self.kodi_joystick_suspended:
            logger.debug('_launch_post_exec() Kodi joystick engine was suspended before launching')
            logger.debug('_launch_post_exec() Resuming Kodi joystick engine')
            response = kodi.jsonrpc_query("Settings.SetSettingValue", {"setting": "input.enablejoystick", "value": True})
            logger.debug(f"Response  '{response}'")
            logger.debug('_launch_post_exec() Not supported on Kodi Krypton!')
        else:
            logger.debug('_launch_post_exec() DO NOT resume Kodi joystick engine')

        # Restore screensaver status.
        if self.execution_settings.suspend_screensaver:
            kodi.restore_screensaver()
        else:
            screensaver_mode = kodi.get_screensaver_mode()
            logger.debug(f'_launch_post_exec() Screensaver status "{screensaver_mode}"')

        # --- Resume Kodi playing if it was paused. If it was stopped, keep it stopped. ---
        media_state_action = self.execution_settings.media_state_action
        media_state_str = ['Stop', 'Pause', 'Let Play'][media_state_action]
        logger.debug('_launch_post_exec() media_state_action is "{}" ({})'.format(media_state_str, media_state_action))
        logger.debug('_launch_post_exec() self.kodi_was_playing is {}'.format(self.kodi_was_playing))
        if self.kodi_was_playing and media_state_action == 1:
            logger.debug('_launch_post_exec() Calling xbmc.Player().play()')
            xbmc.Player().play()
        logger.debug('LauncherABC::_launch_post_exec() function ENDS')

    def _replace_in_args(self, args: typing.List[str], to_be_replaced: str, replace_with: str) -> list:
        if replace_with is None:
            return args
        result = [arg.replace(to_be_replaced, replace_with) for arg in args]
        return result

    def _replace_in_kwargs(self, kwargs: typing.Dict[str, str], to_be_replaced: str, replace_with: str) -> dict:
        if replace_with is None:
            return kwargs
        result = {key: val.replace(to_be_replaced, replace_with) for key, val in kwargs.items()}
        return result
