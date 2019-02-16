import requests
import time


class Waipu:
    def __init__(self, username, password):
        self._auth = None
        self.logged_in = False
        self.__username = username
        self.__password = password

    def fetchToken(self):
        url = "https://auth.waipu.tv/oauth/token"
        payload = {'username': self.__username, 'password': self.__password, 'grant_type': 'password'}
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)',
                   'Authorization': 'Basic YW5kcm9pZENsaWVudDpzdXBlclNlY3JldA=='}
        self._auth = None
        r = requests.post(url, data=payload, headers=headers)
        if r.status_code == 200:
            self._auth = r.json()
            self.logged_in = True
            self._auth["expires"] = time.time() + self._auth["expires_in"]
        return r.status_code

    def getToken(self):
        if self._auth is None or self._auth["expires"] <= time.time():
            code = self.fetchToken()
            if code == 401:
                raise Exception("Login: Invalid user/password!")
            elif code != 200:
                raise Exception("Can't login, Code=" + str(code))
        # TODO: renew token
        return self._auth['access_token']

    def getChannels(self, epg_hours_future = 0):
        self.getToken()

        starttime = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime());
        endtime = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(time.time() + int(epg_hours_future)*60*60))

        url = "https://epg.waipu.tv/api/programs?includeRunningAtStartTime=true&startTime="+starttime+"&stopTime="+endtime
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)',
                   'Accept': 'application/vnd.waipu.epg-channels-and-programs-v1+json',
                   'Authorization': 'Bearer ' + self._auth['access_token']}

        channels = requests.get(url, headers=headers)
        return channels.json()

    def getRecordings(self):
        self.getToken()
        url = "https://recording.waipu.tv/api/recordings"
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)',
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(url, headers=headers)
        recordings = []
        if r.status_code == 200:
            for recording in r.json():
                if recording['status'] == "FINISHED":
                    recordings.append(recording)
        return recordings

    def getStatus(self):
        self.getToken()
        url = "https://status.wpstr.tv/status?nw=wifi"
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)'}
        r = requests.get(url, headers=headers)

    def playChannel(self, playouturl):
        self.getToken()

        payload = {'network': 'wlan'}
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)',
            'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(playouturl, data=payload, headers=headers)
        return r.json()

    def playRecording(self, id):
        self.getToken()
        url = "https://recording.waipu.tv/api/recordings/" + str(id)
        payload = {'network': 'wlan'}
        headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)',
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(url, data=payload, headers=headers)
        return r.json()
