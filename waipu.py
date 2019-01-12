from pprint import pprint

import requests
import time

class Waipu:
	def __init__(self, username, password):
		self._auth = None
		self.logged_in = False
		self._channelData = None
		self.__username = username
		self.__password = password

	def fetchToken(self):
		url  = "https://auth.waipu.tv/oauth/token"
		payload = {'username': self.__username, 'password': self.__password, 'grant_type': 'password'}
		headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)', 'Authorization': 'Basic YW5kcm9pZENsaWVudDpzdXBlclNlY3JldA=='}
		self._auth = None
		self.logged_in = False
		r = requests.post(url, data=payload, headers=headers)
		if r.status_code == 200:
			self._auth = r.json()
			self.logged_in = True
			self._auth["expires"] = time.time()+self._auth["expires_in"]
		return r.status_code

	def getToken(self):
		if (self._auth == None or self._auth["expires"] <= time.time()):
			code = self.fetchToken()
			if (code != 200):
				raise Exception("Can't login, Code="+str(code))
		#TODO: renew token
		#print(self._auth)
		return self._auth['access_token']
	
	def getChannels(self):
		self.getToken()
		url  = "https://epg.waipu.tv/api/channels"
		headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)', 'Authorization': 'Bearer '+self._auth['access_token']}
		r = requests.get(url, headers=headers)
		if r.status_code == 200:		
			self._channelData = r.json()
			#pprint (self._channelData)
			channels = {}
			for channel in  self._channelData:
				channel_data = {}
				for link in channel['links']:
					if (link['rel'] == 'liveImage'):
						channel_data['thumbnail'] = link['href']
					if (link['rel'] == 'icon'):
						channel_data['icon'] = link['href']+"?width=1000&height=1000"
				channel_data['displayName'] = channel['displayName']
				channel_data['orderIndex'] = channel['orderIndex']
				channels[channel['id']] = channel_data
			return channels

	def getStatus(self):
		self.getToken()
		url  = "https://status.wpstr.tv/status?nw=wifi"
		headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)'}
		r = requests.get(url, headers=headers)
		#pprint(r.json())
		if r.status_code == 200:		
			pprint(r.json())

	def homeCheck(self, mac="66:09:80:70:c4:75"):
		self.getToken()
		url  = "https://home-check.waipu.tv/api/users/home-networks/"+mac
		headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)', 'Authorization': 'Bearer '+self._auth['access_token']}
		
		r = requests.get(url, headers=headers)
		#pprint(r.json())
		if r.status_code == 200:		
			pprint(r.json())

	def playChannel(self, id):
		if (self._channelData == None):
			self.getChannels()
		self.getStatus()
		#self.homeCheck()
		for channel in  self._channelData:
			if (channel['id'] == id):
				for link in channel['links']:
					if (link['rel'] == 'livePlayout'):
						url =  link['href']
						payload = {'network': 'wlan'}
						headers = {'User-Agent': 'waipu-2.29.2-c0f220b-9446 (Android 8.1.0)', 'Authorization': 'Bearer '+self._auth['access_token']}
						r = requests.get(url, data=payload, headers=headers)
						return r.json()


