# -*- coding: utf-8 -*-
#
import logging
import json
import pprint
import abc
import collections
import os
import sys
import shutil
from urllib.parse import urlencode, unquote

import xbmc
import xbmcgui
import xbmcaddon

from akl.utils import text, io

logger = logging.getLogger(__name__)


#
# Access Kodi JSON-RPC interface in an easy way.
# Returns a dictionary with the parsed response 'result' field.
#
# Query input:
#
# {
#     "id" : 1,
#     "jsonrpc" : "2.0",
#     "method" : "Application.GetProperties",
#     "params" : { "properties" : ["name", "version"] }
# }
#
# Query response:
#
# {
#     "id" : 1,
#     "jsonrpc" : "2.0",
#     "result" : {
#         "name" : "Kodi",
#         "version" : {"major":17,"minor":6,"revision":"20171114-a9a7a20","tag":"stable"}
#     }
# }
#
# Query response ERROR:
# {
#     "id" : null,
#     "jsonrpc" : "2.0",
#     "error" : { "code":-32700, "message" : "Parse error."}
# }
#
def jsonrpc_query(method=None, params=None, verbose=False):
    if not method:
        return {}
    query = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1}
    if params:
        query["params"] = params
                
    try:
        jrpc = xbmc.executeJSONRPC(json.dumps(query))
        response = json.loads(jrpc)
        if verbose:
            logger.debug('jsonrpc_query() response = \n{}'.format(pprint.pformat(response)))
    except Exception as exc:
        logger.exception(u'jsonrpc_query(): JSONRPC Error:\n{}'.format(exc), 1)
        response = {}    
    return response


def event(sender=None, command='test', data=None):

    if not sender:
        addon = xbmcaddon.Addon()
        sender = addon.getAddonInfo('id')
        
    data = data or {}
    event_params = {
        'sender': sender,
        'message': command,
        'data': data
    }
    
    logger.debug("event(): {}/{} => {}".format(sender, command, data))
    jsonrpc_query('JSONRPC.NotifyAll', event_params)
    #xbmc.executebuiltin('NotifyAll({}, {}, {})'.format(sender, method, data))


def execute(cmd):
    xbmc.executebuiltin(cmd)


def execute_uri(uri, args: dict = None):
    if args is not None:    
        uri = '{}?{}'.format(uri, urlencode(args))
    logger.debug('Executing RunPlugin(%s)...', uri)
    xbmc.executebuiltin('RunPlugin({})'.format(uri))


def update_uri(uri, args: dict = None, reset_history=False):
    if args is not None:    
        uri = f'{uri}?{urlencode(args)}'
    logger.debug('Executing Container.Update(%s)...', uri)
    cmd = f'Container.Update({uri}, replace)' if reset_history else f'Container.Update({uri})'
    execute(cmd)


def run_script(script: str, args: dict = None, wait_for_execution: bool = False):
    script_cmd = None
    if args is None:
        script_cmd = 'RunScript({})'.format(script)
    else:
        args_list = []
        for key, value in args.items():
            if value:
                args_list.append(key)
                args_list.append(str(value))
        script_cmd = 'RunScript({},{})'.format(script, ','.join(args_list))
        
    logger.debug('Executing {}...'.format(script_cmd))
    xbmc.executebuiltin(script_cmd, wait_for_execution)


def play_item(item_label: str, path: str, type: str, info: dict):
    
    listitem = xbmcgui.ListItem(label=item_label, label2=item_label)
    listitem.setInfo(type, info)
    
    logger.debug('Calling xbmc.Player().play() ...')
    xbmc.Player().play(path, listitem)


#
# Displays a small box in the low right corner
#
def notify(text, title='Advanced Kodi Launcher', time=5000):
    # --- Old way ---
    # xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (title, text, time, ICON_IMG_FILE_PATH))

    # --- New way ---
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_INFO, time)


def notify_warn(text, title='Advanced Kodi Launcher warning', time=7000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_WARNING, time)


#
# Do not use this function much because it is the same icon as when Python fails, and that may confuse the user.
#
def notify_error(text, title='Advanced Kodi Launcher error', time=7000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_ERROR, time)


