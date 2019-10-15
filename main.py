# -*- coding: utf-8 -*-
# Module: default
# Author: MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from waipu import Waipu
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import xbmcgui
import xbmcplugin
import xbmcaddon
import inputstreamhelper
import time
from dateutil import parser

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
username = xbmcplugin.getSetting(_handle, "username")
password = xbmcplugin.getSetting(_handle, "password")
provider = int(xbmcplugin.getSetting(_handle, "provider_select"))

# open settings, 
if not username or not password:
    xbmcaddon.Addon().openSettings()

w = Waipu(username, password, provider)


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def _T(id):
    return xbmcaddon.Addon().getLocalizedString(id)


def load_acc_details():
    last_check = xbmcplugin.getSetting(_handle, "accinfo_lastcheck")
    info_acc = xbmcplugin.getSetting(_handle, "accinfo_account")
    user = xbmcplugin.getSetting(_handle, "username")

    if info_acc != user or (int(time.time()) - int(last_check)) > 15*60:
        # load acc details
        acc_details = w.getAccountDetails()
        xbmc.log("waipu accdetails: " + str(acc_details), level=xbmc.LOGDEBUG)
        if 'error' in acc_details:
            xbmcaddon.Addon().setSetting('accinfo_status', acc_details["error"])
            xbmcaddon.Addon().setSetting('accinfo_account', "-")
            xbmcaddon.Addon().setSetting('accinfo_subscription', "-")
        else:
            xbmcaddon.Addon().setSetting('accinfo_status', "Angemeldet")
            xbmcaddon.Addon().setSetting('accinfo_account', acc_details["sub"])
            xbmcaddon.Addon().setSetting('accinfo_subscription', acc_details["userAssets"]["account"]["subscription"])
            xbmcaddon.Addon().setSetting('accinfo_lastcheck', str(int(time.time())))
        # load network status
        status = w.getStatus()
        xbmc.log("waipu status: " + str(status), level=xbmc.LOGDEBUG)
        xbmcaddon.Addon().setSetting('accinfo_network_ip', status["ip"])
        if status["statusCode"] == 200:
            xbmcaddon.Addon().setSetting('accinfo_network', "Waipu verfügbar")
        else:
            xbmcaddon.Addon().setSetting('accinfo_network', status["statusText"])

def get_default():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')

    # TV channel list
    list_item = xbmcgui.ListItem(label=_T(32030), iconImage="DefaultAddonPVRClient.png")
    url = get_url(action='list-channels')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

    # recordings list
    list_item = xbmcgui.ListItem(label=_T(32031), iconImage="DefaultFolder.png")
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
    b_episodeid = xbmcplugin.getSetting(_handle, "recordings_episode_id") == "true"
    b_recordingdate = xbmcplugin.getSetting(_handle, "recordings_date") == "true"
    # Iterate through categories
    for recording in recordings:
        if 'locked' in recording and recording['locked']:
            continue
        label_dat = ''
        if recording['status'] == "RECORDING":
            label_dat = '[COLOR red][REC][/COLOR] '

        metadata = {
            'genre': recording['epgData']['genre'],
            'plot': recording['epgData']['description'],
            'mediatype': 'video'}

        if "episodeId" in recording['epgData'] and recording['epgData']['episodeId']:
            # tv show
            if recording['epgData']['episodeTitle']:
                metadata.update({"tvshowtitle": recording['epgData']['episodeTitle']})
                label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B] - " + recording['epgData']['episodeTitle']
            else:
                label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B]"
            if b_episodeid and recording['epgData']['season'] and recording['epgData']['episode']:
                label_dat = label_dat + " (S"+recording['epgData']['season']+"E"+recording['epgData']['episode']+")"
            metadata.update({
                'title': label_dat,
                'season': recording['epgData']['season'],
                'episode': recording['epgData']['episode'],
            })
        else:
            # movie
            label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B]"
            if b_recordingdate and 'startTime' in recording['epgData'] and recording['epgData']['startTime']:
                startDate = parser.parse(recording['epgData']['startTime'])
                label_dat = label_dat + " " + startDate.strftime("(%d.%m.%Y %H:%M)")
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


