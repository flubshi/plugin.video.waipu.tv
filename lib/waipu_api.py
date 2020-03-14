import requests
import time
import base64
import json

try:
    import http.cookiejar
except ImportError:
    import cookielib
import xbmc


class WaipuAPI:
    user_agent = "kodi plugin for waipu.tv (python)"

    def __init__(self, username, password, provider):
        self._auth = None
        self.logged_in = False
        self.__username = username
        self.__password = password
        self.__provider = provider # 0 = waipu, 1 = O2

    def fetchToken(self):
        if self.__provider == 0:
            # waipu
            return self.fetchTokenWaipu()
        else:
            # O2
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
        br = mechanize.Browser()
        cj = cookielib.CookieJar()
        br.set_cookiejar(cj)
        br.set_handle_equiv(False)
        br.set_handle_robots(False)
        br.addheaders = [('authority', 'o2api.waipu.tv'),
                         ('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        br.set_handle_redirect(mechanize.HTTPRedirectHandler)
        response = br.open("https://o2api.waipu.tv/api/o2/login/token?redirectUri=https%3A%2F%2Fo2tv.waipu.tv%2F&inWebview=true")

        # print("login resp: "+response.read())

        br.select_form("Login")

        control = br.form.find_control("IDToken1")
        control.value = self.__username

        control = br.form.find_control("IDToken2")
        control.value = self.__password

        response = br.submit()

        response_plain = str(response.read())
        # print("final-site: " + response_plain)

        if response_plain.find("Ihre Eingabe ist ung&uuml;ltig. Falls Sie einen Business Tarif bei") != -1:
            # invalid login credentials
            return 401

        for cookie in cj:
            if cookie.name == "user_token":
                token = str(cookie.value).strip()
                decoded_token = self.decodeToken(token)
                # print("Cookie: "+cookie.value)
                self._auth = {'access_token': token, "expires": decoded_token["exp"]}

                self.logged_in = True
                return 200

        return -1

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

        jwt_json = json.loads(jwtpayload_decoded)
        return jwt_json


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

        starttime = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime());
        endtime = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + int(epg_hours_future) * 60 * 60))

        url = "https://epg.waipu.tv/api/programs?includeRunningAtStartTime=true&startTime=" + starttime + "&stopTime=" + endtime
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
                if recording['status'] == "FINISHED" or recording['status'] == "RECORDING":
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
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs/current"
        r = requests.get(url, headers=headers)
        return r.json()
    
    def getEPGForChannel(self, channelId):
        self.getToken()
        starttime = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3*24 * 60 * 60));
        endtime = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 3*24 * 60 * 60))
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self._auth['access_token']}
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs?startTime="+starttime+"&stopTime="+endtime
        r = requests.get(url, headers=headers)
        return r.json()
    
    def getUrl(self, url):
        self.getToken()
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self._auth['access_token']}
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