# Displays a text window and requests a monospaced font.
# v18 Leia change: New optional param added usemono.
def display_text_window_mono(window_title, info_text):
    xbmcgui.Dialog().textviewer(window_title, info_text, True)


# -------------------------------------------------------------------------------------------------
# Kodi notifications and dialogs
# -------------------------------------------------------------------------------------------------
#
# Displays a modal dialog with an OK button. Dialog can have up to 3 rows of text, however first
# row is multiline.
# Call examples:
#  1) ret = kodi_dialog_OK('Launch ROM?')
#  2) ret = kodi_dialog_OK('Launch ROM?', title = 'AKL - Launcher')
#
def dialog_OK(text, title='Advanced Kodi Launcher'):
    xbmcgui.Dialog().ok(title, text)
 
   
# Returns True is YES was pressed, returns False if NO was pressed or dialog canceled.
def dialog_yesno(text, title='Advanced Kodi Launcher'):
    return xbmcgui.Dialog().yesno(title, text)


# Returns True is YES was pressed, returns False if NO was pressed or dialog canceled.
def dialog_yesno_custom(text, yeslabel_str, nolabel_str, title='Advanced Kodi Launcher'):
    return xbmcgui.Dialog().yesno(title, text, yeslabel=yeslabel_str, nolabel=nolabel_str)


def dialog_yesno_timer(text, timer_ms=30000, title='Advanced Kodi Launcher'):
    return xbmcgui.Dialog().yesno(title, text, autoclose=timer_ms)


def browse(type=1, text='Choose files', shares='files', mask='', preselected_path=None, useThumbs=False, multiple=False):
    return xbmcgui.Dialog().browse(type, text, shares, mask, useThumbs, False, preselected_path, enableMultiple=multiple)


def dialog_numeric(title: str, default: int = None):
    if default is not None:
        return xbmcgui.Dialog().numeric(0, heading=title, defaultt=str(default))
    return xbmcgui.Dialog().numeric(0, heading=title)


def dialog_ipaddr(title: str, default: int = None):
    if default is not None:
        return xbmcgui.Dialog().input(title, defaultt=default, type=xbmcgui.INPUT_IPADDRESS)
    return xbmcgui.Dialog().numeric(heading=title, type=xbmcgui.INPUT_IPADDRESS)


# Show keyboard dialog for user input. Returns None if not confirmed.
def dialog_keyboard(title, text='') -> str:
    keyboard = xbmc.Keyboard(text, title)
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return None
    return keyboard.getText()

# Returns a directory. See https://codedocs.xyz/AlwinEsch/kodi
#
# This supports directories, files, images and writable directories.
# xbmcgui.Dialog().browse(type, heading, shares[, mask, useThumbs, treatAsFolder, defaultt, enableMultiple])
#
# This supports files and images only.
# xbmcgui.Dialog().browseMultiple(type, heading, shares[, mask, useThumbs, treatAsFolder, defaultt])
# 
# This supports directories, files, images and writable directories.
# xbmcgui.Dialog().browseSingle(type, heading, shares[, mask, useThumbs, treatAsFolder, defaultt])
#
# shares   string or unicode - from sources.xml
# "files"  list file sources (added through filemanager)
# "local"  list local drives
# ""       list local drives and network shares


# Returns a directory.
def dialog_get_directory(d_heading, d_dir='', shares=''):
    if d_dir:
        ret = xbmcgui.Dialog().browse(0, d_heading, shares, defaultt=d_dir)
    else:
        ret = xbmcgui.Dialog().browse(0, d_heading, shares)
    return ret


def dialog_get_file(heading, d_dir='', shares=''):
    if d_dir:
        ret = xbmcgui.Dialog().browse(1, heading, shares, defaultt=d_dir)
    else:
        ret = xbmcgui.Dialog().browse(1, heading, shares)
    return ret


def get_listitem(label: str, label2: str, path: str = "", art: dict = {}):
    li = xbmcgui.ListItem(label=label, label2=label2, path=path)
    li.setArt(art)
    return li


