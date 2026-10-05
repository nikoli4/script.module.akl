# -*- coding: utf-8 -*-
#
# Advanced Kodi Launcher network IO module
#

# Copyright (c) Wintermute0110 <wintermute0110@gmail.com> / Chrisism <crizizz@gmail.com>
# Portions (c) 2010-2015 Angelscry
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

import typing

import logging
import random
from enum import Enum

import requests
from urllib.error import HTTPError

# AKL modules
from akl.utils import io

logger = logging.getLogger(__name__)


# --- GLOBALS -----------------------------------------------------------------
# Firefox user agents
# USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/68.0'
USER_AGENT = 'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/68.0'


class ContentType(Enum):
    RAW = 0
    STRING = 1
    BYTES = 2
    JSON = 3


# Where did this user agent come from?
# USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31';

# ---  -----------------------------------------------------------------
def get_random_UserAgent():
    platform = random.choice(['Macintosh', 'Windows', 'X11'])
    if platform == 'Macintosh':
        os_str = random.choice(['68K', 'PPC'])
    elif platform == 'Windows':
        os_str = random.choice([
            'Win3.11', 'WinNT3.51', 'WinNT4.0', 'Windows NT 5.0', 'Windows NT 5.1', 
            'Windows NT 5.2', 'Windows NT 6.0', 'Windows NT 6.1', 'Windows NT 6.2', 
            'Win95', 'Win98', 'Win 9x 4.90', 'WindowsCE'])
    elif platform == 'X11':
        os_str = random.choice(['Linux i686', 'Linux x86_64'])
    browser = random.choice(['chrome', 'firefox', 'ie'])
    if browser == 'chrome':
        webkit = str(random.randint(500, 599))
        version = str(random.randint(0, 24)) + '.0' + str(random.randint(0, 1500)) + '.' + str(random.randint(0, 999))
        return 'Mozilla/5.0 (' + os_str + ') AppleWebKit/' + webkit + '.0 (KHTML, live Gecko) Chrome/' + version + ' Safari/' + webkit

    elif browser == 'firefox':
        year = str(random.randint(2000, 2012))
        month = random.randint(1, 12)
        if month < 10:
            month = '0' + str(month)
        else:
            month = str(month)
        day = random.randint(1, 30)
        if day < 10:
            day = '0' + str(day)
        else:
            day = str(day)
        gecko = year + month + day
        version = random.choice([
            '1.0', '2.0', '3.0', '4.0', '5.0', '6.0', '7.0', '8.0', 
            '9.0', '10.0', '11.0', '12.0', '13.0', '14.0', '15.0'])
        return 'Mozilla/5.0 (' + os_str + '; rv:' + version + ') Gecko/' + gecko + ' Firefox/' + version

    elif browser == 'ie':
        version = str(random.randint(1, 10)) + '.0'
        engine = str(random.randint(1, 5)) + '.0'
        option = random.choice([True, False])
        if option:
            token = random.choice(['.NET CLR', 'SV1', 'Tablet PC', 'Win64; IA64', 'Win64; x64', 'WOW64']) + '; '
        else:
            token = ''
        return 'Mozilla/5.0 (compatible; MSIE ' + version + '; ' + os_str + '; ' + token + 'Trident/' + engine + ')'


def download_img(img_url, file_path: io.FileName, url_log=None):
    # --- Download image to a buffer in memory ---
    # If an exception happens here no file is created (avoid creating files with 0 bytes).
    # url_log may contain a sanitized version of img_url for services whose
    # download URLs contain credentials or other sensitive query parameters.
    file_data, http_code = get_URL(
        img_url,
        url_log=url_log,
        verify_ssl=True,
        content_type=ContentType.BYTES
    )
    if http_code != 200:
        return
    
    # --- Write image file to disk ---
    # There should be no more 0 size files with this code.
    try:
        f = file_path.open('wb')
        f.write(file_data)
        f.close()
    except IOError:
        logger.exception('(IOError) In download_img(), disk code.')
    except Exception:
        logger.exception('(Exception) In download_img(), disk code.')

