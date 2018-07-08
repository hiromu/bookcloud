# coding: utf-8
import urllib2
import hashlib, hmac
import base64
import time

class Amazon:
    def __init__(self, access_key, secret_access_key, associate_tag=None):
        self.amazonurl = "http://webservices.amazon.co.jp/onca/xml"
        self.proxy_host = None
        self.proxy_port = None
        self.access_key = access_key
        self.secret_access_key = secret_access_key
        self.associate_tag = associate_tag
        self.version = "2009-10-01"
        self.url = None
    
    def setProxy(self, host, port=8080):
        self.proxy_host = host
        self.proxy_port = port
    
    def setVersion(self, version):
        self.version = version
    
    def itemLookup(self, item_id, **options):
        params = options
        params["Operation"] = "ItemLookup"
        params["ItemId"] = item_id
        return self.sendRequest(params)
    
    def itemSearch(self, search_index, **options):
        params = options
        params["Operation"] = "ItemSearch"
        params["SearchIndex"] = search_index
        return self.sendRequest(params)

    def buildURL(self, params):
        params["Service"] = "AWSECommerceService"
        params["AWSAccessKeyId"] = self.access_key
        if self.associate_tag is not None:
            params["AssociateTag"] = self.associate_tag
        params["Timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sorted_params = sorted(params.items())
        
        request = []
        for p in sorted_params:
            pair = "%s=%s" % (p[0], urllib2.quote(p[1]))
            request.append(pair)
        
        msg = "GET\nwebservices.amazon.co.jp\n/onca/xml\n%s" % ("&".join(request))
        hmac_digest = hmac.new(self.secret_access_key, msg, hashlib.sha256).digest()
        base64_encoded = base64.b64encode(hmac_digest)
        signature = urllib2.quote(base64_encoded)
        
        request.append("Signature=%s" % signature)
        url = self.amazonurl + "?" + "&".join(request)
        
        return url

    def sendRequest(self, params):
        self.url = self.buildURL(params)
        if self.proxy_host:
            proxy_handler = urllib2.ProxyHandler({"http":"http://%s:%s/" % (self.proxy_host, self.proxy_port)})
            opener = urllib2.build_opener(proxy_handler)
        else:
            opener = urllib2.build_opener()
        return opener.open(self.url).read()
