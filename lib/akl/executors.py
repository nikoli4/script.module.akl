# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher: Executors
#
# Copyright (c) Chrisism <crizizz@gmail.com>
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
import subprocess
import webbrowser
import logging
import re
import json
import os

import xbmc

from akl.utils import io
from akl.utils import kodi

logger = logging.getLogger(__name__)

NON_BLOCKING_KEYWORD = "non_blocking"
SEPARATOR_KEYWORD = "separator"

DEFAULT_KEYWORDS = [
    NON_BLOCKING_KEYWORD,
    SEPARATOR_KEYWORD
]


# #################################################################################################
# #################################################################################################
# Executors
# #################################################################################################
# #################################################################################################
class ExecutorABC():
    __metaclass__ = abc.ABCMeta

    def __init__(self, logFile: io.FileName = None):
        self.logFile = logFile

    @abc.abstractmethod
    def execute(self, application: str, *args, **kwargs):
        """
        Executes an application with this executor implementation.
        For the kwargs by default we work with the keyword 'non_blocking'
        to indicate if Kodi should wait/freeze for this executing application.
        By default the application will be treated as non blocking.
        With the keyword 'separator' you can define the separator character
        to use when combining all keywords. By default we use a whitespace.
        The other arguments (args and kwargs) will be processed as the
        arguments for the execution.
        """
        pass


class XbmcExecutor(ExecutorABC):
    """
    Execute Kodi built-in functions.
    """
    
    def execute(self, application: str, *args, **kwargs):
        non_blocking = kwargs.get(NON_BLOCKING_KEYWORD, True)
        separator = kwargs.get(SEPARATOR_KEYWORD, " ")
       
        arguments = list(args)
        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                arguments.append(f'"{key}{separator}{value}"' if value else key)

        if len(arguments) > 0:
            args_string = ", ".join(arguments)
            xbmc.executebuiltin(f'{application}({args_string})', wait=not non_blocking)
        else:
            xbmc.executebuiltin(application, wait=not non_blocking)


#
# --- Linux ---
# New in AEL 0.9.7: always close all file descriptions except 0, 1 and 2 on the child
# process. This is to avoid Kodi opens sockets be inherited by the child process. A
# wrapper script may terminate Kodi using JSON RPC and if file descriptors are not
# closed Kodi will complain that the remote interfacte cannot be initialised. I believe
# the cause is that the socket is kept open by the wrapper script.
#
class LinuxExecutor(ExecutorABC):
    def __init__(self, logFile: io.FileName, lirc_state: bool):
        self.lirc_state = lirc_state
        super(LinuxExecutor, self).__init__(logFile)

    def execute(self, application: str, *args, **kwargs):
        logger.debug('LinuxExecutor::execute() Starting ...')
        command = [application] + list(args)
    
        non_blocking = kwargs.get(NON_BLOCKING_KEYWORD, True)
        separator = kwargs.get(SEPARATOR_KEYWORD, " ")

        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                command.append(f"{key}{separator}{value}" if value else key)

        # >> New way of launching, uses subproces module. Also, save child process stdout.
        if non_blocking:
            # >> In a non-blocking launch stdout/stderr of child process cannot be recorded.
            logger.info('Launching non-blocking process subprocess.Popen()')
            subprocess.Popen(command, close_fds=True)
        else:
            if self.lirc_state:
                xbmc.executebuiltin('LIRC.stop')
            with open(self.logFile.getPathTranslated(), 'w') as f:
                retcode = subprocess.call(
                    command, stdout=f, stderr=subprocess.STDOUT, close_fds=True)
            logger.info(f'Process retcode = {retcode}')
            if self.lirc_state:
                xbmc.executebuiltin('LIRC.start')
        logger.debug('LinuxExecutor::execute() function ENDS')


