# -*- coding: utf-8 -*-
# Module: default
# Author: flubshi, MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import routing
from lib.waipu_api import WaipuAPI
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import inputstreamhelper
import time
from dateutil import parser

plugin = routing.Plugin()

username = xbmcplugin.getSetting(plugin.handle, "username")
password = xbmcplugin.getSetting(plugin.handle, "password")
provider = int(xbmcplugin.getSetting(plugin.handle, "provider_select"))

# open settings,
if not username or not password:
    xbmcaddon.Addon().openSettings()

w = WaipuAPI(username, password, provider)

user_agent = "kodi plugin for waipu.tv (python)"  # "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"


def _T(string_id):
    return xbmcaddon.Addon().getLocalizedString(string_id)


def load_acc_details():
    last_check = xbmcplugin.getSetting(plugin.handle, "accinfo_lastcheck")
    info_acc = xbmcplugin.getSetting(plugin.handle, "accinfo_account")
    user = xbmcplugin.getSetting(plugin.handle, "username")

    if info_acc != user or (int(time.time()) - int(last_check)) > 15 * 60:
        # load acc details
        acc_details = w.get_account_details()
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
        status = w.get_status()
        xbmc.log("waipu status: " + str(status), level=xbmc.LOGDEBUG)
        xbmcaddon.Addon().setSetting('accinfo_network_ip', status["ip"])
        if status["statusCode"] == 200:
            xbmcaddon.Addon().setSetting('accinfo_network', "Waipu verfügbar")
        else:
            xbmcaddon.Addon().setSetting('accinfo_network', status["statusText"])


@plugin.route('/list-recordings')
def list_recordings():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    # Get video categories
    try:
        recordings = w.get_recordings()
    except Exception as e:
        xbmcgui.Dialog().ok("Error", str(e))
        return
    b_episodeid = xbmcplugin.getSetting(plugin.handle, "recordings_episode_id") == "true"
    b_recording_date = xbmcplugin.getSetting(plugin.handle, "recordings_date") == "true"
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
                label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B] - " + recording['epgData'][
                    'episodeTitle']
            else:
                label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B]"
            if b_episodeid and recording['epgData']['season'] and recording['epgData']['episode']:
                label_dat = label_dat + " (S" + recording['epgData']['season'] + "E" + recording['epgData'][
                    'episode'] + ")"
            metadata.update({
                'title': label_dat,
                'season': recording['epgData']['season'],
                'episode': recording['epgData']['episode'],
            })
        else:
            # movie
            label_dat = label_dat + "[B]" + recording['epgData']['title'] + "[/B]"
            if b_recording_date and 'startTime' in recording['epgData'] and recording['epgData']['startTime']:
                start_date = parser.parse(recording['epgData']['startTime'])
                label_dat = label_dat + " " + start_date.strftime("(%d.%m.%Y %H:%M)")
            metadata.update({'title': label_dat})

        list_item = xbmcgui.ListItem(label=label_dat)
        list_item.setInfo('video', metadata)

        for previewImage in recording['epgData']['previewImages']:
            previewImage += "?width=200&height=200"
            xbmc.log("waipu image: " + previewImage, level=xbmc.LOGDEBUG)
            list_item.setArt(
                {'thumb': previewImage, 'icon': previewImage, 'clearlogo': previewImage})
            break
        list_item.setProperty('IsPlayable', 'true')
        url = plugin.url_for(play_recording, recording_id=recording["id"])
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)


def filter_pictograms(data, apply_filter=True):
    if apply_filter:
        return ''.join(c for c in data if ord(c) < 0x25A0 or ord(c) > 0x1F5FF)
    return data


def play_inputstream(url, metadata=dict(), art=dict()):
    title = ''
    if 'title' in metadata:
        title = metadata['title']

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    listitem = xbmcgui.ListItem(title, path=url)
    listitem.setInfo('video', metadata)
    listitem.setArt(art)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    # License update, to be tested... listitem.setProperty(is_helper.inputstream_addon + ".media_renewal_url",
    # get_url(action='renew_token', playouturl=playouturl))

    listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                         "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" +
                         user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" +
                         w.get_license() + "|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(plugin.handle, True, listitem=listitem)
    return True