def filter_pictograms(data, filter=True):
    if filter:
        return ''.join(c for c in data if ord(c) < 0x25A0 or ord(c) > 0x1F5FF)
    return data


def list_channels():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    epg_in_channel = xbmcplugin.getSetting(_handle, "epg_in_channel") == "true"
    epg_in_plot = xbmcplugin.getSetting(_handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(_handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.getChannels(epg_hours_future)
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return

    b_filter = xbmcplugin.getSetting(_handle, "filter_pictograms") == "true"
    # Iterate through categories
    order_index = 0
    for data in channels:
        order_index += 1
        channel = data["channel"]

        if "programs" in data and len(data["programs"]) > 0:
            epg_now = " | " + filter_pictograms(data["programs"][0]["title"], b_filter)

        plot = ""
        b1 = "[B]"
        b2 = "[/B]"
        if epg_in_plot and "programs" in data:
            for program in data["programs"]:
                starttime = parser.parse(program["startTime"]).strftime("%H:%M")
                plot += "[B]" + starttime + " Uhr:[/B] " + b1 + filter_pictograms(program["title"],
                                                                                  b_filter) + b2 + "\n"
                b1 = ""
                b2 = ""
        elif not epg_in_plot and "programs" in data and len(data["programs"]) > 0:
            plot = filter_pictograms(data["programs"][0]["description"], b_filter)

        if epg_in_channel:
            title = "[B]" + channel['displayName'] + "[/B]" + epg_now
        else:
            title = "[B]" + channel['displayName'] + "[/B]"

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': title,
                                    'tracknumber': order_index,
                                    'plot': plot,
                                    'mediatype': 'video'})
        logo_url = ""
        livePlayoutURL = ""
        for link in channel["links"]:
            if link["rel"] == "iconsd":
                logo_url = link["href"] + "?width=200&height=200"
            if link["rel"] == "livePlayout":
                livePlayoutURL = link["href"]

        list_item.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play-channel', playouturl=livePlayoutURL,
                      title=title.encode('ascii', 'ignore').decode('ascii'), logourl=logo_url)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=False)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def play_channel(playouturl, title, logo_url):
    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "kodi plugin for waipu.tv (python)"
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    channel = w.playChannel(playouturl)
    xbmc.log("play channel: " + str(channel), level=xbmc.LOGDEBUG)

    stream_select = xbmcplugin.getSetting(_handle, "stream_select")
    xbmc.log("stream to be played: " + str(stream_select), level=xbmc.LOGDEBUG)

    for stream in channel["streams"]:
        if (stream["protocol"] == 'mpeg-dash'):
            # if (stream["protocol"] == 'hls'):
            for link in stream['links']:
                path = link["href"]
                rel = link["rel"]
                if path and (stream_select == "auto" or rel == stream_select):
                    path = path + "|User-Agent=" + user_agent
                    xbmc.log("selected stream: " + str(link), level=xbmc.LOGDEBUG)
                    break
    if not path:
        xbmc.executebuiltin(
            'Notification("Stream selection","No stream of type \'' + str(stream_select) + '\' found",10000)')
        return

    listitem = xbmcgui.ListItem(channel["channel"], path=path)
    listitem.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})

    metadata = {'title': title, 'mediatype': 'video'}

    if xbmcplugin.getSetting(_handle, "metadata_on_play") == "true":
        current_program = w.getCurrentProgram(channel["channel"])
        xbmc.log("play channel metadata: " + str(current_program), level=xbmc.LOGDEBUG)

        b_filter = xbmcplugin.getSetting(_handle, "filter_pictograms") == "true"

        description = ""
        if "title" in current_program and current_program["title"] is not None:
            description = "[B]" + filter_pictograms(current_program["title"], b_filter) + "[/B]\n"
            metadata.update({'title': filter_pictograms(current_program["title"], b_filter)})
        if "description" in current_program and current_program["description"] is not None:
            description += filter_pictograms(current_program["description"], b_filter)
        metadata.update({'plot': description})

    listitem.setInfo('video', metadata)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
    # License update, to be tested...
    # listitem.setProperty(is_helper.inputstream_addon + ".media_renewal_url", get_url(action='renew_token', playouturl=playouturl))

    license_str = w.getLicense()
    listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                         "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" + user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" + license_str + "|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)