class AndroidExecutor(ExecutorABC):
    """
    Launch an Android native app.
    It will use the "/system/bin/am start <PACKAGE/ACTIVITY INTENT> .." shell execution to launch
    the android app. The combination of the application, *args and *kwargs will build up this complete
    command. The "am start" part of the command is fixed with the executor.

    execute() parameters:
    - application (type: str)     : the app package/activity you want to execute (e.g. com.android.chrome or com.retroarch/com.retroarch.browser.retroactivity.RetroActivityFuture)
    - *args                       : each arg in this list will be added as a -e argument to the am cmd
    - **kwargs                    : keyed arguments to provide the -a, -d, -t, -c arguments.

    The kwargs can be set with:
    "intent"    : The intent action like 'android.intent.action.VIEW', added as the -a parameter
    "dataURI"   : The data uri for the -d parameter, like 'http://kodi.tv'
    "dataType"  : The mime type, applied as the -t parameter
    "category"  : The category, applied as a -c parameter. Provide as array for multiple categories.
    
    The original system/am start parameters.
    <INTENT> specifications include these flags and arguments:
        [-a <ACTION>] [-d <DATA_URI>] [-t <MIME_TYPE>]
        [-c <CATEGORY> [-c <CATEGORY>] ...]
        [-e|--es <EXTRA_KEY> <EXTRA_STRING_VALUE> ...]
        [--esn <EXTRA_KEY> ...]
        [--ez <EXTRA_KEY> <EXTRA_BOOLEAN_VALUE> ...]
        [--ei <EXTRA_KEY> <EXTRA_INT_VALUE> ...]
        [--el <EXTRA_KEY> <EXTRA_LONG_VALUE> ...]
        [--ef <EXTRA_KEY> <EXTRA_FLOAT_VALUE> ...]
        [--eu <EXTRA_KEY> <EXTRA_URI_VALUE> ...]
        [--ecn <EXTRA_KEY> <EXTRA_COMPONENT_NAME_VALUE>]
        [--eia <EXTRA_KEY> <EXTRA_INT_VALUE>[,<EXTRA_INT_VALUE...]]
        [--efa <EXTRA_KEY> <EXTRA_FLOAT_VALUE>[,<EXTRA_FLOAT_VALUE...]]
        [--ela <EXTRA_KEY> <EXTRA_LONG_VALUE>[,<EXTRA_LONG_VALUE...]]
        [-n <COMPONENT>] [-f <FLAGS>]
        [--grant-read-uri-permission] [--grant-write-uri-permission]
        [--debug-log-resolution] [--exclude-stopped-packages]
        [--include-stopped-packages]
        [--activity-brought-to-front] [--activity-clear-top]
        [--activity-clear-when-task-reset] [--activity-exclude-from-recents]
        [--activity-launched-from-history] [--activity-multiple-task]
        [--activity-no-animation] [--activity-no-history]
        [--activity-no-user-action] [--activity-previous-is-top]
        [--activity-reorder-to-front] [--activity-reset-task-if-needed]
        [--activity-single-top] [--activity-clear-task]
        [--activity-task-on-home]
        [--receiver-registered-only] [--receiver-replace-pending]
        [--selector]
        [<URI> | <PACKAGE> | <COMPONENT>]
    """
    def __init__(self, logFile: io.FileName):
        super(AndroidExecutor, self).__init__(logFile)

    def execute(self, application: str, *args, **kwargs):
        logger.debug("AndroidExecutor::execute() Starting ...")
        
        command = ["/system/bin/am", "start", f"-n {application}"]
        if "intent" in kwargs:
            command.append(f"-a {kwargs.get('intent')}")
        if "dataURI" in kwargs:
            command.append(f"-d {kwargs.get('dataURI')}")    
        if "dataType" in kwargs:
            command.append(f"-t {kwargs.get('dataType')}")
        if "category" in kwargs:
            category_args = kwargs.get("category")
            if isinstance(category_args, list):
                command = command + [f"-c {arg}" for arg in category_args]
            else:
                command.append(f"-c {category_args}")
        
        if len(args) > 0:
            command = command + [f"-e {arg}" for arg in args]
        
        #retcode = os.system(cmd)
        with open(self.logFile.getPathTranslated(), 'w') as f:
            retcode = subprocess.call(command, stdout=f, stderr=subprocess.STDOUT)
        logger.info(f"Process retcode = {retcode}")
        logger.debug("AndroidExecutor::execute() function ENDS")


