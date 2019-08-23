import requests
import time
import base64
import json


class Waipu:
    user_agent = "kodi plugin for waipu.tv (python)"

    def __init__(self, username, password):
        self._auth = None
        self.logged_in = False
        self.__username = username
        self.__password = password

    def fetchToken(self):
        url = "https://auth.waipu.tv/oauth/token"
        payload = {'username': self.__username, 'password': self.__password, 'grant_type': 'password'}
        headers = {'User-Agent': self.user_agent,
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

    def getAccountDetails(self):
        try:
            token = self.getToken()
        except Exception as e:
            return {'error': str(e)}
        if token:
            jwtheader, jwtpayload, jwtsignature = token.split(".")
            jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
            jwt_json = json.loads(jwtpayload_decoded)
            return jwt_json
        return {'error': 'unknown'}

    def getLicense(self):
        # Prepare for drm keys
        acc_details = self.getAccountDetails()
        license = {'merchant': 'exaring', 'sessionId': 'default', 'userId': acc_details["userHandle"]}
        license_str = base64.b64encode(json.dumps(license))
        return license_str

    def getAccountChannels(self):
        jwtheader, jwtpayload, jwtsignature = self.getToken().split(".")
        jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
        jwt_json = json.loads(jwtpayload_decoded)

        acc_channels = []
        acc_channels += jwt_json["userAssets"]["channels"]["SD"]
        acc_channels += jwt_json["userAssets"]["channels"]["HD"]
        return acc_channels


    def getChannels(self, epg_hours_future = 0):
        self.getToken()

        starttime = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime());
        endtime = time.strftime("%Y-%m-%dT%H:%M:%S",time.localtime(time.time() + int(epg_hours_future)*60*60))

        url = "https://epg.waipu.tv/api/programs?includeRunningAtStartTime=true&startTime="+starttime+"&stopTime="+endtime
        headers = {'User-Agent': self.user_agent,
                   'Accept': 'application/vnd.waipu.epg-channels-and-programs-v1+json',
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        acc_channels = self.getAccountChannels()
        channels_data = requests.get(url, headers=headers).json()
        channels = []
        for channel in channels_data:
            if channel["channel"]["id"] in acc_channels:
                channels.append(channel)
        return channels

    def getRecordings(self):
        self.getToken()
        url = "https://recording.waipu.tv/api/recordings"
        headers = {'User-Agent': self.user_agent,
                   'Accept': 'application/vnd.waipu.recordings-v2+json',
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(url, headers=headers)
        recordings = []
        if r.status_code == 200:
            for recording in r.json():
                if recording['status'] == "FINISHED":
                    recordings.append(recording)
        return recordings

    def getStatus(self):
        url = "https://status.wpstr.tv/status?nw=wifi"
        headers = {'User-Agent': self.user_agent}
        r = requests.get(url, headers=headers)
        return r.json()

    def getCurrentProgram(self, channelId):
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self._auth['access_token'],
                   'Accept': 'application/vnd.waipu.epg-program-v1+json'}
        url = "https://epg.waipu.tv/api/channels/"+channelId+"/programs/current"
        r = requests.get(url, headers=headers)
        return r.json()

    def playChannel(self, playouturl):
        self.getToken()

        payload = {'network': 'wlan'}
        headers = {'User-Agent': self.user_agent,
            'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(playouturl, data=payload, headers=headers)
        return r.json()

    def playRecording(self, id):
        self.getToken()
        url = "https://recording.waipu.tv/api/recordings/" + str(id)
        payload = {'network': 'wlan'}
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        r = requests.get(url, data=payload, headers=headers)
        return r.json()