@plugin.route('/play-vod')
def play_vod():
    title = plugin.args['title'][0]

    stream = w.get_url(plugin.args['streamUrlProvider'][0])

    if "player" in stream and "mpd" in stream["player"]:
        return play_inputstream(stream["player"]["mpd"], {'title': title})
    else:
        return False


@plugin.route('/list-vod-channel')
def list_vod_channel():
    channel_id = plugin.args['channel_id'][0]

    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    streams = w.get_epg_for_channel(channel_id)
    for stream in streams:
        # print("stream: "+str(stream))
        title = filter_pictograms(stream["title"])

        preview_image = ""
        if "previewImages" in stream:
            preview_image = stream["previewImages"][0] + "?width=200&height=200"

        plot = ""
        if "description" in stream:
            plot = stream["description"]

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': title,
                                    'plot': plot,
                                    'mediatype': 'video'})

        list_item.setArt({'thumb': preview_image, 'icon': preview_image, 'clearlogo': preview_image})
        list_item.setProperty('IsPlayable', 'true')

        url = plugin.url_for(play_vod, streamUrlProvider=stream["streamUrlProvider"],
                             title=title.encode('ascii', 'ignore').decode('ascii'), logo_url=preview_image)
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/list-vod-channels')
def list_vod_channels():
    load_acc_details()
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    epg_in_plot = xbmcplugin.getSetting(plugin.handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(plugin.handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.get_channels(epg_hours_future)
    except Exception as e:
        xbmcgui.Dialog().ok("Error", str(e))
        return

    # Iterate through categories
    order_index = 0
    for data in channels:
        channel = data["channel"]

        if not ("properties" in channel and "tvfuse" in channel["properties"]):
            # is not VoD channel
            continue

        order_index += 1
        title = channel['displayName']

        list_item = xbmcgui.ListItem(label=title)
        logo_url = ""
        for link in channel["links"]:
            if link["rel"] == "iconsd":
                logo_url = link["href"] + "?width=200&height=200"

        list_item.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})
        url = plugin.url_for(list_vod_channel, channel_id=channel['id'])
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=True)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/list-channels')
def list_channels():
    load_acc_details()
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    # Get video categories
    epg_in_channel = xbmcplugin.getSetting(plugin.handle, "epg_in_channel") == "true"
    epg_in_plot = xbmcplugin.getSetting(plugin.handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(plugin.handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.get_channels(epg_hours_future)
    except Exception as e:
        xbmcgui.Dialog().ok("Error", str(e))
        return

    b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"
    # Iterate through categories
    order_index = 0
    for data in channels:
        channel = data["channel"]

        if "properties" in channel and "tvfuse" in channel["properties"]:
            continue  # is VoD channel

        order_index += 1

        plot = ""
        b1 = "[B]"
        b2 = "[/B]"
        if epg_in_plot and "programs" in data:
            for program in data["programs"]:
                start_time = parser.parse(program["startTime"]).strftime("%H:%M")
                plot += "[B]" + start_time + " Uhr:[/B] " + \
                        b1 + filter_pictograms(program["title"], b_filter) + b2 + "\n"
                b1 = ""
                b2 = ""
        elif not epg_in_plot and "programs" in data and len(data["programs"]) > 0:
            plot = filter_pictograms(data["programs"][0]["description"], b_filter)

        if epg_in_channel and "programs" in data and len(data["programs"]) > 0:
            title = "[B]" + channel['displayName'] + "[/B] | " + \
                    filter_pictograms(data["programs"][0]["title"], b_filter)
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
        url = plugin.url_for(play_channel, playout_url=livePlayoutURL,
                             title=title.encode('ascii', 'ignore').decode('ascii'), logo_url=logo_url)
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/play-channel')
def play_channel():
    title = plugin.args['title'][0]
    logo_url = plugin.args['logo_url'][0]

    channel = w.play_channel(plugin.args['playout_url'][0])
    xbmc.log("play channel: " + str(channel), level=xbmc.LOGDEBUG)

    stream_select = xbmcplugin.getSetting(plugin.handle, "stream_select")
    xbmc.log("stream to be played: " + str(stream_select), level=xbmc.LOGDEBUG)

    for stream in channel["streams"]:
        if stream["protocol"] == 'mpeg-dash':
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

    art = {'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url}
    metadata = {'title': title, 'mediatype': 'video'}

    if xbmcplugin.getSetting(plugin.handle, "metadata_on_play") == "true":
        current_program = w.get_current_program(channel["channel"])
        xbmc.log("play channel metadata: " + str(current_program), level=xbmc.LOGDEBUG)

        b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"

        description = ""
        if "title" in current_program and current_program["title"] is not None:
            description = "[B]" + filter_pictograms(current_program["title"], b_filter) + "[/B]\n"
            metadata.update({'title': filter_pictograms(current_program["title"], b_filter)})
        if "description" in current_program and current_program["description"] is not None:
            description += filter_pictograms(current_program["description"], b_filter)
        metadata.update({'plot': description})

    return play_inputstream(path, metadata, art)


@plugin.route('/renew-token')
def renew_token():
    channel = w.play_channel(plugin.args['playouturl'][0])
    xbmc.log("renew channel token: " + str(channel), level=xbmc.LOGDEBUG)

    stream_select = xbmcplugin.getSetting(plugin.handle, "stream_select")
    xbmc.log("stream to be renewed: " + str(stream_select), level=xbmc.LOGDEBUG)

    url = ""
    for stream in channel["streams"]:
        if stream["protocol"] == 'mpeg-dash':
            for link in stream['links']:
                path = link["href"]
                rel = link["rel"]
                if path and (stream_select == "auto" or rel == stream_select):
                    url = path
                    xbmc.log("selected renew stream: " + str(link), level=xbmc.LOGDEBUG)
                    break
    xbmc.executebuiltin(
        'Notification("Stream RENEW","tada",30000)')
    listitem = xbmcgui.ListItem()
    xbmcplugin.addDirectoryItem(plugin.handle, url, listitem)
    xbmcplugin.endOfDirectory(plugin.handle, cacheToDisc=False)


@plugin.route('/play-recording')
def play_recording():
    streaming_data = w.play_recording(plugin.args['recording_id'][0])
    xbmc.log("play recording: " + str(streaming_data), level=xbmc.LOGDEBUG)

    for stream in streaming_data["streamingDetails"]["streams"]:
        if stream["protocol"] == 'MPEG_DASH':
            path = stream["href"]
            if path:
                path = path + "|User-Agent=" + user_agent
                # print(path)
                break

    b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"
    b_episodeid = xbmcplugin.getSetting(plugin.handle, "recordings_episode_id") == "true"
    b_recordingdate = xbmcplugin.getSetting(plugin.handle, "recordings_date") == "true"
    title = ""
    metadata = {'mediatype': 'video'}
    if streaming_data["epgData"]["title"]:
        metadata['title'] = filter_pictograms(streaming_data["epgData"]["title"], b_filter)
    if streaming_data["epgData"]["episodeTitle"]:
        title = title + ": " + filter_pictograms(streaming_data["epgData"]["episodeTitle"], b_filter)
    if b_recordingdate and not streaming_data["epgData"]["episodeId"] and streaming_data["epgData"]["startTime"]:
        start_date = parser.parse(streaming_data['epgData']['startTime'])
        title = title + " " + start_date.strftime("(%d.%m.%Y %H:%M)")
    if b_episodeid and streaming_data['epgData']['season'] and streaming_data['epgData']['episode']:
        title = title + " (S" + streaming_data['epgData']['season'] + "E" + streaming_data['epgData']['episode'] + ")"
        metadata.update({
            'season': streaming_data['epgData']['season'],
            'episode': streaming_data['epgData']['episode'],
        })

    metadata.update({"title": title})

    if "epgData" in streaming_data and streaming_data["epgData"]["description"]:
        metadata.update({"plot": filter_pictograms(streaming_data["epgData"]["description"], b_filter)})

    art = dict()
    if "epgData" in streaming_data and len(streaming_data["epgData"]["previewImages"]) > 0:
        logo_url = streaming_data["epgData"]["previewImages"][0] + "?width=256&height=256"
        art = {'thumb': logo_url, 'icon': logo_url}

    return play_inputstream(path, metadata, art)


@plugin.route('/')
def index():
    load_acc_details()

    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')

    # TV channel list
    list_item = xbmcgui.ListItem(label=_T(32030))
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_channels), list_item, isFolder=True)

    # VoD Channels
    list_item = xbmcgui.ListItem(label=_T(32032))
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_vod_channels), list_item, isFolder=True)

    # recordings list
    list_item = xbmcgui.ListItem(label=_T(32031))
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_recordings), list_item, isFolder=True)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)


def run():
    plugin.run()