#
# User agent is fixed and defined in global var USER_AGENT
#
# @param url: [string] URL to open
# @param url_log: [string] If not None this URL will be used in the logs.
# @param headers: [Dict(string,string)] Optional collection of custom headers to add.
# @param verify_ssl: [bool|string] Set to False to ignore SSL verification, or path to certificates to use.
# @param cert: [tuple(str,str)] Client side certificates. Tuple with paths to cert and key file. None if not used.
# @param encoding: [string] If you want to override auto encoding, provide with preferred encoding.
# @param content_type: [ContentType Enum] Define what kind of type will be returned (bytes, string, json, any).
# @return: [tuple] Tuple of content and code. First tuple element is a string, bytes or json object with the 
#          web content or None if network error/exception. Second tuple element is the 
#          HTTP status code as integer or None if network error/exception.
def get_URL(url:str, url_log:str = None, headers:dict = None, 
            verify_ssl=None, cert=None, encoding=None, 
            content_type:ContentType=ContentType.STRING,
            session: requests.Session = None) -> typing.Union[typing.Tuple[str,int],typing.Tuple[any,int]]:
    try:
        if url_log is None:
            logger.debug(f'get_URL() GET URL "{url}"')
        else:
            logger.debug(f'get_URL() GET URL "{url_log}"')

        if headers is None:
            headers = {}
        headers["User-Agent"] = USER_AGENT

        if session is None:
            session = requests.Session()

        response: requests.Response = session.get(
            url,
            headers=headers, 
            timeout=120, 
            verify=verify_ssl,
            cert=cert)
        
        logger.debug(f'get_URL() encoding {response.encoding}')
        if encoding is not None:
            response.encoding = encoding
            logger.debug(f'get_URL() encoding override with {response.encoding}')

        http_code = response.status_code
        if content_type == ContentType.BYTES:
            page_data = response.content
        elif content_type == ContentType.RAW:
            page_data = response.raw
        elif content_type == ContentType.STRING:
            page_data = response.text
        elif content_type == ContentType.JSON:
            page_data = response.json()
       
        logger.debug('get_URL() content-length {:,} bytes'.format(int(response.headers.get("content-length", "0"))))
        logger.debug(f'get_URL() HTTP status code {http_code}')

        return page_data, http_code
    except HTTPError as ex:
        http_code = ex.code
        try:
            page_data = ex.read()
            ex.close()
        except:
            page_data = str(ex.reason)
        logger.exception('(HTTPError) In net_get_URL()')
        logger.error(f'(HTTPError) Code {http_code}')
        return page_data, http_code
    except Exception as ex:
        logger.exception('(Exception) In net_get_URL()')
        return None, 500

def get_URL_oneline(url, url_log = None):
    page_data, http_code = get_URL(url, url_log)
    if page_data is None: return (page_data, http_code)

    # --- Put all page text into one line ---
    page_data = page_data.replace('\r\n', '')
    page_data = page_data.replace('\n', '')

    return page_data, http_code

def get_URL_as_json(url, url_log = None, headers:dict = None, verify_ssl=None, encoding=None) -> any:
    page_data, http_code = get_URL(url, url_log, headers=headers, verify_ssl=verify_ssl, 
                                    encoding=encoding, content_type = ContentType.JSON)
    return page_data

