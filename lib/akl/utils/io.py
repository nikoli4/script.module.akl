# -*- coding: utf-8 -*-

# Advanced Kodi Launcher miscellaneous functions

# Copyright (c) 2016-2019 Wintermute0110 <wintermute0110@gmail.com>
# Portions (c) 2010-2015 Angelscry and others
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# --- Module documentation ---
# 1. This function contains utilities that do not depend on Kodi modules and utilities that
#    depend on Kodi modules. Appropiate replacements are provided when the Kodi modules are
#    not available, for example when running this file with the standard Python interpreter and
#    not Kodi Python interpreter.
#
# 2. Filesystem access utilities are located in this file. Filesystem can use the Python
#    standard library or Kodi Virtual FileSystem library if available.
#
# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
from __future__ import annotations

import abc
import logging
import errno
import fnmatch
import json
import sys
import os
import shutil
import typing
import zlib
import hashlib

# Python 3
from urllib.parse import urlparse

# --- Python standard library named imports ---
import xml.etree.ElementTree as ET

import xbmcvfs

from akl import constants

logger = logging.getLogger(__name__)
FILENAME_VERBOSE = False


# -------------------------------------------------------------------------------------------------
# --- New Filesystem class ---
#
# 1. Automatically uses Python standard library for local files and Kodi VFS for remote files.
#
# 2. All paths on all platforms use the slash '/' to separate directories.
#
# 3. Directories always end in a '/' character.
#
# 3. Decoding Unicode to the filesystem encoding is done in this class.
#
# 4. Tested with the following remote protocols:
#
#     a) special://
#
#     b) smb://
#
# --- Function reference ---
# FileName.getPath()         Full path                                     /home/Wintermute/Sonic.zip
# FileName.getPathNoExt()    Full path with no extension                   /home/Wintermute/Sonic
# FileName.getDir()          Directory name of file. Does not end in '/'   /home/Wintermute/
# FileName.getBase()         File name with no path                        Sonic.zip
# FileName.getBaseNoExt()    File name with no path and no extension       Sonic
# FileName.getExt()          File extension                                .zip
#
#
# A) Transform paths like smb://server/directory/ into \\server\directory\
# B) Use xbmcvfs.translatePath() for paths starting with special://
# C) Uses xbmcvfs wherever possible
#
# -------------------------------------------------------------------------------------------------
class FileType():
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, path_str: str):
        if path_str is None:
            path_str = ''
        self.path_str = path_str
        self.path_tr = path_str
        self.is_translated = False
    
    # ---------------------------------------------------------------------------------------------
    # Path manipulation and file information
    # ---------------------------------------------------------------------------------------------
    def getPath(self) -> str:
        return self.path_str

    def getPathTranslated(self):
        return self.path_tr

    def getPathNoExt(self):
        root, ext = os.path.splitext(self.path_str)
        return root

    def getDir(self) -> str:
        path_dir = os.path.dirname(self.path_str)
        return os.path.join(path_dir, '')

    def getBase(self) -> str:
        return os.path.basename(self.path_str)

    def getBaseNoExt(self) -> str:
        basename = os.path.basename(self.path_str)
        root, ext = os.path.splitext(basename)

        return root

    def getExt(self) -> str:
        root, ext = os.path.splitext(self.path_str)
        return ext
    
    def escapeQuotes(self):
        self.path_tr = self.path_tr.replace("'", "\\'")
        self.path_tr = self.path_tr.replace('"', '\\"')
        
    def isImageFile(self):
        ext = self.getExt().replace('.', '')
        return ext in constants.IMAGE_EXTENSION_LIST
    
    def isVideoFile(self):
        ext = self.getExt().replace('.', '')
        return ext in constants.TRAILER_EXTENSION_LIST
    
    def isManualFile(self):
        ext = self.getExt().replace('.', '')
        return ext in constants.MANUAL_EXTENSION_LIST
           
    #
    # Appends a string to path
    # Returns self FileName object
    #
    def append(self, arg):
        self.path_str = self.path_str + arg
        self.path_tr = self.path_tr + arg

        return self

    # ---------------------------------------------------------------------------------------------
    # Operator overloads
    # ---------------------------------------------------------------------------------------------
    def __str__(self):
        return self.path_str
    
    # Overloaded operator
    # See http://blog.teamtreehouse.com/operator-overloading-python
    # Argument other is a FileType object. other originalPath is expected to be a
    # subdirectory (path transformation not required)
    def __eq__(self, other):
        return self.path_str == other.path_str

    def __ne__(self, other):
        return not self.__eq__(other)
    
    
