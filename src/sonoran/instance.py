from __future__ import print_function

from .constants import productEnums
from .managers.cad import CADManager
from .managers.cms import CMSManager
from .managers.radio import RadioManager


class Instance(object):
    def __init__(self, options=None, **kwargs):
        merged = dict(options or {})
        merged.update(kwargs)

        self.cadCommunityId = None
        self.cadApiKey = None
        self.cadApiUrl = "https://api.sonorancad.com"
        self.cadDefaultServerId = 1
        self.isCADSuccessful = False

        self.cmsCommunityId = None
        self.cmsApiKey = None
        self.cmsApiUrl = "https://api.sonorancms.com"
        self.cmsDefaultServerId = 1
        self.isCMSSuccessful = False

        self.radioCommunityId = None
        self.radioApiKey = None
        self.radioApiUrl = "https://api.sonoranradio.com"
        self.radioDefaultServerId = 1
        self.isRadioSuccessful = False

        self.debug = bool(merged.get("debug", False))
        self.apiHeaders = dict(merged.get("apiHeaders") or {})
        self.timeout = float(merged.get("timeout", 30))

        self.cad = None
        self.cms = None
        self.radio = None

        if "apiKey" in merged and "communityId" in merged:
            product = merged.get("product")
            if product is None:
                raise ValueError("No product enum given when instancing.")

            if product == productEnums.CAD:
                self.cadCommunityId = merged["communityId"]
                self.cadApiKey = merged["apiKey"]
                if merged.get("serverId") is not None:
                    self.cadDefaultServerId = int(merged["serverId"])
                if isinstance(merged.get("cadApiUrl"), str):
                    self.cadApiUrl = merged["cadApiUrl"]
            elif product == productEnums.RADIO:
                self.radioCommunityId = merged["communityId"]
                self.radioApiKey = merged["apiKey"]
                if merged.get("serverId") is not None:
                    self.radioDefaultServerId = int(merged["serverId"])
                if isinstance(merged.get("radioApiUrl"), str):
                    self.radioApiUrl = merged["radioApiUrl"]
            else:
                raise ValueError("Only productEnums.CAD and productEnums.RADIO are currently supported in Sonoran.py.")
        else:
            self.cadCommunityId = merged.get("cadCommunityId")
            self.cadApiKey = merged.get("cadApiKey")
            self.cmsCommunityId = merged.get("cmsCommunityId")
            self.cmsApiKey = merged.get("cmsApiKey")
            self.radioCommunityId = merged.get("radioCommunityId")
            self.radioApiKey = merged.get("radioApiKey")
            if merged.get("radioDefaultServerId") is not None:
                self.radioDefaultServerId = int(merged["radioDefaultServerId"])
            if isinstance(merged.get("radioApiUrl"), str):
                self.radioApiUrl = merged["radioApiUrl"]

            if merged.get("cadDefaultServerId") is not None:
                self.cadDefaultServerId = int(merged["cadDefaultServerId"])
            if isinstance(merged.get("cadApiUrl"), str):
                self.cadApiUrl = merged["cadApiUrl"]

        self._initialize()

    def _initialize(self):
        if self.cadCommunityId and self.cadApiKey and self.cadApiUrl:
            self.cad = CADManager(self)
            self.isCADSuccessful = True
        if self.cmsCommunityId and self.cmsApiKey and self.cmsApiUrl:
            self.cms = CMSManager(self)
            self.isCMSSuccessful = True
        if self.radioCommunityId and self.radioApiKey and self.radioApiUrl:
            self.radio = RadioManager(self)
            self.isRadioSuccessful = True

    def _debugLog(self, message):
        if self.debug:
            print("[Sonoran.py] {0}".format(message))