def refresh_container():
    logger.debug('refresh_container()')
    xbmc.executebuiltin('Container.Refresh')


def get_current_window_id():
    return xbmcgui.getCurrentWindowId()


def set_windowprop(key, value, window_id=10000):
    window = xbmcgui.Window(window_id)
    window.setProperty(key, value)


def dict_to_windowprops(data=None, prefix="", window_id=10000):
    window = xbmcgui.Window(window_id)
    if not data:
        return None
    for (key, value) in data.items():
        window.setProperty('%s%s' % (prefix, key), str(value))


def clear_windowprops(keys=None, prefix="", window_id=10000):
    window = xbmcgui.Window(window_id)
    if not keys:
        return None
    for key in keys:
        window.clearProperty('%s%s' % (prefix, key))


def get_info_label(name):
    return xbmc.getInfoLabel(name)


def translate(id):
    return xbmcaddon.Addon().getLocalizedString(int(id))


def getAddonDir() -> io.FileName:
    addon_id = xbmcaddon.Addon().getAddonInfo('id')
    addon_data_dir = io.FileName('special://profile/addon_data/{}'.format(addon_id))
    return addon_data_dir


def get_addon_id() -> str:
    addon_id = xbmcaddon.Addon().getAddonInfo('id')
    return addon_id


def get_addon_version() -> str:
    return xbmcaddon.Addon().getAddonInfo('version')


def get_addon_path() -> str:
    return xbmcaddon.Addon().getAddonInfo('path')


def toggle_fullscreen():
    jsonrpc_query('Input.ExecuteAction', {'action': 'togglefullscreen'})


def get_screensaver_mode():
    r_dic = jsonrpc_query('Settings.getSettingValue', {'setting': 'screensaver.mode'})
    screensaver_mode = r_dic['result']['value'] if 'result' in r_dic else None
    return screensaver_mode


g_screensaver_mode = None  # Global variable to store screensaver status.


def disable_screensaver():
    global g_screensaver_mode
    g_screensaver_mode = get_screensaver_mode()
    logger.debug('kodi.disable_screensaver() g_screensaver_mode "{}"'.format(g_screensaver_mode))
    p_dic = {
        'setting': 'screensaver.mode',
        'value': '',
    }
    jsonrpc_query('Settings.setSettingValue', p_dic)
    logger.debug('kodi_disable_screensaver() Screensaver disabled.')


# kodi_disable_screensaver() must be called before this function or bad things will happen.
def restore_screensaver():
    if g_screensaver_mode is None:
        logger.error('kodi_disable_screensaver() must be called before kodi_restore_screensaver()')
        raise RuntimeError
    logger.debug('kodi_restore_screensaver() Screensaver mode "{}"'.format(g_screensaver_mode))
    p_dic = {
        'setting': 'screensaver.mode',
        'value': g_screensaver_mode,
    }
    jsonrpc_query('Settings.setSettingValue', p_dic)
    logger.debug('kodi_restore_screensaver() Restored previous screensaver status.')


#
# See https://kodi.wiki/view/JSON-RPC_API/v8#Textures
# See https://forum.kodi.tv/showthread.php?tid=337014
# See https://forum.kodi.tv/showthread.php?tid=236320
#
def delete_cache_texture(database_path_str):
    parameters = {
        "properties": ["url", "cachedurl", "lasthashcheck", "imagehash", "sizes"]
    }

    r_dic = jsonrpc_query(
        'Textures.GetTextures',
        parameters,
        verbose=False
    )

    textures = r_dic.get('result', {}).get('textures', [])

    target_path = database_path_str.replace('\\', '/').lower()
    matching_textures = []

    for texture in textures:
        texture_url = texture.get('url', '')

        if not texture_url.startswith('image://'):
            continue

        decoded_url = unquote(texture_url[8:])

        if decoded_url.endswith('/transform?size=thumb'):
            decoded_url = decoded_url[:-21]
        elif decoded_url.endswith('/'):
            decoded_url = decoded_url[:-1]

        decoded_path = decoded_url.replace('\\', '/').lower()

        if decoded_path == target_path:
            matching_textures.append(texture)

    logger.debug(
        'kodi_delete_cache_texture() Found {0} matching textures'.format(
            len(matching_textures)
        )
    )

    for texture in matching_textures:
        textureid = texture['textureid']

        logger.debug(
            'kodi_delete_cache_texture() Deleting texture with id {0}: {1}'.format(
                textureid,
                texture.get('url', '')
            )
        )

        jsonrpc_query(
            'Textures.RemoveTexture',
            {'textureid': textureid},
            verbose=False
        )

