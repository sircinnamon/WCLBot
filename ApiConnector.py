# Connector for the WCL API v2
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from datetime import datetime, timedelta

class ApiConnector(object):
	def __init__(self, clientid, clientsecret, logging):
		# Init fields
		self.client_id=clientid
		self.client_secret=clientsecret
		self.baseURL = "https://www.warcraftlogs.com:443/api/v2/client"

		self.oauth_auth_uri="https://www.warcraftlogs.com/oauth/authorize"
		self.oauth_token_uri="https://www.warcraftlogs.com/oauth/token"
		self.oauth_session=None
		self.current_oauth_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5MWY5ZGVmNC03ODE2LTQ0YjktODI4Yi01ZDY2NTE3ZDg4NjciLCJqdGkiOiIxYzU2ZjI1MjgzMTI0OTc4ZmNjYTZhMjg3MmYzZTk3NWU0MGFmMzZkYmMyZWExNTFhNTNkZGJlYmZhY2Q3NzJlNTlkZjY1MTQ5MjE3MTkzYyIsImlhdCI6MTYwODIyOTM2MywibmJmIjoxNjA4MjI5MzYzLCJleHAiOjE2MTA4MjEzNjMsInN1YiI6IjQ4MjQ0NiIsInNjb3BlcyI6WyJ2aWV3LXByaXZhdGUtcmVwb3J0cyJdfQ.Pv0cfHGnun0-MFAA9nMZdrWK1dV46lyBm74uOhQjPEDoFIrPdeUX7uljxNweKn65G-mIwevyM_O9YnZBbjIosNVNaRmjudF2MKmoKn3OmCp06EemEI--skkuCoo_DGRvVAVXaU7kOmv7xppY0HQPx15AwfPdrv2ILYrfYW30uFCfGgIDFb6IUrnnuP_8MUSCUcflInX2fyBi-NFJxWpHi4UoDG52q1DE3XWxWSwN2aDWSXn3Gs7dcMUdNJuWMFjRAUvtJgy8QP4FCzFn9sFxmlYyEKKNhKga7urxO6FNvnInrOtNYhUOTwq5UwID-bYyeS5UF5ibY-VfSnbbovLM4xOS03pEGma23_KONWOcjhvJDYFb1b1Ss6psCDiuCTjt7tEhS2JfFT_qsqF7yYaOseVDw7MDqObAiscSsH8mVTilOHiusGpQttGPkU4RsCwwoI5K40pdpWtHI3e2bPg22-HV-zMZkwwb4V4MUOPArIcyINk1soQPKGP5NO8wZiFbpvJPDpO0dF5OVvk6loKVL-mVfb4qoxyuep6UsrFP7wc9Esdihy6ztTzqCnIkDux2n3Tzd-fwQ_h4gu3v_4l_b_zqv-daM_FbSrKTsSxonw7SG3uesxqam4DwQHv1MZa1ZjYL02O08ad0QHv5nWZ847X6StlxB_GnyX9-2p2ePuM"
		self.current_oauth_token_expiry=datetime.now() + timedelta(seconds=9999999999)
		self.logging = logging
		# Create session

		# self.create_oauth_session()
		self.logging.info("API Connector initialized.")

	def create_oauth_session(self):
		auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
		data = {"grant_type":"client_credentials"}
		response = requests.post(self.oauth_token_uri, data=data, auth=(self.client_id, self.client_secret))
		# print(response.status_code)
		resp = response.json()
		# print(resp)
		# print(response.headers)
		self.current_oauth_token = resp["access_token"]
		self.current_oauth_token_expiry	= (datetime.now() + timedelta(seconds=resp["expires_in"]))

	def renew_token_if_needed(self):
		# Renew the token if it's near expiration
		if(self.current_oauth_token	== None): self.create_oauth_session()
		elif(self.current_oauth_token_expiry== None): self.create_oauth_session()
		elif((self.current_oauth_token_expiry - datetime.now()).total_seconds() < 86400):
			# Less than 1 day left, renew
			self.create_oauth_session()
		else: return

	def generic_request(self, query):
		self.renew_token_if_needed()
		url = self.baseURL
		headers = {
			"authorization":"Bearer {}".format(self.current_oauth_token),
			"accept":"application/json"
		}
		response = requests.get(url, json={'query': query}, headers=headers)
		# print(response.url + " " + str(response.status_code))
		response.raise_for_status()
		return response.json()