# -*- coding: utf-8 -*-
# Module: default
# Author: MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import xbmcplugin
import xbmcaddon
import menu_helper

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
username = xbmcplugin.getSetting(_handle, "username")
password = xbmcplugin.getSetting(_handle, "password")

# open settings, 
if not username or not password:
    xbmcaddon.Addon().openSettings()

def router(paramstring):
    params = dict(urlparse.parse_qsl(paramstring))
    if params:
        if params['action'] == "play-channel":
            menu_helper.play_channel(params['playouturl'], params['title'], params['logourl'])
        elif params['action'] == "list-channels":
            menu_helper.load_acc_details()
            menu_helper.list_channels()
        elif params['action'] == "list-recordings":
            menu_helper.list_recordings()
        elif params['action'] == "play-recording":
            menu_helper.play_recording(params['recordingid'])
        elif params['action'] == "renew_token":
            menu_helper.renew_token(params['playouturl'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        menu_helper.load_acc_details()
        menu_helper.get_default()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