#
# Kodi dialog with select box based on a list.
# preselect is int
# Returns the int index selected or None if dialog was canceled.
#
class ListDialog(object):
    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    def select(self, title, options_list, preselect_idx=0, use_details=False):
        # --- Execute select dialog menu logic ---
        selection = self.dialog.select(title, options_list, useDetails=use_details, preselect=preselect_idx)
        if selection < 0:
            return None
        return selection


#
# Kodi dialog with select box based on a dictionary
#
class OrdDictionaryDialog(object):
    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    def select(self, title: str, options_odict: collections.OrderedDict, preselect=None, use_details: bool = False):
        preselected_index = -1
        if preselect is not None:
            preselected_value = options_odict[preselect]
            preselected_index = list(options_odict.values()).index(preselected_value)
            
        # --- Execute select dialog menu logic ---
        selection = self.dialog.select(title, [v for v in options_odict.values()], useDetails=use_details, preselect=preselected_index)       
        if selection < 0:
            return None
        key = list(options_odict.keys())[selection]

        return key


#
# Kodi dialog with multiselect
#
class MultiSelectDialog(object):
    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    def select(self, title: str, options_odict: collections.OrderedDict, preselected=[], use_details: bool = False):
        preselected_indices = None
        if preselected is not None and len(preselected) > 0:
            preselected_indices = []
            for preselect in preselected:
                preselected_value = options_odict[preselect]
                preselected_indices.append(list(options_odict.values()).index(preselected_value))
            
        # --- Execute select dialog menu logic ---
        selection = self.dialog.multiselect(title, [v for v in options_odict.values()],
                                            useDetails=use_details,
                                            preselect=preselected_indices)
        if selection is None:
            return None
        if len(selection) == 0:
            return []
        
        selected_keys = []
        for selected in selection:
            selected_keys.append(list(options_odict.keys())[selected])

        return selected_keys


# Progress dialog that can be closed and reopened.
# If the dialog is canceled this class remembers it forever.
class ProgressDialog(object):
    def __init__(self):
        self.title = 'Advanced Kodi Launcher'
        self.progress = 0
        self.progress_step = 0
        self.flag_dialog_canceled = False
        self.dialog_active = False
        self.progressDialog = xbmcgui.DialogProgress()

    def startProgress(self, message, num_steps=100):
        self.num_steps = num_steps
        self.progress = 0
        self.progress_step = 0
        self.dialog_active = True
        self.message = message
        self.progressDialog.create(self.title, self.message)
        self.progressDialog.update(self.progress)

    def setSteps(self, num_steps):
        self.num_steps = num_steps
        self.progress = 0
        self.progress_step = 0

    def incrementStep(self, message=None):
        self.updateProgress(self.progress_step + 1, message)
        
    # Update progress and optionally update messages as well.
    # If not messages specified then keep current message/s
    def updateProgress(self, step_index, message=None):
        self.progress_step = step_index
        self.progress = int((self.progress_step * 100) / self.num_steps)
        # Update both messages
        if message:
            self.message = message
            self.progressDialog.update(self.progress, message)
            return
        else:
            # The ' ' is to avoid a bug in Kodi progress dialog that keeps old message
            # if an empty string is passed.
            self.progressDialog.update(self.progress, self.message)

    # Update dialog message but keep same progress.
    def updateMessage(self, message):
        self.message = message
        self.progressDialog.update(self.progress, self.message)

    def isCanceled(self):
        # If the user pressed the cancel button before then return it now.
        if self.flag_dialog_canceled:
            return True
        else:
            self.flag_dialog_canceled = self.progressDialog.iscanceled()
            return self.flag_dialog_canceled

    def cancel(self):
        self.flag_dialog_canceled = True

    def close(self):
        # Before closing the dialog check if the user pressed the Cancel button and remember
        # the user decision.
        if self.progressDialog.iscanceled():
            self.flag_dialog_canceled = True
        self.progressDialog.close()
        self.dialog_active = False

    def endProgress(self):
        # Before closing the dialog check if the user pressed the Cancel button and remember
        # the user decision.
        if self.progressDialog.iscanceled():
            self.flag_dialog_canceled = True
        self.progressDialog.update(100)
        self.progressDialog.close()
        self.dialog_active = False

    # Reopens a previously closed dialog, remembering the messages and the progress it had
    # when it was closed.
    def reopen(self):
        self.progressDialog.create(self.title, self.message)
        self.progressDialog.update(self.progress)
        self.dialog_active = True