class AndroidActivityExecutor(ExecutorABC):
    """
    Launch an Android native app. Preferred solution above AndroidExecutor.
    It will use StartAndroidActivity(package,[..]) with the given
    application name as the package.
    The provided kwargs are: intent, dataType, dataURI, action, category,
    className, flags and extras.
    example:
      StartAndroidActivity(com.android.chrome,android.intent.action.VIEW,,http://kodi.tv/)
      application: com.android.chrome
      intent: android.intent.action.VIEW
      dataURI: http://kodi.tv/
    
    Read more at https://kodi.wiki/view/List_of_built-in_functions#Android_built-in's
    """
    def __init__(self):
        super(AndroidActivityExecutor, self).__init__()

    def execute(self, application: str, *args, **kwargs):
        logger.debug("AndroidActivityExecutor::execute() Starting ...")

        intent = kwargs.get("intent", "")
        action = kwargs.get("action", "")
        category = kwargs.get("category", "")
        className = kwargs.get("className", "")
        dataType = kwargs.get("dataType", "")
        dataURI = kwargs.get("dataURI", "")
        flags = kwargs.get("flags", "")
        extras = kwargs.get("extras", [])

        non_blocking = kwargs.get(NON_BLOCKING_KEYWORD, True)

        if len(args) > 0:
            for arg in args:
                arg_splitted = arg.split(' ')
                extras.append({
                    "key": arg_splitted[0],
                    "value": " ".join(arg_splitted[1:]),
                    "type": "string"
                })
        
        extras_json = json.dumps(extras)
        command = f'StartAndroidActivity("{application}", "{intent}", "{dataType}", "{dataURI}", "{flags}", "{extras_json}", "{action}", "{category}", "{className}")'
        logger.debug(f"=============>>>> CMD: {command}")
        xbmc.executebuiltin(command, non_blocking)

        logger.debug("AndroidActivityExecutor::execute() function ENDS")


class OSXExecutor(ExecutorABC):

    def execute(self, application: str, *args, **kwargs):
        logger.debug('OSXExecutor::execute() Starting ...')
        command = [application] + list(args)

        separator = kwargs.get(SEPARATOR_KEYWORD, " ")
        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                command.append(f"{key}{separator}{value}" if value else key)

        # >> Old way.
        # os.system('"{0}" {1}'.format(application, arguments).encode('utf-8'))

        # >> New way.
        with open(self.logFile.getPathTranslated(), 'w') as f:
            retcode = subprocess.call(command, stdout=f, stderr=subprocess.STDOUT)
        logger.info('Process retcode = {0}'.format(retcode))
        logger.debug('OSXExecutor::execute() function ENDS')


class WindowsLnkFileExecutor(ExecutorABC):

    def execute(self, application: str, *args, **kwargs):
        logger.debug('WindowsLnkFileExecutor::execute() Starting ...')
        retcode = subprocess.call(f'start "AKL" /b "{application}"', shell=True)
        logger.info('LNK app retcode = {0}'.format(retcode))
        logger.debug('WindowsLnkFileExecutor::execute() function ENDS')


#
# CMD/BAT files in Windows
#
class WindowsBatchFileExecutor(ExecutorABC):
    def __init__(self, logFile: io.FileName, show_batch_window: bool):
        self.show_batch_window = show_batch_window
        super(WindowsBatchFileExecutor, self).__init__(logFile)

    def execute(self, application: str, *args, **kwargs):
        logger.debug('WindowsBatchFileExecutor::execute() Starting ...')
        command = [application] + list(args)
        
        separator = kwargs.get(SEPARATOR_KEYWORD, " ")
        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                command.append(f"{key}{separator}{value}" if value else key)

        apppath = io.FileName(application)
        apppath = apppath.getDir()
        
        # --- Workaround to run UNC paths in Windows ---
        # >> Retroarch now support ROMs in UNC paths (Samba remotes)
        new_command = list(command)
        for i, _ in enumerate(command):
            if command[i][0] == '\\':
                new_command[i] = '\\' + command[i]
                logger.debug('Executor (Windows BatchFile): Before arg #{0} = "{1}"'.format(i, command[i]))
                logger.debug('Executor (Windows BatchFile): Now    arg #{0} = "{1}"'.format(i, new_command[i]))
        command = list(new_command)
        logger.debug('Executor (Windows BatchFile): command = {0}'.format(command))
        
        logger.debug('Executor (Windows BatchFile) Launching BAT application')
        logger.debug('Executor (Windows BatchFile) Ignoring setting windows_cd_apppath')
        logger.debug('Executor (Windows BatchFile) Ignoring setting windows_close_fds')
        logger.debug('Executor (Windows BatchFile) show_batch_window = {0}'.format(self.show_batch_window))
        info = subprocess.STARTUPINFO()
        info.dwFlags = 1
        info.wShowWindow = 5 if self.show_batch_window else 0
        retcode = subprocess.call(command, cwd=apppath.encode('utf-8'), close_fds=True, startupinfo=info)
        logger.info('Executor (Windows BatchFile) Process BAR retcode = {0}'.format(retcode))
        logger.debug('WindowsBatchFileExecutor::execute() function ENDS')