class FileName(FileType):
    # ---------------------------------------------------------------------------------------------
    # Constructor
    # path_str is an Unicode string.
    # ---------------------------------------------------------------------------------------------
    def __init__(self, path_str: str, isdir: bool = False):
        super(FileName, self).__init__(path_str)
        self.is_a_dir = isdir

        # --- Check if path needs translation ---
        # Note that internally path_tr is always used as the filename.
        if self.path_str.lower().startswith('special://'):
            self.is_translated = True
            self.path_tr = xbmcvfs.translatePath(self.path_str)
            # Check translated path does not contain '\'
            # NOTE We don't care if the translated paths has '\' characters or not. The translated
            #      path is internal to the class and never used outside the class. In the JSON
            #      databases and config files the original path path_str is used always.
            # if self.path_tr.find('\\'):
            #     logger.error('(FileName) path_str "{0}"'.format(self.path_str))
            #     logger.error('(FileName) path_tr  "{0}"'.format(self.path_tr))
            #     e_str = '(FileName) Translated path has \\ characters'
            #     logger.error(e_str)
            #     raise Addon_Error(e_str)

        # --- Ensure directory separator is the '/' character for all OSes ---
        self.path_str = self.path_str.replace('\\', '/')
        self.path_tr = self.path_tr.replace('\\', '/')

        # --- If a directory, ensure path ends with '/' ---
        if self.is_a_dir:
            if not self.path_str[-1:] == '/': self.path_str = self.path_str + '/'
            if not self.path_tr[-1:] == '/': self.path_tr = self.path_tr + '/'

        # --- Check if file is local or remote and needs translation ---
        if self.path_str.lower().startswith('smb://'):
            self.is_local = False
        else:
            self.is_local = True

        # --- Assume that translated paths are always local ---
        if self.is_translated and not self.is_local:
            e_str = '(FileName) File is translated and remote.'
            logger.error(e_str)
            raise constants.AddonError(e_str)

        # --- Use Pyhton for local paths and Kodi VFS for remote paths ---
        if self.is_local:
            # --- Filesystem functions ---
            self.exists         = self.exists_python
            self.makedirs       = self.makedirs_python
            self.list           = self.list_python
            self.recursive_list = self.recursive_list_python

            # --- File low-level IO functions ---
            self.open     = self.open_python
            self.read     = self.read_python
            self.write    = self.write_python
            self.close    = self.close_python
            self.unlink   = self.unlink_python
            self.stat     = self.stat_python
        else:
            self.exists         = self.exists_kodivfs
            self.makedirs       = self.makedirs_kodivfs
            self.list           = self.list_kodivfs
            self.recursive_list = self.recursive_list_kodivfs

            self.open     = self.open_kodivfs
            self.read     = self.read_kodivfs
            self.write    = self.write_kodivfs
            self.close    = self.close_kodivfs
            self.unlink   = self.unlink_kodivfs
            self.stat     = self.stat_kodivfs
    
    # ---------------------------------------------------------------------------------------------
    # Core functions
    # ---------------------------------------------------------------------------------------------
    #
    # Wheter the path stored in the FileName class is a directory or a regular file is handled
    # internally. This is to avoid a design flaw of the Kodi VFS library.
    #
    def isdir(self):
        return self.is_a_dir

    #
    # Allow late setting of isdir() if using the constructor call is not available, for example
    # when using FileName.pjoin().
    #
    def set_isdir(self, isdir):
        self.__init__(self.path_str, isdir)

    #
    # Joins paths and returns a new filename object.
    #
    def pjoin(self, path_str, isdir = False):
        return FileName(os.path.join(self.path_str, path_str), isdir)

    # Overloaded operator + behaves like self pjoin()
    def __add__(self, path_str):
        return self.pjoin(path_str)

    # ---------------------------------------------------------------------------------------------
    # Path manipulation and file information
    # ---------------------------------------------------------------------------------------------
    # Returns a new FileName object.
    def getDirAsFileName(self) -> FileName:
        return FileName(self.getDir())

    def changeExtension(self, targetExt):
        #raise AddonError('Implement me.')
        ext = self.getExt()
        copiedPath = self.path_str
        if not targetExt.startswith('.'):
            targetExt = '.{0}'.format(targetExt)
        new_path = FileName(copiedPath.replace(ext, targetExt))
        return new_path
    
    # ---------------------------------------------------------------------------------------------
    # Filesystem functions. Python Standard Library implementation
    # ---------------------------------------------------------------------------------------------
    def exists_python(self):
        return os.path.exists(self.path_tr)

    def makedirs_python(self):
        if not os.path.exists(self.path_tr): 
            if FILENAME_VERBOSE:
                logger.debug('FileName::makedirs_python() path_tr "{0}"'.format(self.path_tr))
            os.makedirs(self.path_tr)

    def list_python(self):        
        return os.listdir(self.path_tr)

    def recursive_list_python(self):
        files = []
        for root, dirs, foundfiles in os.walk(self.path_tr):
            for filename in foundfiles:
                files.append(os.path.join(root, filename))

        return files
    
    def stat_python(self):
        return os.stat(self.path_tr)

    # ---------------------------------------------------------------------------------------------
    # Filesystem functions. Kodi VFS implementation.
    # Kodi VFS functions always work with path_str, not with the translated path.
    # ---------------------------------------------------------------------------------------------
    def exists_kodivfs(self):
        return xbmcvfs.exists(self.path_str)

    def makedirs_kodivfs(self):
        xbmcvfs.mkdirs(self.path_tr)

    def list_kodivfs(self):
        subdirectories, filenames = xbmcvfs.listdir(self.path_tr)
        return filenames
    
    def recursive_list_kodivfs(self):
        files = self.recursive_list_kodivfs_folders(self.path_tr, None)
        return files
    
    def recursive_list_kodivfs_folders(self, fullPath, parentFolder):
        files = []
        subdirectories, filenames = xbmcvfs.listdir(fullPath)
        
        for filename in filenames:
            filePath = os.path.join(parentFolder, filename) if parentFolder is not None else filename
            files.append(filePath)

        for subdir in subdirectories:
            subPath = os.path.join(parentFolder, subdir) if parentFolder is not None else subdir
            subFullPath = os.path.join(fullPath, subdir)
            subPathFiles = self.recursive_list_kodivfs_folders(subFullPath, subPath)
            files.extend(subPathFiles)

        return files

    def stat_kodivfs(self):
        return xbmcvfs.Stat(self.path_tr)

    # ---------------------------------------------------------------------------------------------
    # File low-level IO functions. Python Standard Library implementation
    # ---------------------------------------------------------------------------------------------
    def open_python(self, flags, encoding='utf-8'):
        if FILENAME_VERBOSE:
            logger.debug('FileName::open_python() path_tr "{0}"'.format(self.path_tr))
            logger.debug('FileName::open_python() flags   "{0}"'.format(flags))

        # open() is a built-in function.
        # See https://docs.python.org/3/library/functions.html#open
        if flags and 'b' in flags:
            self.fileHandle = open(self.path_tr, flags)
        else: 
            self.fileHandle = open(self.path_tr, flags, encoding=encoding)
            
        return self.fileHandle

    def close_python(self):
        if self.fileHandle is None:
            raise OSError('file not opened')
        self.fileHandle.close()
        self.fileHandle = None

    def read_python(self):
       if self.fileHandle is None:
           raise OSError('file not opened')

       return self.fileHandle.read()

    def write_python(self, data:str): 
       if self.fileHandle is None:
           raise OSError('file not opened')
       self.fileHandle.write(data)

    def unlink_python(self):
        os.remove(self.path_tr)
            
    # ---------------------------------------------------------------------------------------------
    # File low-level IO functions. Kodi VFS implementation.
    # Kodi VFS documentation in https://alwinesch.github.io/group__python__xbmcvfs.html
    # ---------------------------------------------------------------------------------------------
    def open_kodivfs(self, flags, encoding='utf-8'):
        if FILENAME_VERBOSE:
            logger.debug('FileName::open_kodivfs() path_tr "{0}"'.format(self.path_tr))
            logger.debug('FileName::open_kodivfs() flags   "{0}"'.format(flags))

        self.fileHandle = xbmcvfs.File(self.path_tr, flags)
        return self.fileHandle
    
    def read_kodivfs(self):
        if self.fileHandle is None: raise OSError('file not opened')
        return self.fileHandle.read()
 
    def write_kodivfs(self, data):
        if self.fileHandle is None: raise OSError('file not opened')
        self.fileHandle.write(data)

    def close_kodivfs(self):
        if self.fileHandle is None: raise OSError('file not opened')
        self.fileHandle.close()
        self.fileHandle = None
  
    def unlink_kodivfs(self):
        if self.is_a_dir:
            xbmcvfs.rmdir(self.path_tr)
            return
        
        xbmcvfs.delete(self.path_tr)
        # hard delete if it doesnt succeed
        #logger.debug('xbmcvfs.delete() failed, applying hard delete')
        if self.exists():
            self.unlink_python()
            
    # ---------------------------------------------------------------------------------------------
    # File high-level IO functions
    # These functions are independent of the filesystem implementation.
    # For compatibility with Python 3, use the terms str for Unicode strings and bytes for
    # encoded strings.
    # ---------------------------------------------------------------------------------------------
    #
    # If both files are local use Python SL. Otherwise use Kodi VFS.
    # shutil.copy2() preserves metadata, including atime and mtime. We do not want that.
    #
    # See https://docs.python.org/2/library/shutil.html#shutil.copy
    # See https://docs.python.org/2/library/shutil.html#shutil.copy2
    # See https://docs.python.org/2/library/sys.html#sys.getfilesystemencoding
    #
    def copy(self, to_FN: FileName):
        if self.is_local and to_FN.is_local:
            fs_encoding = sys.getfilesystemencoding()
            source = self.getPathTranslated()
            dest = to_FN.getPathTranslated()
            if FILENAME_VERBOSE:
                logger.debug('FileName::copy() Using Python Standard Library')
                logger.debug(f'FileName::copy() fs encoding "{fs_encoding}"')
                logger.debug(f'FileName::copy() Copy "{source}"')
                logger.debug(f'FileName::copy() into "{dest}"')
            try:
                shutil.copy(source, dest)
            except OSError:
                logger.exception('FileName::copy() OSError exception copying image')
                raise constants.AddonError('OSError exception copying image')
            except IOError:
                logger.exception('FileName::copy() IOError exception copying image')
                raise constants.AddonError('IOError exception copying image')
        else:
            if FILENAME_VERBOSE:
                logger.debug('FileName::copy() Using Kodi VFS')
                logger.debug(f'FileName::copy() Copy "{self.getPath()}"')
                logger.debug(f'FileName::copy() into "{to_FN.getPath()}"')
            # >> If xbmcvfs.copy() fails what exceptions raise???
            xbmcvfs.copy(self.getPath(), to_FN.getPath())

    def readAll(self) -> str:
        return self.loadFileToStr()
    #
    # Loads a file into a Unicode string.
    # By default all files are assumed to be encoded in UTF-8.
    # Returns a Unicode string.
    #
    def loadFileToStr(self, encoding = 'utf-8'):
        if FILENAME_VERBOSE:
            logger.debug('FileName::loadFileToStr() Loading path_str "{0}"'.format(self.path_str))

        # NOTE Exceptions should be catched, reported and re-raised in the low-level
        # functions, not here!!!
        file_bytes = None
        try:
            self.open('r')
            file_bytes = self.read()
            self.close()
        except OSError:
            logger.exception('(OSError) Exception in FileName::loadFileToStr()')
            logger.error('(OSError) Cannot read {0} file'.format(self.path_tr))
            raise constants.AddonError('(OSError) Cannot read {0} file'.format(self.path_tr))
        except IOError as Ex:
            logger.exception('(IOError) Exception in FileName::loadFileToStr()')
            logger.error('(IOError) errno = {0}'.format(Ex.errno))
            if Ex.errno == errno.ENOENT: logger.error('(IOError) No such file or directory.')
            else:                        logger.error('(IOError) Unhandled errno value.')
            logger.error('(IOError) Cannot read {0} file'.format(self.path_tr))
            raise constants.AddonError('(IOError) Cannot read {0} file'.format(self.path_tr))
        
        # Return a Unicode string.
        if encoding is None or file_bytes is None:
            return file_bytes
        
        if type(file_bytes) == str:
            return file_bytes

        return file_bytes.decode(encoding)
    
    def writeAll(self, data: str):
        return self.saveStrToFile(data)
    
    #
    # data_str is a Unicode string. Encode it in UTF-8 for file writing.
    #
    def saveStrToFile(self, data_str: str, encoding = 'utf-8'):
        if FILENAME_VERBOSE:
            logger.debug('FileName::loadFileToStr() Loading path_str "{0}"'.format(self.path_str))
            logger.debug('FileName::loadFileToStr() Loading path_tr  "{0}"'.format(self.path_tr))

        # --- Catch exceptions in the FileName class ---
        try:
            self.open('w', encoding)
            self.write(data_str)
            self.close()
        except OSError:
            logger.exception('(OSError) Exception in saveStrToFile()')
            logger.error('(OSError) Cannot write {0} file'.format(self.path_tr))
            raise constants.AddonError('(OSError) Cannot write {0} file'.format(self.path_tr))
        except IOError as e:
            logger.exception('(IOError) Exception in saveStrToFile()')
            logger.error('(IOError) errno = {0}'.format(e.errno))
            if e.errno == errno.ENOENT: logger.error('(IOError) No such file or directory.')
            else:                       logger.error('(IOError) Unhandled errno value.')
            logger.error('(IOError) Cannot write {0} file'.format(self.path_tr))
            raise constants.AddonError('(IOError) Cannot write {0} file'.format(self.path_tr))

    # Opens a propery file and reads it
    # Reads a given properties file with each line of the format key=value.
    # Returns a dictionary containing the pairs.
    def readPropertyFile(self):
        import csv

        file_contents = self.loadFileToStr()
        file_lines = file_contents.splitlines()

        result = {}
        reader = csv.reader(file_lines, delimiter=str('='), quotechar=str('"'), quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
        for row in reader:
            if len(row) < 2:
                continue
            
            key = row[0].strip()
            value = row[1].strip().lstrip('"').rstrip('"')
            result[key] = value

        return result

    # Opens JSON file and reads it
    def readJson(self) -> typing.Any:
        contents = self.loadFileToStr()
        return json.loads(contents)
        
    # --- Configure JSON writer ---
    # >> json_unicode is either str or unicode
    # >> See https://docs.python.org/2.7/library/json.html#json.dumps
    # unicode(json_data) auto-decodes data to unicode if str
    # NOTE More compact JSON files (less blanks) load faster because size is smaller.
    def writeJson(self, raw_data, JSON_indent=1, JSON_separators=(',', ':')):
        json_data = json.dumps(raw_data, ensure_ascii=False, sort_keys=True,
                               indent=JSON_indent, separators=JSON_separators)
        self.saveStrToFile(json_data)

    def readXml(self) -> ET.Element:
        tree = None
        try:
            str_data = self.loadFileToStr()
            tree = ET.fromstring(str_data)
        except ET.ParseError as e:
            logger.exception('(ParseError) Exception parsing XML {}'.format(self.getPath()))
            logger.error('(ParseError) {0}'.format(str(e)))
    
        return tree

    # Opens file and writes xml. Give xml root element.
    def writeXml(self, xml_root: ET.Element):
        data = ET.tostring(xml_root)
        self.saveStrToFile(data)
        
    # ---------------------------------------------------------------------------------------------
    # Scanner functions
    # ---------------------------------------------------------------------------------------------
    def scanFilesInPath(self, mask = '*.*', progress_total_function=None, progress_function=None):
        files: typing.List[FileName] = []
        all_files = self.list()
        if progress_total_function is not None: progress_total_function(len(all_files))
        
        for filename in fnmatch.filter(all_files, mask):
            files.append(self.pjoin(filename))
            if progress_function is not None: progress_function()
            
        return files
    
    def recursiveScanFilesInPath(self, mask = '*.*', progress_total_function=None, progress_function=None):
        files: typing.List[FileName] = []
        all_files = self.recursive_list()
        if progress_total_function is not None:
            progress_total_function(len(all_files))
        
        for filename in fnmatch.filter(all_files, mask):
            files.append(self.pjoin(filename))
            if progress_function is not None:
                progress_function()
            
        return files


class Url(FileType):    
    def __init__(self, url: str):
        super(Url, self).__init__(url) 
    

# --- Determine interpreter running platform ---
# Cache all possible platform values in global variables for maximum speed.
# See http://stackoverflow.com/questions/446209/possible-values-from-sys-platform
cached_sys_platform = sys.platform


def _aux_is_android():
    if not cached_sys_platform.startswith('linux'):
        return False
    return 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ or 'XBMC_ANDROID_APK' in os.environ


def is_windows():
    return is_windows_bool


def is_osx():
    return is_osx_bool


def is_android():
    return is_android_bool


def is_linux():
    return is_linux_bool


def is_which_os() -> str:
    if is_windows_bool:
        return "Windows"
    if is_android_bool:
        return "Android"
    if is_osx_bool:
        return "OSX"
    if is_linux_bool:
        return "Linux"
    return "Unknown"


is_windows_bool = cached_sys_platform == 'win32' or cached_sys_platform == 'win64' or cached_sys_platform == 'cygwin'
is_osx_bool = cached_sys_platform.startswith('darwin')
is_android_bool = _aux_is_android()
is_linux_bool = cached_sys_platform.startswith('linux') and not is_android_bool


# -------------------------------------------------------------------------------------------------
# URLs
# -------------------------------------------------------------------------------------------------
#
# Get extension of URL. Returns '' if not found. Examples: 'png', 'jpg', 'gif'.
#
def get_URL_extension(url) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    if len(ext) == 0:
        return ext
    if ext[0] == '.':
        ext = ext[1:]  # Remove initial dot

    return ext


#
# Defaults to 'jpg' if URL extension cannot be determined
#
def get_image_URL_extension(url) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    if len(ext) == 0: return 'jpg'
    if ext[0] == '.': ext = ext[1:] # Remove initial dot
    ret = 'jpg' if ext == '' else ext

    return ret

# -------------------------------------------------------------------------------------------------
# File cache
# -------------------------------------------------------------------------------------------------
file_cache = {}
def misc_add_file_cache(dir_FN:FileName):
    global file_cache
    # >> Create a set with all the files in the directory
    if not dir_FN:
        logger.debug('misc_add_file_cache() Empty dir_str. Exiting')
        return

    logger.debug('misc_add_file_cache() Scanning path "{0}"'.format(dir_FN.getPath()))

    file_list = dir_FN.scanFilesInPath()
    # lower all filenames for easier matching
    file_set = [file.getBase().lower() for file in file_list]

    logger.debug('misc_add_file_cache() Adding {0} files to cache'.format(len(file_set)))
    file_cache[dir_FN.getPath()] = file_set


#
# See misc_look_for_file() documentation below.
#
def misc_search_file_cache(dir_path: FileName, filename_noext: str, file_exts):
    # logger.debug('misc_search_file_cache() Searching in  "{0}"'.format(dir_str))
    dir_str = dir_path.getPath()
    if dir_str not in file_cache:
        logger.warning('Directory {0} not in file_cache'.format(dir_str))
        return None

    current_cache_set = file_cache[dir_str]
    for ext in file_exts:
        file_base = filename_noext + '.' + ext
        file_base_as_cached = file_base.lower()
        # logger.debug('misc_search_file_cache() file_Base = "{0}"'.format(file_base))
        if file_base_as_cached in current_cache_set:
            # logger.debug('misc_search_file_cache() Found in cache')
            return dir_path.pjoin(file_base)

    return None


# -------------------------------------------------------------------------------------------------
# Misc stuff
# -------------------------------------------------------------------------------------------------
#
# Given the image path, image filename with no extension and a list of file extensions search for 
# a file.
#
# rootPath       -> FileName object
# filename_noext -> Unicode string
# file_exts      -> list of extenstions with no dot [ 'zip', 'rar' ]
#
# Returns a FileName object if a valid filename is found.
# Returns None if no file was found.
#
def misc_look_for_file(rootPath, filename_noext, file_exts):
    for ext in file_exts:
        file_path = rootPath.pjoin(filename_noext + '.' + ext)
        if file_path.exists():
            return file_path

    return None


#
# Get extensions to search for files
# Input : ['png', 'jpg']
# Output: ['png', 'jpg', 'PNG', 'JPG']
#
def get_filesearch_extension_list(exts):
    ext_list = list(exts)
    for ext in exts:
        ext_list.append(ext.upper())

    return ext_list


def parse_to_json_arg(obj) -> str:
    arg = '"{}"'.format(json.dumps(obj))
    arg = arg.replace('\\', '\\\\') #double encoding
    return arg


#
# Calculates CRC, MD5 and SHA1 of a file in an efficient way.
# Returns a dictionary with the checksums or None in case of error.
#
# https://stackoverflow.com/questions/519633/lazy-method-for-reading-big-file-in-python
# https://stackoverflow.com/questions/1742866/compute-crc-of-file-in-python 
#
def misc_calculate_checksums(full_file_path: FileName):
    if full_file_path is None:
        logger.debug('No checksum to complete')
        return None
    
    logger.debug('Computing checksums "{}"'.format(full_file_path.getPath()))
    file_opened = False
    try:
        f = full_file_path.open('rb')
        file_opened = True
        crc_prev = 0
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        for piece in misc_read_file_in_chunks(f):
            crc_prev = zlib.crc32(piece, crc_prev)
            md5.update(piece)
            sha1.update(piece)
        crc_digest = '{:08X}'.format(crc_prev & 0xFFFFFFFF)
        md5_digest = md5.hexdigest()
        sha1_digest = sha1.hexdigest()
        stat_size = full_file_path.stat().st_size
        size = stat_size() if callable(stat_size) else stat_size
        #os.path.getsize(full_file_path)
    except Exception as ex:
        logger.exception('Exception in plugin')
        logger.debug('(Exception) In misc_calculate_checksums()')
        logger.debug('Returning None')
        return None
    finally:
        if file_opened:
            try:
                full_file_path.close()
            except Exception:
                logger.exception('Exception closing checksum file')
    checksums = {
        'crc': crc_digest.upper(),
        'md5': md5_digest.upper(),
        'sha1': sha1_digest.upper(),
        'size': size,
    }

    return checksums


def misc_calculate_stream_checksums(file_bytes):
    logger.debug('Computing checksums of bytes stream...'.format(len(file_bytes)))
    crc_prev = 0
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    # Process bytes stream block by block
    # for piece in misc_read_bytes_in_chunks(file_bytes):
    #     crc_prev = zlib.crc32(piece, crc_prev)
    #     md5.update(piece)
    #     sha1.update(piece)
    # Process bytes in one go
    crc_prev = zlib.crc32(file_bytes, crc_prev)
    md5.update(file_bytes)
    sha1.update(file_bytes)
    crc_digest = '{:08X}'.format(crc_prev & 0xFFFFFFFF)
    md5_digest = md5.hexdigest()
    sha1_digest = sha1.hexdigest()
    size = len(file_bytes)

    checksums = {
        'crc'  : crc_digest.upper(),
        'md5'  : md5_digest.upper(),
        'sha1' : sha1_digest.upper(),
        'size' : size,
    }

    return checksums


#
# Lazy function (generator) to read a file piece by piece. Default chunk size: 256 KiB.
#
def misc_read_file_in_chunks(file_object, chunk_size=262144):
    while True:
        if hasattr(file_object, 'readBytes'):
            data = file_object.readBytes(chunk_size)
        else:
            data = file_object.read(chunk_size)
        if not data:
            break
        yield data

# Supported image files in:
# 1. misc_identify_image_id_by_contents()
# 2. misc_identify_image_id_by_ext()
IMAGE_PNG_ID     = 'PNG'
IMAGE_JPEG_ID    = 'JPEG'
IMAGE_GIF_ID     = 'GIF'
IMAGE_BMP_ID     = 'BMP'
IMAGE_TIFF_ID    = 'TIFF'
IMAGE_UKNOWN_ID  = 'Image unknown'
IMAGE_CORRUPT_ID = 'Image corrupt'

IMAGE_IDS = [
    IMAGE_PNG_ID,
    IMAGE_JPEG_ID,
    IMAGE_GIF_ID,
    IMAGE_BMP_ID,
    IMAGE_TIFF_ID,
]

IMAGE_EXTENSIONS = {
    IMAGE_PNG_ID  : ['png'],
    IMAGE_JPEG_ID : ['jpg', 'jpeg'],
    IMAGE_GIF_ID  : ['gif'],
    IMAGE_BMP_ID  : ['bmp'],
    IMAGE_TIFF_ID : ['tif', 'tiff'],
}

# Image file magic numbers. All at file offset 0.
# See https://en.wikipedia.org/wiki/List_of_file_signatures
IMAGE_MAGIC_DIC = {
    IMAGE_PNG_ID  : [ b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A' ],
    IMAGE_JPEG_ID : [
        b'\xFF\xD8\xFF\xDB',
        b'\xFF\xD8\xFF\xE0\x00\x10\x4A\x46\x49\x46\x00\x01',
        b'\xFF\xD8\xFF\xEE',
        b'\xFF\xD8\xFF\xE1',
    ],
    IMAGE_GIF_ID  : [
        b'\x47\x49\x46\x38\x37\x61',
        b'\x47\x49\x46\x38\x39\x61',
    ],
    IMAGE_BMP_ID  : [ b'\x42\x4D' ],
    IMAGE_TIFF_ID : [
        b'\x49\x49\x2A\x00',
        b'\x4D\x4D\x00\x2A',
    ]
}

# Inspects an image file and determine its type by using the magic numbers,
# Returns an image id defined in list IMAGE_IDS or IMAGE_UKNOWN_ID.
def misc_identify_image_id_by_contents(fpath: FileName):
    # If file size is 0 or less than 64 bytes it is corrupt.
    statinfo = os.stat(fpath.getPath())
    if statinfo.st_size < 64: return IMAGE_CORRUPT_ID

    # Read first 64 bytes of file.
    # Search for the magic number of the beginning of the file.
    with open(fpath.getPath(), "rb") as f:
        file_bytes = f.read(64)
    for img_id in IMAGE_MAGIC_DIC:
        for magic_bytes in IMAGE_MAGIC_DIC[img_id]:
            magic_bytes_len = len(magic_bytes)
            file_chunk = file_bytes[0:magic_bytes_len]
            if len(file_chunk) != magic_bytes_len: raise TypeError
            if file_chunk == magic_bytes: return img_id

    return IMAGE_UKNOWN_ID

# Returns an image id defined in list IMAGE_IDS or IMAGE_UKNOWN_ID.
def misc_identify_image_id_by_ext(path: FileName):
    ext = path.getExt()
    # log_debug('asset_ext {}'.format(asset_ext))
    if not ext: return IMAGE_UKNOWN_ID
    ext = ext[1:] # Remove leading dot '.png' -> 'png'
    for img_id in IMAGE_EXTENSIONS:
        for img_ext in IMAGE_EXTENSIONS[img_id]:
            if ext.lower() == img_ext: return img_id

    return IMAGE_UKNOWN_ID