# Do HTTP request with POST.
# If an exception happens return empty data (None).
#
# @param url: [string] URL to open
# @param data: [dict] Form data to post to server
# @param headers: [Dict(string,string)] Optional collection of custom headers to add.
# @param verify_ssl: [bool|string] Set to False to ignore SSL verification, or path to certificates to use.
# @param cert: [tuple(str,str)] Client side certificates. Tuple with paths to cert and key file. None if not used.
# @param encoding: [string] If you want to override auto encoding, provide with preferred encoding.
# @param content_type: [ContentType Enum] Define what kind of type will be returned (bytes, string, json, any).
# @return: [tuple] Tuple of strings. First tuple element is a string with the web content as 
#          a Unicode string or None if network error/exception. Second tuple element is the 
#          HTTP status code as integer or hardcoded 500 if network error/exception.
def post_URL(url:str, data:dict, headers:dict = None, verify_ssl=None, 
             cert=None, encoding=None, content_type:ContentType=ContentType.STRING,
             session: requests.Session = None) -> typing.Union[typing.Tuple[str, int],typing.Tuple[any, int]]:
    try:
        logger.debug(f"post_URL() POST URL '{url}'")
        if headers is None: headers = {}
        headers["User-Agent"] = USER_AGENT

        if session is None:
            session = requests.Session()

        response:requests.Response = session.post(
            url,
            data=data,
            headers=headers, 
            timeout=120, 
            verify=verify_ssl,
            cert=cert)
        
        logger.debug(f"post_URL() encoding {response.encoding}")
        if encoding is not None:
            response.encoding = encoding
            logger.debug(f"post_URL() encoding override with {response.encoding}")
                
        http_code = response.status_code
        if content_type == ContentType.BYTES:
            page_data = response.content
        elif content_type == ContentType.RAW:
            page_data = response.raw
        elif content_type == ContentType.STRING:
            page_data = response.text
        elif content_type == ContentType.JSON:
            page_data = response.json()

        logger.debug('post_URL() content-length {:,} bytes'.format(int(response.headers.get("content-length", "0"))))
        logger.debug(f"post_URL() HTTP status code {http_code}")

        return page_data, http_code
    except HTTPError as ex:
        http_code = ex.code
        try:
            page_bytes = ex.read()
            ex.close()
        except:
            page_bytes = str(ex.reason)
        logger.exception('(HTTPError) In post_URL()')
        logger.error(f'(HTTPError) Code {http_code}')
        return page_bytes, http_code
    except IOError:
        logger.exception('(IOError exception) In post_URL()')
        return None, 500
    except Exception:
        logger.exception('(General exception) In post_URL()')
        return None, 500


# POST JSON content to an url.
# If an exception happens return empty data (None).
#
# @param url: [string] URL to open
# @param json_obj: [any] Object to parse to JSON and post.
# @param headers: [Dict(string,string)] Optional collection of custom headers to add.
# @param verify_ssl: [bool|string] Set to False to ignore SSL verification, or path to certificates to use.
# @param cert: [tuple(str,str)] Client side certificates. Tuple with paths to cert and key file. None if not used.
# @param encoding: [string] If you want to override auto encoding, provide with preferred encoding.
# @param content_type: [ContentType Enum] Define what kind of type will be returned (bytes, string, json, any).
# @return: [tuple] Tuple of strings. First tuple element is a string with the web content as 
#          a Unicode string or None if network error/exception. Second tuple element is the 
#          HTTP status code as integer or hardcoded 500 if network error/exception.
def post_JSON_URL(url, json_obj: any, headers:dict = None, 
                verify_ssl=None, cert=None, encoding=None, 
                content_type:ContentType=ContentType.STRING) -> typing.Union[typing.Tuple[str, int],typing.Tuple[any, int]]:
    try:
        logger.debug(f"post_JSON_URL() POST URL '{url}'")
        if headers is None:
            headers = {}
        headers["User-Agent"] = USER_AGENT

        response: requests.Response = requests.post(
            url,
            json=json_obj,
            headers=headers, 
            timeout=120, 
            verify=verify_ssl,
            cert=cert)
        
        logger.debug(f"post_JSON_URL() encoding {response.encoding}")
        if encoding is not None:
            response.encoding = encoding
            logger.debug(f"post_JSON_URL() encoding override with {response.encoding}")
        
        http_code = response.status_code
        if content_type == ContentType.BYTES:
            page_data = response.content
        elif content_type == ContentType.RAW:
            page_data = response.raw
        elif content_type == ContentType.STRING:
            page_data = response.text
        elif content_type == ContentType.JSON:
            page_data = response.json()
       
        logger.debug('post_JSON_URL() content-length {:,} bytes'.format(int(response.headers.get("content-length", "0"))))
        logger.debug(f"post_JSON_URL() HTTP status code {http_code}")

        return page_data, http_code
    except HTTPError as ex:
        http_code = ex.code
        try:
            page_bytes = ex.read()
            ex.close()
        except Exception:
            page_bytes = str(ex.reason)
        logger.exception('(HTTPError) In post_JSON_URL()')
        logger.error(f'(HTTPError) Code {http_code}')
        return page_bytes, http_code
    except IOError:
        logger.exception('(IOError exception) In post_JSON_URL()')
        return None, 500
    except Exception:
        logger.exception('(General exception) In post_JSON_URL()')
        return None, 500


def start_http_session():
    return requests.Session()