#
# --- Windoze ---
# NOTE subprocess24_hack.py was hacked to always set CreateProcess() bInheritHandles to 0.
# bInheritHandles [in] If this parameter TRUE, each inheritable handle in the calling 
# process is inherited by the new process. If the parameter is FALSE, the handles are not 
# inherited. Note that inherited handles have the same value and access rights as the original handles.
# See https://msdn.microsoft.com/en-us/library/windows/desktop/ms682425(v=vs.85).aspx
#
# Same behaviour can be achieved in current version of subprocess with close_fds.
# If close_fds is true, all file descriptors except 0, 1 and 2 will be closed before the
# child process is executed. (Unix only). Or, on Windows, if close_fds is true then no handles
# will be inherited by the child process. Note that on Windows, you cannot set close_fds to
# true and also redirect the standard handles by setting stdin, stdout or stderr.
#
# If I keep old launcher behaviour in Windows (close_fds = True) then program output cannot
# be redirected to a file.
#
class WindowsExecutor(ExecutorABC):
    def __init__(self, logFile, cd_apppath: bool, close_fds: bool):
        self.windows_cd_apppath = cd_apppath
        self.windows_close_fds = close_fds
        super(WindowsExecutor, self).__init__(logFile)

    def execute(self, application: str, *args, **kwargs):
        logger.debug('WindowsExecutor::execute() Starting ...')
        command = [application] + list(args)

        # Normalize Windows filesystem paths before launching.
        # Only normalize arguments that point to an existing local file or directory.
        for i, value in enumerate(command):
            if isinstance(value, str):
                normalized = value.replace('/', '\\')
                if os.path.exists(normalized):
                    command[i] = normalized

        separator = kwargs.get(SEPARATOR_KEYWORD, " ")
        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                command.append(f"{key}{separator}{value}" if value else key)

        apppath = io.FileName(application)
        apppath = apppath.getDir()

        # --- Workaround to run UNC paths in Windows ---
        # >> Retroarch now support ROMs in UNC paths (Samba remotes)
        new_command = list(command)
        for i, _ in enumerate(command):
            if command[i][0] == '\\':
                new_command[i] = '\\' + command[i]
                logger.debug(f'WindowsExecutor: Before arg #{i} = "{command[i]}"')
                logger.debug(f'WindowsExecutor: Now    arg #{i} = "{new_command[i]}"')
            command = list(new_command)
        
        #command = ' '.join(command)
        logger.debug(f'WindowsExecutor: command = {command}')

        # >> cwd = apppath.encode('utf-8') fails if application path has Unicode on Windows
        # >> A workaraound is to use cwd = apppath.encode(sys.getfilesystemencoding()) --> DOES NOT WORK
        # >> For the moment AKL cannot launch executables on Windows having Unicode paths.
        logger.debug('Launching regular application')
        logger.debug(f'windows_cd_apppath = {self.windows_cd_apppath}')
        logger.debug(f'windows_close_fds  = {self.windows_close_fds}')
        logger.debug(f'apppath            = {apppath}')
        logger.debug(f'logfile path       = {self.logFile.getPathTranslated()}')

        # >> Note that on Windows, you cannot set close_fds to true and also redirect the
        # >> standard handles by setting stdin, stdout or stderr.
        if self.windows_cd_apppath:
            if self.windows_close_fds:
                retcode = subprocess.call(command, cwd=apppath.encode('utf-8'), close_fds=True)
            else:
                with open(self.logFile.getPathTranslated(), 'w') as f:
                    retcode = subprocess.call(command, cwd=apppath.encode('utf-8'), close_fds=False,
                                              stdout=f, stderr=subprocess.STDOUT)
        else:
            if self.windows_close_fds:
                retcode = subprocess.call(command, close_fds=True)
            else:
                with open(self.logFile.getPathTranslated(), 'w') as f:
                    retcode = subprocess.call(command, close_fds=False, stdout=f, stderr=subprocess.STDOUT)
                    
        logger.info(f'Process retcode = {retcode}')
        logger.debug('WindowsExecutor::execute() function ENDS')


