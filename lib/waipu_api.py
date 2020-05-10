import requests
import time
import base64
import json
import xbmc


class WaipuAPI:
    user_agent = "kodi plugin for waipu.tv (python)"

    def __init__(self, username, password, provider):
        self._auth = None
        self.logged_in = False
        self.__username = username
        self.__password = password
        self.__provider = provider  # 0 = waipu, 1 = O2

    def fetchToken(self):
        if self.__provider == 0:
            return self.fetchTokenWaipu()
        else:
            return self.fetchTokenO2()

    def fetchTokenWaipu(self):
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

    def fetchTokenO2(self):
        import mechanize
        try:
            import http.cookiejar as cookielib
        except ImportError:
            import cookielib
        br = mechanize.Browser()
        cj = cookielib.CookieJar()
        br.set_cookiejar(cj)
        br.set_handle_equiv(False)
        br.set_handle_robots(False)
        br.addheaders = [('authority', 'o2api.waipu.tv'),
                         ('User-agent',
                          'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        br.set_handle_redirect(mechanize.HTTPRedirectHandler)
        br.open("https://o2api.waipu.tv/api/o2/login/token?redirectUri=https%3A%2F%2Fo2tv.waipu.tv%2F&inWebview=true")
        br.select_form("Login")
        control = br.form.find_control("IDToken1")
        control.value = self.__username
        control = br.form.find_control("IDToken2")
        control.value = self.__password
        response = br.submit()
        response_plain = str(response.read())
        if response_plain.find("Ihre Eingabe ist ung&uuml;ltig. Falls Sie einen Business Tarif bei") != -1:
            # invalid login credentials
            return 401
        for cookie in cj:
            if cookie.name == "user_token":
                token = str(cookie.value).strip()
                decoded_token = self.decodeToken(token)
                self._auth = {'access_token': token, "expires": decoded_token["exp"]}

                self.logged_in = True
                return 200
        return -1

    def prepareHeaders(self, additional_headers=dict()):
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        headers.update(additional_headers)
        return headers

    def getToken(self):
        if self._auth is None or self._auth["expires"] <= time.time():
            code = self.fetchToken()
            if code == 401:
                raise Exception("Login: Invalid user/password!")
            elif code != 200:
                raise Exception("Can't login, Code=" + str(code))
        # TODO: renew token
        return self._auth['access_token']

    def decodeToken(self, token):
        jwtheader, jwtpayload, jwtsignature = token.split(".")
        jwtpayload = jwtpayload.replace("_", "/").replace("-", "+")
        try:
            jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
        except TypeError:
            xbmc.log("base64 padding error: " + str(jwtpayload), level=xbmc.LOGERROR)
            raise
        return json.loads(jwtpayload_decoded)

    def getAccountDetails(self):
        try:
            token = self.getToken()
        except Exception as e:
            return {'error': str(e)}
        if token:
            return self.decodeToken(token)
        return {'error': 'unknown'}

    def getLicense(self):
        # Prepare for drm keys
        acc_details = self.getAccountDetails()
        license = {'merchant': 'exaring', 'sessionId': 'default', 'userId': acc_details["userHandle"]}
        try:
            license_str = base64.b64encode(json.dumps(license))
            return license_str
        except Exception as e:
            license_str = base64.b64encode(json.dumps(license).encode("utf-8"))
            return str(license_str, "utf-8")

    def getAccountChannels(self):
        jwt_json = self.decodeToken(self.getToken())
        acc_channels = []
        acc_channels += jwt_json["userAssets"]["channels"]["SD"]
        acc_channels += jwt_json["userAssets"]["channels"]["HD"]
        return acc_channels

    def getChannels(self, epg_hours_future=0):
        self.getToken()

        start_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        end_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + int(epg_hours_future) * 60 * 60))

        url = "https://epg.waipu.tv/api/programs?includeRunningAtStartTime=true&startTime=" + start_time + \
              "&stopTime=" + end_time
        headers = self.prepareHeaders({'Accept': 'application/vnd.waipu.epg-channels-and-programs-v1+json'})
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
        headers = self.prepareHeaders({'Accept': 'application/vnd.waipu.recordings-v2+json'})
        r = requests.get(url, headers=headers)
        recordings = []
        if r.status_code == 200:
            for recording in r.json():
                if recording['status'] == "FINISHED" or recording['status'] == "RECORDING":
                    recordings.append(recording)
        return recordings

    def getStatus(self):
        return requests.get("https://status.wpstr.tv/status?nw=wifi", headers=self.prepareHeaders()).json()

    def getCurrentProgram(self, channelId):
        headers = self.prepareHeaders({'Accept': 'application/vnd.waipu.epg-program-v1+json'})
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs/current"
        return requests.get(url, headers=headers).json()

    def getEPGForChannel(self, channelId):
        self.getToken()
        start_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 24 * 60 * 60))
        end_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 3 * 24 * 60 * 60))
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs?startTime=" + start_time + \
              "&stopTime=" + end_time
        return requests.get(url, headers=self.prepareHeaders()).json()

    def getUrl(self, url):
        self.getToken()
        return requests.get(url, headers=self.prepareHeaders()).json()

    def playChannel(self, playouturl):
        self.getToken()
        return requests.get(playouturl, data={'network': 'wlan'}, headers=self.prepareHeaders()).json()

    def playRecording(self, id):
        self.getToken()
        url = "https://recording.waipu.tv/api/recordings/" + str(id)
        return requests.get(url, data={'network': 'wlan'}, headers=self.prepareHeaders()).json()
