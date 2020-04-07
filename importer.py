# -*- coding: utf-8 -*-
# Module: plugin.video.waipu.tv
# Author: flubshi
# Created on: 2020
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from six.moves.urllib.parse import parse_qs, unquote, urlparse, urlencode
from lib.waipu_api import WaipuAPI
import xbmc
import xbmcaddon
import xbmcgui
import xbmcmediaimport

from xbmc import log


def filter_pictograms(data, filter=True):
    if filter:
        return ''.join(c for c in data if ord(c) < 0x25A0 or ord(c) > 0x1F5FF)
    return data


def mediaTypesFromOptions(options):
    if not 'mediatypes' in options and not 'mediatypes[]' in options:
        return None

    mediaTypes = None
    if 'mediatypes' in options:
        mediaTypes = options['mediatypes']
    elif 'mediatypes[]' in options:
        mediaTypes = options['mediatypes[]']

    return mediaTypes


def mediaProvider2str(mediaProvider):
    if not mediaProvider:
        return 'unknown media provider'

    return '"{}" ({})'.format(mediaProvider.getFriendlyName(), mediaProvider.getIdentifier())


def importItems(handle, mediaType, importSettings, mediaProviderSettings):
    items = []

    addon = xbmcaddon.Addon()
    username = addon.getSetting("username")
    password = addon.getSetting("password")
    provider = addon.getSettingInt("provider_select")

    if not username or not password:
        return items
    w = WaipuAPI(username, password, provider)

    channels = ['FILMTASTIC', 'WATCHMOVIESNOW', 'NETZKINO', 'BRONCO']  # , 'WATCHDOKUS'
    for channel_id in channels:
        streams = w.getEPGForChannel(channel_id)
        for stream in streams:
            # print("stream: "+str(stream))
            title = filter_pictograms(stream["title"])
            streamUrlProvider = stream["streamUrlProvider"]

            previewImage = ""
            if "previewImages" in stream:
                previewImage = stream["previewImages"][0] + "?width=200&height=200"

            stream_url = "plugin://plugin.video.waipu.tv/play-vod?" + urlencode(
                {"streamUrlProvider": streamUrlProvider, "title": title, "logo_url": previewImage})

            item = xbmcgui.ListItem(label=title, path=stream_url)

            info = {'mediatype': mediaType,
                    'title': title,
                    'sorttitle': title,
                    'path': stream_url,
                    'filenameandpath': stream_url
                    }

            if "description" in stream and stream['description']:
                info.update({'plot': stream['description']})

            if "genre" in stream and stream['genre']:
                info.update({'genre': stream['genre']})

            if "year" in stream and stream['year']:
                info.update({'year': stream['year']})

            if "country" in stream and stream['country']:
                info.update({'country': stream['country']})

            if "duration" in stream and stream['duration']:
                info.update({'duration': (int(stream['duration']) * 60)})

            # unassigned options: tag, album, artist, writer, director, lastplayed, placount, mpaa, rating, dateadded, plotoutline

            item.setInfo('video', info)

            item.setArt({'poster': previewImage})
            item.setIsFolder(False)
            items.append(item)

    return items


# default method
def discoverProvider(handle, options):
    mediatypes = set([xbmcmediaimport.MediaTypeMovie])  # xbmcmediaimport.MediaTypeTvShow

    providerId = "plugin.video.waipu.tv"
    providerIconUrl = "https://raw.githubusercontent.com/flubshi/plugin.video.waipu.tv/master/icon.png"
    provider = xbmcmediaimport.MediaProvider(providerId, "plugin://"+providerId, "Waipu.tv / O2 TV", providerIconUrl, mediatypes)
    provider.setIconUrl(providerIconUrl)

    xbmcmediaimport.setDiscoveredProvider(handle, True, provider)


# default method
def lookupProvider(handle, options):
    # retrieve the media provider
    mediaProvider = xbmcmediaimport.getProvider(handle)
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    xbmcmediaimport.setProviderFound(handle, True)