class WebBrowserExecutor(ExecutorABC):

    def execute(self, application: str, *args, **kwargs):
        logger.debug('WebBrowserExecutor::execute() Starting ...')
        command = [application] + list(args)

        separator = kwargs.get(SEPARATOR_KEYWORD, " ")
        for key, value in kwargs.items():
            if key not in DEFAULT_KEYWORDS:
                command.append(f"{key}{separator}{value}" if value else key)

        url = " ".join([application] + list(args))
        logger.debug(f'Launching URL "{url}"')
        webbrowser.open(url)
        logger.debug('WebBrowserExecutor::execute() function ENDS')


class ExecutorSettings(object):
    show_batch_window = False
    lirc_state = False
    windows_cd_apppath = False
    windows_close_fds = False


class ExecutorFactoryABC(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def create(self, application_str: str, **kwargs) -> ExecutorABC: 
        """
        This creates a new Executor instance that is applicable for the
        OS and application to execute.
        Use the kwargs to set extra flags to help out in deciding which
        executor to choose.
        
        Optional kwargs:
            xbmc = True             : Directly choose the XbmcExecutor
            android_builtin = True  : Directly choose the Kodi built-in startactivity for Android (if os=android)
            browser = True          : Directly choose the webbrowser executor
        """
        pass


# -------------------------------------------------------------------------------------------------
# Abstract Factory Pattern
# See https://www.oreilly.com/library/view/head-first-design/0596007124/ch04.html
# -------------------------------------------------------------------------------------------------
class ExecutorFactory(ExecutorFactoryABC):
    def __init__(self, reportFilePath: io.FileName = None, settings: ExecutorSettings = ExecutorSettings()):
        self.settings = settings
        self.logFile = reportFilePath
        super(ExecutorFactory).__init__()

    def create(self, application_str: str, **kwargs) -> ExecutorABC:
        
        application = io.FileName(application_str)
        use_xbmc = kwargs.get("xbmc", False)
        use_android_builtin = kwargs.get("android_builtin", True)
        use_browser = kwargs.get("browser", False)

        if use_xbmc \
            or application.getBase().lower().replace('.exe', '') == 'xbmc' \
            or 'xbmc-fav-' in application.getPath() \
            or 'xbmc-sea-' in application.getPath():
            return XbmcExecutor(self.logFile)

        elif use_browser or re.search('.*://.*', application.getPath()):
            return WebBrowserExecutor(self.logFile)

        elif io.is_windows():
            # >> BAT/CMD file.
            if application.getExt().lower() == '.bat' or application.getExt().lower() == '.cmd':
                return WindowsBatchFileExecutor(self.logFile, self.settings.show_batch_window)
            # >> Standalone launcher where application is a LNK file
            elif application.getExt().lower() == '.lnk':
                return WindowsLnkFileExecutor(self.logFile)

            # >> Standard Windows executor
            return WindowsExecutor(self.logFile,
                                   self.settings.windows_cd_apppath,
                                   self.settings.windows_close_fds)

        elif io.is_android():
            if use_android_builtin:
                return AndroidActivityExecutor()
            return AndroidExecutor(self.logFile)

        elif io.is_linux():
            return LinuxExecutor(self.logFile, self.settings.lirc_state)

        elif io.is_osx():
            return OSXExecutor(self.logFile)

        else:
            logger.error('ExecutorFactory::create() Cannot determine the running platform')
            kodi.notify_warn('Cannot determine the running platform')

        return
