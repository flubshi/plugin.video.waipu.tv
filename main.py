# -*- coding: utf-8 -*-
# Module: default
# Author: MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib import urlencode
from urlparse import parse_qsl
from waipu import Waipu
import xbmcgui
import xbmcplugin
import xbmcaddon
import base64
import json
import inputstreamhelper

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
username = xbmcplugin.getSetting(_handle, "username")
password = xbmcplugin.getSetting(_handle, "password")

# open settings, 
if not username or not password:
    xbmcaddon.Addon().openSettings()
    # TODO not working as expected
    username = xbmcplugin.getSetting(_handle, "username")
    password = xbmcplugin.getSetting(_handle, "password")

w = Waipu(username, password)


def get_url(**kwargs):    
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def get_default():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')

    # TV channel list
    list_item = xbmcgui.ListItem(label="Live TV", iconImage="DefaultAddonPVRClient.png")
    url = get_url(action='list-channels')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

    # recordings list
    list_item = xbmcgui.ListItem(label="Aufnahmen", iconImage="DefaultFolder.png")
    url = get_url(action='list-recordings')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_recordings():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    try:
        recordings = w.getRecordings()
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return
    # Iterate through categories
    for recording in recordings:
        label_dat = ''
        metadata = {
            'genre': recording['epgData']['genre'],
            'plot': recording['epgData']['description'],
            'mediatype': 'video'}

        if "episodeId" in recording['epgData'] and recording['epgData']['episodeId']:
            # tv show
            if recording['epgData']['episodeTitle']:
                metadata.update({"tvshowtitle": recording['epgData']['episodeTitle']})
                label_dat = "[B]" + recording['epgData']['title'] + "[/B] - " + recording['epgData']['episodeTitle']
            else:
                label_dat = "[B]" + recording['epgData']['title'] + "[/B]"
            metadata.update({
                'title': label_dat,
                'season': recording['epgData']['season'],
                'episode': recording['epgData']['episode'],
                })
        else:
            # movie
            label_dat = "[B]" + recording['epgData']['title'] + "[/B]"
            metadata.update({
                'title': label_dat
                })

        list_item = xbmcgui.ListItem(label=label_dat)
        list_item.setInfo('video', metadata)

        for previewImage in recording['epgData']['previewImages']:
            previewImage += "?width=200&height=200"
            xbmc.log("waipu image: " + previewImage, level=xbmc.LOGDEBUG)
            list_item.setArt(
            {'thumb': previewImage, 'icon': previewImage, 'clearlogo': previewImage})
            break
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play-recording', recordingid=recording["id"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=False)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_channels():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    try:
        channels = w.getChannels()
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return
    # Iterate through categories
    for channel, channel_data in channels.iteritems():
        list_item = xbmcgui.ListItem(label=channel_data['displayName'])
        list_item.setInfo('video', {'title': channel_data['displayName'],
                                    #'genre': category,
                                    'tracknumber' : channel_data['orderIndex']+1,
                                    #'plot': "Langinfo",
                                    #'tagline': "Tagline",
                                    'mediatype': 'video'})
        list_item.setArt({'thumb': channel_data['icon'], 'icon': channel_data['icon'], 'clearlogo': channel_data['icon']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play-channel', channel=channel)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder = False)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def play_channel(channel):

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"
    print "Playing "+channel
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    for stream in w.playChannel(channel)["streams"]:
        if (stream["protocol"] == 'mpeg-dash'):
        #if (stream["protocol"] == 'hls'):
            for link in stream['links']:
                path=link["href"]
                if path:
                    path=path+"|User-Agent="+user_agent
                    print path
                    break

    listitem = xbmcgui.ListItem(channel, path=path)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    # Prepare for drm keys
    jwtheader,jwtpayload,jwtsignature = w.getToken().split(".")
    xbmc.log("waipu jwt payload: "+jwtpayload, level=xbmc.LOGDEBUG)
    jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
    jwt_json = json.loads(jwtpayload_decoded)
    xbmc.log("waipu userhandle: "+jwt_json["userHandle"], level=xbmc.LOGDEBUG)
    license = {'merchant' : 'exaring', 'sessionId' : 'default', 'userId' : jwt_json["userHandle"]}
    license_str=base64.b64encode(json.dumps(license))
    xbmc.log("waipu license: "+license_str, level=xbmc.LOGDEBUG)
    listitem.setProperty(is_helper.inputstream_addon + '.license_key', "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent="+user_agent+"&Content-Type=text%2Fxml&x-dt-custom-data="+license_str+"|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)

def play_recording(recordingid):

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"
    print "Playing "+recordingid
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    streamingData = w.playRecording(recordingid)
    for stream in streamingData["streamingDetails"]["streams"]:
        if (stream["protocol"] == 'MPEG_DASH'):
                path=stream["href"]
                if path:
                    path=path+"|User-Agent="+user_agent
                    print path
                    break

    listitem = xbmcgui.ListItem(streamingData["epgData"]["title"], path=path)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    # Prepare for drm keys
    jwtheader,jwtpayload,jwtsignature = w.getToken().split(".")
    xbmc.log("waipu jwt payload: "+jwtpayload, level=xbmc.LOGDEBUG)
    jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
    jwt_json = json.loads(jwtpayload_decoded)
    xbmc.log("waipu userhandle: "+jwt_json["userHandle"], level=xbmc.LOGDEBUG)
    license = {'merchant' : 'exaring', 'sessionId' : 'default', 'userId' : jwt_json["userHandle"]}
    license_str=base64.b64encode(json.dumps(license))
    xbmc.log("waipu license: "+license_str, level=xbmc.LOGDEBUG)
    listitem.setProperty(is_helper.inputstream_addon + '.license_key', "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent="+user_agent+"&Content-Type=text%2Fxml&x-dt-custom-data="+license_str+"|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == "play-channel":
            play_channel(params['channel'])
        elif params['action'] == "list-channels":
            list_channels()
        elif params['action'] == "list-recordings":
            list_recordings()
        elif params['action'] == "play-recording":
            play_recording(params['recordingid'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        get_default()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