# default method
def canImport(handle, options):
    if not 'path' in options:
        log('cannot execute "canimport" without path')
        return

    xbmcmediaimport.setCanImport(handle, True)


# default method
def isProviderReady(handle, options):
    # retrieve the media provider
    mediaProvider = xbmcmediaimport.getProvider(handle)
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    # prepare the media provider settings
    if not mediaProvider.prepareSettings():
        log('cannot prepare media provider settings', xbmc.LOGERROR)
        return
    
    addon = xbmcaddon.Addon()
    username = addon.getSetting("username")
    password = addon.getSetting("password")
    provider = addon.getSettingInt("provider_select")

    if not username or not password:
        log('login credentials not filled', xbmc.LOGERROR)
        return

    w = WaipuAPI(username, password, provider)
    if w.fetchToken() != 200:
        log('login credentials invalid', xbmc.LOGERROR)
        return

    xbmcmediaimport.setProviderReady(handle, True)


# default method
def isImportReady(handle, options):
    # retrieve the media import
    mediaImport = xbmcmediaimport.getImport(handle)
    if not mediaImport:
        log('cannot retrieve media import', xbmc.LOGERROR)
        return
    # prepare and get the media import settings
    importSettings = mediaImport.prepareSettings()
    if not importSettings:
        log('cannot prepare media import settings', xbmc.LOGERROR)
        return

    # retrieve the media provider
    mediaProvider = xbmcmediaimport.getProvider(handle)
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    # prepare the media provider settings
    if not mediaProvider.prepareSettings():
        log('cannot prepare media provider settings', xbmc.LOGERROR)
        return

    xbmcmediaimport.setImportReady(handle, True)


# default method
def loadProviderSettings(handle, options):
    # retrieve the media provider
    mediaProvider = xbmcmediaimport.getProvider(handle)
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    settings = mediaProvider.getSettings()
    if not settings:
        log('cannot retrieve media provider settings', xbmc.LOGERROR)
        return

    settings.setLoaded()


# default method
def loadImportSettings(handle, options):
    # retrieve the media import
    mediaImport = xbmcmediaimport.getImport(handle)
    if not mediaImport:
        log('cannot retrieve media import', xbmc.LOGERROR)
        return

    settings = mediaImport.getSettings()
    if not settings:
        log('cannot retrieve media import settings', xbmc.LOGERROR)
        return

    settings.setLoaded()


# default method
def canUpdateMetadataOnProvider(handle, options):
    xbmcmediaimport.setCanUpdateMetadataOnProvider(True)


# default method
def canUpdatePlaycountOnProvider(handle, options):
    xbmcmediaimport.setCanUpdatePlaycountOnProvider(False)


# default method
def canUpdateLastPlayedOnProvider(handle, options):
    xbmcmediaimport.setCanUpdateLastPlayedOnProvider(False)


# default method
def canUpdateResumePositionOnProvider(handle, options):
    xbmcmediaimport.setCanUpdateResumePositionOnProvider(False)