# -------------------------------------------------------------------------------------------------
# Kodi Wizards (by Chrisism)
# -------------------------------------------------------------------------------------------------
#
# The wizarddialog implementations can be used to chain a collection of
# different kodi dialogs and use them to fill a dictionary with user input.
#
# Each wizarddialog accepts a key which will correspond with the key/value combination
# in the dictionary. It will also accept a customFunction (delegate or lambda) which
# will be called after the dialog has been shown. Depending on the type of dialog some
# other arguments might be needed.
#
# The chaining is implemented by applying the decorator pattern and injecting
# the previous wizarddialog in each new one.
# You can then call the method 'runWizard()' on the last created instance.
#
# Each wizard has a customFunction which will can be called after executing this 
# specific dialog. It also has a conditionalFunction which can be called before
# executing this dialog which will indicate if this dialog may be shown (True return value).
#
class WizardDialogABC(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def executeDialog(self, properties: dict):
        pass


class WizardDialog(WizardDialogABC):
    __metaclass__ = abc.ABCMeta

    def __init__(self, decoratorDialog: WizardDialogABC, property_key: str, title: str, customFunction=None, conditionalFunction=None):
        self.decoratorDialog = decoratorDialog
        self.property_key = property_key
        self.title = title
        self.customFunction = customFunction
        self.conditionalFunction = conditionalFunction
        self.cancelled = False
        super(WizardDialog, self).__init__()

    def runWizard(self, properties: dict) -> dict:
        if not self.executeDialog(properties):
            logger.warning('User stopped wizard')
            return None

        return properties

    def executeDialog(self, properties):
        if self.decoratorDialog is not None:
            if not self.decoratorDialog.executeDialog(properties):
                return False

        if self.conditionalFunction is not None:
            mayShow = self.conditionalFunction(self.property_key, properties)
            if not mayShow:
                logger.debug('Skipping dialog for key: {0}'.format(self.property_key))
                return True

        output = self.show(properties)
        if self.cancelled:
            return False

        if self.customFunction is not None:
            output = self.customFunction(output, self.property_key, properties)

        if self.property_key:
            logger.debug('WizardDialog::executeDialog() props[{0}] =  {1}'.format(self.property_key, output))
            properties[self.property_key] = output

        return True

    @abc.abstractmethod
    def show(self, properties):
        return True

    def _cancel(self):
        self.cancelled = True


#
# Wizard dialog which accepts a keyboard user input.
#
class WizardDialog_Keyboard(WizardDialog):
    def show(self, properties):
        logger.debug('Executing keyboard wizard dialog for key: {0}'.format(self.property_key))
        originalText = properties[self.property_key] if self.property_key in properties else ''
        textInput = xbmc.Keyboard(originalText, self.title)
        textInput.doModal()
        if not textInput.isConfirmed():
            self._cancel()
            return None
        output = textInput.getText()

        return output


#
# Wizard dialog which shows a list of options to select from.
#
class WizardDialog_Selection(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, options,
                 customFunction=None, conditionalFunction=None):
        self.options = options
        super(WizardDialog_Selection, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('Executing selection wizard dialog for key: {0}'.format(self.property_key))
        selection = xbmcgui.Dialog().select(self.title, self.options)
        if selection < 0:
            self._cancel()
            return None
        output = self.options[selection]

        return output


#
# Wizard dialog which shows a list of options to select from.
# In comparison with the normal SelectionWizardDialog, this version allows a dictionary or key/value
# list as the selectable options. The selected key will be used.
# 
class WizardDialog_DictionarySelection(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, options,
                 customFunction=None, conditionalFunction=None):
        self.options = options
        super(WizardDialog_DictionarySelection, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('Executing dict selection wizard dialog for key: {0}'.format(self.property_key))
        dialog = OrdDictionaryDialog()
        if callable(self.options):
            self.options = self.options(self.property_key, properties)
        output = dialog.select(self.title, self.options)
        if output is None:
            self._cancel()
            return None

        return output


#
# Wizard dialog which shows a filebrowser.
#
class WizardDialog_FileBrowse(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, browseType, filter, shares='files',
                 customFunction=None, conditionalFunction=None):
        self.browseType = browseType
        self.filter = filter
        self.shares = shares
        super(WizardDialog_FileBrowse, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction
        )

    def show(self, properties):
        logger.debug('WizardDialog_FileBrowse::show() key = {0}'.format(self.property_key))
        originalPath = properties[self.property_key] if self.property_key in properties else ''

        if callable(self.filter):
            self.filter = self.filter(self.property_key, properties)
        output = xbmcgui.Dialog().browse(self.browseType, self.title, self.shares, self.filter, False, False, originalPath)

        if not output:
            self._cancel()
            return None
       
        return output


#
# Wizard dialog which shows an input for one of the following types:
#    - xbmcgui.INPUT_ALPHANUM (standard keyboard)
#    - xbmcgui.INPUT_NUMERIC (format: #)
#    - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
#    - xbmcgui.INPUT_TIME (format: HH:MM)
#    - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
#    - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
#
class WizardDialog_Input(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, inputType,
                 customFunction=None, conditionalFunction=None):
        self.inputType = inputType
        super(WizardDialog_Input, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('WizardDialog::show() {} key = {}'.format(self.inputType, self.property_key))
        originalValue = properties[self.property_key] if self.property_key in properties else ''
        output = xbmcgui.Dialog().input(self.title, originalValue, self.inputType)
        if not output:
            self._cancel()
            return None

        return output


# YesNo Dialog
class WizardDialog_YesNo(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, message, yes_label='Yes', no_label='No',
                 customFunction=None, conditionalFunction=None):
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label
        super(WizardDialog_YesNo, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('WizardDialog_YesNo::show() key = {}'.format(self.property_key))
        output = xbmcgui.Dialog().yesno(self.title, self.message, self.no_label, self.yes_label)
        return output


#
# Wizard dialog which shows you a message formatted with a value from the dictionary.
#
# Example:
#   dictionary item {'token':'roms'}
#   inputtext: 'I like {} a lot'
#   result message on screen: 'I like roms a lot'
#
# Formatting is optional
#
class WizardDialog_FormattedMessage(WizardDialog):
    def __init__(self, decoratorDialog, property_key, title, text,
                 customFunction=None, conditionalFunction=None):
        self.text = text
        super(WizardDialog_FormattedMessage, self).__init__(
            decoratorDialog, property_key, title, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('Executing message wizard dialog for key: {0}'.format(self.property_key))
        format_values = properties[self.property_key] if self.property_key in properties else ''
        full_text = self.text.format(format_values)
        output = xbmcgui.Dialog().ok(self.title, full_text)

        if not output:
            self._cancel()
            return None

        return output


#
# Wizard dialog which does nothing or shows anything.
# It only sets a certain property with the predefined value.
#
class WizardDialog_Dummy(WizardDialog):
    def __init__(self, decoratorDialog, property_key, predefinedValue,
                 customFunction=None, conditionalFunction=None):
        self.predefinedValue = predefinedValue
        super(WizardDialog_Dummy, self).__init__(
            decoratorDialog, property_key, None, customFunction, conditionalFunction)

    def show(self, properties):
        logger.debug('WizardDialog_Dummy::show() {0} key = {0}'.format(self.property_key))

        return self.predefinedValue


# -------------------------------------------------------------------------------------------------
# Kodi useful definition
# -------------------------------------------------------------------------------------------------
# https://codedocs.xyz/AlwinEsch/kodi/group__kodi__guilib__listitem__iconoverlay.html
KODI_ICON_OVERLAY_NONE = 0
KODI_ICON_OVERLAY_RAR = 1
KODI_ICON_OVERLAY_ZIP = 2
KODI_ICON_OVERLAY_LOCKED = 3
KODI_ICON_OVERLAY_UNWATCHED = 4
KODI_ICON_OVERLAY_WATCHED = 5
KODI_ICON_OVERLAY_HD = 6

# -------------------------------------------------------------------------------------------------
# Kodi GUI error reporting.
# * Errors can be reported up in the function backtrace with `if not st_dic['status']: return` after
#   every function call.
# * Warnings and non-fatal messages are printed in the callee function.
# * If st_dic['status'] is True but st_dic['dialog'] is not KODI_MESSAGE_NONE then display
#   the message but do not abort execution (success information message).
# * When display_status_message() is used to display the last message on a chaing of
#   function calls it is irrelevant its return value because addon always finishes.
#
# How to use:
# def high_level_function():
#     st_dic = new_status_dic()
#     function_that_does_something_that_may_fail(..., st_dic)
#     if display_status_message(st_dic): return # Display error message and abort addon execution.
#     if not st_dic['status']: return # Alternative code to return to caller function.
#
# def function_that_does_something_that_may_fail(..., st_dic):
#     code_that_fails
#     kodi_set_error_status(st_dic, 'Message') # Or change st_dic manually.
#     return
# -------------------------------------------------------------------------------------------------
KODI_MESSAGE_NONE = 100
# Kodi notifications must be short.
KODI_MESSAGE_NOTIFY = 200
KODI_MESSAGE_NOTIFY_WARN = 300
# Kodi OK dialog to display a message.
KODI_MESSAGE_DIALOG = 400
# Kodi notification to cancel current progress
KODI_MESSAGE_CANCEL = 500


# If status_dic['status'] is True then everything is OK. If status_dic['status'] is False,
# then display the notification.
def new_status_dic(message):
    return {
        'status': True,
        'dialog': KODI_MESSAGE_NOTIFY,
        'msg': message,
    }


# Display an status/error message in the GUI.
# Note that it is perfectly OK to display an error message and not abort execution.
# Returns True in case of error and addon must abort/exit immediately.
# Returns False if no error.
#
# Example of use: if kodi_display_user_message(st_dic): return
def display_status_message(st_dic):
    # Display (error) message and return status.
    if st_dic['dialog'] == KODI_MESSAGE_NONE:
        pass
    elif st_dic['dialog'] == KODI_MESSAGE_NOTIFY:
        notify(st_dic['msg'])
    elif st_dic['dialog'] == KODI_MESSAGE_NOTIFY_WARN:
        notify(st_dic['msg'])
    elif st_dic['dialog'] == KODI_MESSAGE_DIALOG:
        dialog_OK(st_dic['msg'])
    else:
        raise TypeError('st_dic["dialog"] = {}'.format(st_dic['dialog']))

    return st_dic['abort']


def kodi_is_error_status(st_dic):
    return st_dic['abort']


# Utility function to write more compact code.
# By default error messages are shown in modal OK dialogs.
def kodi_set_error_status(st_dic, msg, dialog=KODI_MESSAGE_DIALOG):
    st_dic['abort'] = True
    st_dic['msg'] = msg
    st_dic['dialog'] = dialog


def kodi_reset_status(st_dic):
    st_dic['abort'] = False
    st_dic['msg'] = ''
    st_dic['dialog'] = KODI_MESSAGE_NONE


# -------------------------------------------------------------------------------------------------
# Alternative Kodi GUI error reporting.
# This is a more phytonic way of reporting errors than using st_dic.
# -------------------------------------------------------------------------------------------------
# Create a Exception-derived class and use that for reporting.
#
# Example code:
# try:
#     function_that_may_fail()
# except KodiAddonError as ex:
#     display_status_message(ex)
# else:
#     notify('Operation completed')
#
# def function_that_may_fail():
#     raise KodiAddonError(msg, dialog)
class KodiAddonError(Exception):
    def __init__(self, msg, dialog=KODI_MESSAGE_DIALOG):
        self.dialog = dialog
        self.msg = msg

    def __str__(self):
        return self.msg


def kodi_display_exception(ex):
    st_dic = new_status_dic()
    st_dic['abort'] = True
    st_dic['dialog'] = ex.dialog
    st_dic['msg'] = ex.msg
    display_status_message(st_dic)
    
# -------------------------------------------------------------------------------------------------
# Kodi specific stuff
# -------------------------------------------------------------------------------------------------
# About Kodi image cache
#
# See http://kodi.wiki/view/Caches_explained
# See http://kodi.wiki/view/Artwork
# See http://kodi.wiki/view/HOW-TO:Reduce_disk_space_usage
# See http://forum.kodi.tv/showthread.php?tid=139568 (What are .tbn files for?)
#
# Whenever Kodi downloads images from the internet, or even loads local images saved along
# side your media, it caches these images inside of ~/.kodi/userdata/Thumbnails/. By default,
# large images are scaled down to the default values shown below, but they can be sized
# even smaller to save additional space.


# Gets where in Kodi image cache an image is located.
# image_path is a Unicode string.
# cache_file_path is a Unicode string.
def get_cached_image_FN(image_path):
    THUMBS_CACHE_PATH = os.path.join(xbmc.translatePath('special://profile/'), 'Thumbnails')
    # This function return the cache file base name
    base_name = xbmc.getCacheThumbName(image_path)
    cache_file_path = os.path.join(THUMBS_CACHE_PATH, base_name[0], base_name)
    return cache_file_path


# *** Experimental code not used for releases ***
# Updates Kodi image cache for the image provided in img_path.
# In other words, copies the image img_path into Kodi cache entry.
# Needles to say, only update the image cache if the image already was on the cache.
# img_path is a Unicode string
def update_image_cache(img_path):
    # What if image is not cached?
    cached_thumb = get_cached_image_FN(img_path)
    logger.debug('update_image_cache()       img_path {}'.format(img_path))
    logger.debug('update_image_cache()   cached_thumb {}'.format(cached_thumb))

    # For some reason Kodi xbmc.getCacheThumbName() returns a filename ending in TBN.
    # However, images in the cache have the original extension. Replace TBN extension
    # with that of the original image.
    cached_thumb_root, cached_thumb_ext = os.path.splitext(cached_thumb)
    if cached_thumb_ext == '.tbn':
        img_path_root, img_path_ext = os.path.splitext(img_path)
        cached_thumb = cached_thumb.replace('.tbn', img_path_ext)
        logger.debug('update_image_cache() U cached_thumb {}'.format(cached_thumb))

    # --- Check if file exists in the cache ---
    # xbmc.getCacheThumbName() seems to return a filename even if the local file does not exist!
    if not os.path.isfile(cached_thumb):
        logger.debug('update_image_cache() Cached image not found. Doing nothing')
        return

    # --- Copy local image into Kodi image cache ---
    # See https://docs.python.org/2/library/sys.html#sys.getfilesystemencoding
    logger.debug('update_image_cache() Image found in cache. Updating Kodi image cache')
    logger.debug('update_image_cache() copying {}'.format(img_path))
    logger.debug('update_image_cache() into    {}'.format(cached_thumb))
    fs_encoding = sys.getfilesystemencoding()
    logger.debug('update_image_cache() fs_encoding = "{}"'.format(fs_encoding))
    encoded_img_path = str(img_path, fs_encoding, 'ignore')
    encoded_cached_thumb = cached_thumb.encode(fs_encoding, 'ignore')
    try:
        shutil.copy2(encoded_img_path, encoded_cached_thumb)
    except OSError:
        notify_warn(title='AKL warning', text='Cannot update cached image (OSError)')
        logger.exception('Exception in update_image_cache()')
        logger.error('(OSError) Cannot update cached image')

    # Is this really needed?
    # xbmc.executebuiltin('ReloadSkin()')