def renew_token(playouturl):
    # user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"
    channel = w.playChannel(playouturl)
    xbmc.log("renew channel token: " + str(channel), level=xbmc.LOGDEBUG)

    stream_select = xbmcplugin.getSetting(_handle, "stream_select")
    xbmc.log("stream to be renewed: " + str(stream_select), level=xbmc.LOGDEBUG)

    url = ""
    for stream in channel["streams"]:
        if (stream["protocol"] == 'mpeg-dash'):
            # if (stream["protocol"] == 'hls'):
            for link in stream['links']:
                path = link["href"]
                rel = link["rel"]
                if path and (stream_select == "auto" or rel == stream_select):
                    # path=path+"|User-Agent="+user_agent
                    url = path
                    xbmc.log("selected renew stream: " + str(link), level=xbmc.LOGDEBUG)
                    break
    xbmc.executebuiltin(
        'Notification("Stream RENEW","tada",30000)')
    listitem = xbmcgui.ListItem()
    xbmcplugin.addDirectoryItem(_handle, url, listitem)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)


def play_recording(recordingid):
    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "kodi plugin for waipu.tv (python)"

    streamingData = w.playRecording(recordingid)
    xbmc.log("play recording: " + str(streamingData), level=xbmc.LOGDEBUG)

    for stream in streamingData["streamingDetails"]["streams"]:
        if (stream["protocol"] == 'MPEG_DASH'):
            path = stream["href"]
            if path:
                path = path + "|User-Agent=" + user_agent
                # print(path)
                break

    b_filter = xbmcplugin.getSetting(_handle, "filter_pictograms") == "true"
    b_episodeid = xbmcplugin.getSetting(_handle, "recordings_episode_id") == "true"
    b_recordingdate = xbmcplugin.getSetting(_handle, "recordings_date") == "true"
    title = ""
    metadata = {'mediatype': 'video'}
    if streamingData["epgData"]["title"]:
        title = filter_pictograms(streamingData["epgData"]["title"], b_filter)
    if streamingData["epgData"]["episodeTitle"]:
        title = title + ": " + filter_pictograms(streamingData["epgData"]["episodeTitle"], b_filter)
    if b_recordingdate and not streamingData["epgData"]["episodeId"] and streamingData["epgData"]["startTime"]:
        startDate = parser.parse(streamingData['epgData']['startTime'])
        title = title + " " + startDate.strftime("(%d.%m.%Y %H:%M)")
    if b_episodeid and streamingData['epgData']['season'] and streamingData['epgData']['episode']:
        title = title + " (S" + streamingData['epgData']['season'] + "E" + streamingData['epgData']['episode'] + ")"
        metadata.update({
            'season': streamingData['epgData']['season'],
            'episode': streamingData['epgData']['episode'],
        })

    metadata.update({"title": title})

    listitem = xbmcgui.ListItem(title, path=path)

    if "epgData" in streamingData and streamingData["epgData"]["description"]:
        metadata.update({"plot": filter_pictograms(streamingData["epgData"]["description"], b_filter)})

    if "epgData" in streamingData and len(streamingData["epgData"]["previewImages"]) > 0:
        logo_url = streamingData["epgData"]["previewImages"][0] + "?width=256&height=256"
        listitem.setArt({'thumb': logo_url, 'icon': logo_url})

    listitem.setInfo('video', metadata)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    license_str = w.getLicense()
    listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                         "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" + user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" + license_str + "|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)


def router(paramstring):
    params = dict(urlparse.parse_qsl(paramstring))
    if params:
        if params['action'] == "play-channel":
            play_channel(params['playouturl'], params['title'], params['logourl'])
        elif params['action'] == "list-channels":
            load_acc_details()
            list_channels()
        elif params['action'] == "list-recordings":
            list_recordings()
        elif params['action'] == "play-recording":
            play_recording(params['recordingid'])
        elif params['action'] == "renew_token":
            renew_token(params['playouturl'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        load_acc_details()
        get_default()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