# default method
def execImport(handle, options):
    if not 'path' in options:
        log('cannot execute "import" without path', xbmc.LOGERROR)
        return

    # parse all necessary options
    mediaTypes = mediaTypesFromOptions(options)
    if not mediaTypes:
        log('cannot execute "import" without media types', xbmc.LOGERROR)
        return

    # retrieve the media import
    mediaImport = xbmcmediaimport.getImport(handle)
    if not mediaImport:
        log('cannot retrieve media import', xbmc.LOGERROR)
        return

    # prepare and get the media import settings
    importSettings = mediaImport.prepareSettings()
    if not importSettings:
        log('cannot prepare media import settings', xbmc.LOGERROR)
        return

    # retrieve the media provider
    mediaProvider = mediaImport.getProvider()
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    log('importing {} items from {}...'.format(mediaTypes, mediaProvider2str(mediaProvider)))

    # prepare the media provider settings
    mediaProviderSettings = mediaProvider.prepareSettings()
    if not mediaProviderSettings:
        log('cannot prepare media provider settings', xbmc.LOGERROR)
        return

    # loop over all media types to be imported
    progress = 0
    progressTotal = len(mediaTypes)
    for mediaType in mediaTypes:
        if xbmcmediaimport.shouldCancel(handle, progress, progressTotal):
            return
        progress += 1

        if mediaType == xbmcmediaimport.MediaTypeVideoCollection and not importCollections:
            log('importing {} items from {} is disabled'.format(mediaType, mediaProvider2str(mediaProvider)),
                xbmc.LOGDEBUG)
            continue

        log('importing {} items from {}...'.format(mediaType, mediaProvider2str(mediaProvider)))

        xbmcmediaimport.setProgressStatus(handle, mediaType)

        log('importing {} items from from {}...'.format(mediaType, mediaProvider2str(mediaProvider)))
        items = importItems(handle, mediaType, importSettings, mediaProviderSettings)

        # pass the imported items back to Kodi
        if items:
            xbmcmediaimport.addImportItems(handle, items, mediaType)

    xbmcmediaimport.finishImport(handle, False)


# default method
def updateOnProvider(handle, options):
    # retrieve the media import
    mediaImport = xbmcmediaimport.getImport(handle)
    if not mediaImport:
        log('cannot retrieve media import', xbmc.LOGERROR)
        return

    # retrieve the media provider
    mediaProvider = mediaImport.getProvider()
    if not mediaProvider:
        log('cannot retrieve media provider', xbmc.LOGERROR)
        return

    # prepare and get the media import settings
    importSettings = mediaImport.prepareSettings()
    if not importSettings:
        log('cannot prepare media import settings', xbmc.LOGERROR)
        return

    item = xbmcmediaimport.getUpdatedItem(handle)
    if not item:
        log('cannot retrieve updated item', xbmc.LOGERROR)
        return

    log('updating "{}" ({}) on {}...'.format(item.getLabel(), item.getPath(), mediaProvider2str(mediaProvider)))

    itemVideoInfoTag = item.getVideoInfoTag()
    if not itemVideoInfoTag:
        log('updated item is not a video item', xbmc.LOGERROR)
        return

    # prepare the media provider settings
    if not mediaProvider.prepareSettings():
        log('cannot prepare media provider settings', xbmc.LOGERROR)
        return

    xbmcmediaimport.finishUpdateOnProvider(handle)


ACTIONS = {
    # official media import callbacks
    'discoverprovider': discoverProvider,
    'lookupprovider': lookupProvider,
    'canimport': canImport,
    'isproviderready': isProviderReady,
    'isimportready': isImportReady,
    'loadprovidersettings': loadProviderSettings,
    'loadimportsettings': loadImportSettings,
    'canupdatemetadataonprovider': canUpdateMetadataOnProvider,
    'canupdateplaycountonprovider': canUpdatePlaycountOnProvider,
    'canupdatelastplayedonprovider': canUpdateLastPlayedOnProvider,
    'canupdateresumepositiononprovider': canUpdateResumePositionOnProvider,
    'import': execImport,
    'updateonprovider': updateOnProvider
}


def run(argv):
    path = sys.argv[0]
    handle = int(sys.argv[1])

    options = None
    if len(sys.argv) > 2:
        # get the options but remove the leading ?
        params = sys.argv[2][1:]
        if params:
            options = parse_qs(params)

    log('path = {}, handle = {}, options = {}'.format(path, handle, params), xbmc.LOGDEBUG)

    url = urlparse(path)
    action = url.path
    if action[0] == '/':
        action = action[1:]

    if not action in ACTIONS:
        log('cannot process unknown action: {}'.format(action), xbmc.LOGERROR)
        sys.exit(0)

    actionMethod = ACTIONS[action]
    if not actionMethod:
        log('action not implemented: {}'.format(action), xbmc.LOGWARNING)
        sys.exit(0)

    log('executing action "{}"...'.format(action), xbmc.LOGDEBUG)
    actionMethod(handle, options)


run(sys.argv)
