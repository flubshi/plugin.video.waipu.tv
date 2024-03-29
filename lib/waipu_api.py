import requests
import time
import base64
import json
import xbmc
import xbmcaddon


class WaipuAPI:
    user_agent = "kodi plugin for waipu.tv (python)"

    def __init__(self, username, password, provider, device_id, user_agent):
        self._access_token = xbmcaddon.Addon().getSetting("access_token")
        self.__username = username
        self.__password = password
        self.__provider = provider  # 0 = waipu, 1 = O2
        self.__device_id = device_id
        self.user_agent = user_agent


    def is_jwt_valid(self, jwt_str, threshold=0):
        jwt = self.decode_token(jwt_str)
        exp = int(jwt["exp"])
        return time.time() < (exp - threshold)


    def fetch_waipu_token(self):
        # assume access token expired -> check refresh_token
        refresh_token = xbmcaddon.Addon().getSetting("refresh_token")
        if refresh_token and self.is_jwt_valid(refresh_token):
            # refresh is valid, lets use it
            payload = {'refresh_token': refresh_token,
                       'grant_type': 'refresh_token',
                       'waipu_device_id': self.__device_id}
            xbmc.log("Fetch access token by using refresh token", level=xbmc.LOGDEBUG)
        else:
            # use pw grant
            payload = {'username': self.__username,
                       'password': self.__password,
                       'grant_type': 'password',
                       'waipu_device_id': self.__device_id}
            xbmc.log("Fetch access token by using password grant", level=xbmc.LOGDEBUG)

        url = "https://auth.waipu.tv/oauth/token"
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Basic YW5kcm9pZENsaWVudDpzdXBlclNlY3JldA=='}

        try:
            r = requests.post(url, data=payload, headers=headers)
        except requests.exceptions.ConnectionError as e:
            xbmc.log("Error while fetching waipu token - No HTTP connection?", level=xbmc.LOGERROR)

        if r.status_code == 200:
            jwt = r.json()
            self._access_token = jwt["access_token"]
            xbmcaddon.Addon().setSetting("access_token", self._access_token)
            if "refresh_token" in jwt:
                xbmcaddon.Addon().setSetting("refresh_token", jwt["refresh_token"])
            return self._access_token
        else:
            # TODO add error handling
            xbmc.log("Error while fetching waipu token - HTTP code: " + str(r.status_code), level=xbmc.LOGERROR)
            raise Exception("Error: no valid access token")
        return ""

    def fetch_o2_token(self):
        import mechanize
        try:
            import http.cookiejar as cookie
        except ImportError:
            import cookie
        br = mechanize.Browser()
        cj = cookie.CookieJar()
        br.set_cookiejar(cj)
        br.set_handle_equiv(False)
        br.set_handle_robots(False)
        br.addheaders = [('authority', 'o2api.waipu.tv'),
                         ('User-agent',
                          'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 '
                          'Firefox/3.0.1')]
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
                decoded_token = self.decode_token(token)
                self._access_token = token
                xbmcaddon.Addon().setSetting("access_token", token)

                return 200
        return -1

    def prepare_headers(self, additional_headers=dict()):
        headers = {'User-Agent': self.user_agent,
                   'Authorization': 'Bearer ' + self.get_token()}
        headers.update(additional_headers)
        return headers

    def get_token(self):
        if not self._access_token or not self.is_jwt_valid(self._access_token):
            if self.__provider == 0:
                return self.fetch_waipu_token()
            else:
                return self.fetch_o2_token()
        return self._access_token

    def decode_token(self, token):
        jwtheader, jwtpayload, jwtsignature = token.split(".")
        jwtpayload = jwtpayload.replace("_", "/").replace("-", "+")
        try:
            jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
        except TypeError:
            xbmc.log("base64 padding error: " + str(jwtpayload), level=xbmc.LOGERROR)
            raise
        return json.loads(jwtpayload_decoded)

    def get_account_details(self):
        try:
            token = self.get_token()
        except Exception as e:
            return {'error': str(e)}
        if token:
            return self.decode_token(token)
        return {'error': 'unknown'}

    def get_license(self):
        # Prepare for drm keys
        acc_details = self.get_account_details()
        license = {'merchant': 'exaring', 'sessionId': 'default', 'userId': acc_details["userHandle"]}
        try:
            license_str = base64.b64encode(json.dumps(license))
            return license_str
        except Exception as e:
            license_str = base64.b64encode(json.dumps(license).encode("utf-8"))
            return str(license_str, "utf-8")

    def get_account_channels(self):
        jwt_json = self.decode_token(self.get_token())
        acc_channels = []
        acc_channels += jwt_json["userAssets"]["channels"]["SD"]
        acc_channels += jwt_json["userAssets"]["channels"]["HD"]
        return acc_channels

    def get_channels(self, epg_hours_future=0):
        self.get_token()

        start_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        end_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + int(epg_hours_future) * 60 * 60))

        url = "https://epg.waipu.tv/api/programs?includeRunningAtStartTime=true&startTime=" + start_time + \
              "&stopTime=" + end_time
        headers = self.prepare_headers({'Accept': 'application/vnd.waipu.epg-channels-and-programs-v1+json'})
        acc_channels = self.get_account_channels()
        channels_data = requests.get(url, headers=headers).json()
        channels = []
        for channel in channels_data:
            if channel["channel"]["id"] in acc_channels:
                channels.append(channel)
        return channels

    def get_recordings(self):
        self.get_token()
        url = "https://recording.waipu.tv/api/recordings"
        headers = self.prepare_headers({'Accept': 'application/vnd.waipu.recordings-v2+json'})
        r = requests.get(url, headers=headers)
        recordings = []
        if r.status_code == 200:
            for recording in r.json():
                if recording['status'] == "FINISHED" or recording['status'] == "RECORDING":
                    recordings.append(recording)
        return recordings

    def get_status(self):
        jwt_json = self.decode_token(self.get_token())
        return requests.get("https://status.wpstr.tv/status?uh=" + str(jwt_json["userHandle"]),
                            headers=self.prepare_headers()).json()

    def get_current_program(self, channelId):
        headers = self.prepare_headers({'Accept': 'application/vnd.waipu.epg-program-v1+json'})
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs/current"
        return requests.get(url, headers=headers).json()

    def get_epg_for_channel(self, channelId):
        self.get_token()
        start_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 24 * 60 * 60))
        end_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 3 * 24 * 60 * 60))
        url = "https://epg.waipu.tv/api/channels/" + channelId + "/programs?startTime=" + start_time + \
              "&stopTime=" + end_time
        return requests.get(url, headers=self.prepare_headers()).json()

    def get_url(self, url):
        self.get_token()
        return requests.get(url, headers=self.prepare_headers()).json()

    def play_channel(self, channel_id):
        self.get_token()
        req_data = '{"stream": {"station": "' + str(
            channel_id) + '", "protocol": "dash", "requestMuxInstrumentation": false}}'
        xbmc.log("req_data: " + str(req_data), level=xbmc.LOGDEBUG)
        headers = self.prepare_headers({"Content-Type": "application/vnd.streamurlprovider.stream-url-request-v1+json"})
        return requests.post("https://stream-url-provider.waipu.tv/api/stream-url", data=req_data,
                             headers=headers).json()

    def play_recording(self, id):
        self.get_token()
        url = "https://recording.waipu.tv/api/recordings/" + str(id)
        return requests.get(url, data={'network': 'wlan'}, headers=self.prepare_headers()).json()

    def open_eu_network(self):
        self.get_token()
        url = "https://eunet.waipu.tv/api/open-eu-network"
        return requests.post(url, headers=self.prepare_headers()).status_code

    def deleteRecording(self, recordId):
        self.get_token()
        url = "https://recording.waipu.tv/api/recordings"

        payload = {'ids': [recordId]}
        headers = self.prepare_headers({'content-type' : 'application/vnd.waipu.pvr-recording-ids-v2+json', 'Accept': 'application/vnd.waipu.recordings-v2+json'})

        r = requests.delete(url, data=json.dumps(payload), headers=headers)
        return r.status_code
