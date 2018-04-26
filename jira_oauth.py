import config
import base64
from urllib.parse import parse_qsl
from tlslite.utils import keyfactory
import oauth2 as oauth

class SignatureMethod_RSA_SHA1(oauth.SignatureMethod):
    name = 'RSA-SHA1'

    def signing_base(self, request, consumer, token):
        if not hasattr(request, 'normalized_url') or request.normalized_url is None:
            raise ValueError("Base URL for request is not set.")

        sig = (
            oauth.escape(request.method),
            oauth.escape(request.normalized_url),
            oauth.escape(request.get_normalized_parameters()),
        )

        key = '%s&' % oauth.escape(consumer.secret)
        if token:
            key += oauth.escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        privatekey = keyfactory.parsePrivateKey(config.JIRA_OAUTH_PEM)
        signature = privatekey.hashAndSign(raw.encode('utf-8'))

        return base64.b64encode(signature)



class JiraOauth:
    def __init__(self):
        consumer_key = config.JIRA_OAUTH_KEY
        consumer_secret = 'dont_care'

        base_url = config.JIRA_BASE_URL
        self.request_token_url = '{}/plugins/servlet/oauth/request-token'.format(base_url)
        self.access_token_url = '{}/plugins/servlet/oauth/access-token'.format(base_url)
        self.authorize_url = '{}/plugins/servlet/oauth/authorize'.format(base_url)

        self.consumer = oauth.Consumer(consumer_key, consumer_secret)

    def request_token(self):
        client = oauth.Client(self.consumer)
        client.set_signature_method(SignatureMethod_RSA_SHA1())
        resp, content = client.request(self.request_token_url, "POST")
        if resp['status'] != '200':
            raise Exception("Invalid response %s: %s" % (resp['status'], content))

        self.request_token = dict(parse_qsl(content))
        state = {
            'token': self.request_token[b'oauth_token'],
            'token_secret': self.request_token[b'oauth_token_secret']
        }
        return "{}?oauth_token={}".format(
            self.authorize_url, self.request_token[b'oauth_token'].decode('utf-8')
        ), state

    def accepted(self, state):
        token = oauth.Token(state['token'], state['token_secret'])
        client = oauth.Client(self.consumer, token)
        client.set_signature_method(SignatureMethod_RSA_SHA1())

        resp, content = client.request(self.access_token_url, "POST")
        access_token = dict(parse_qsl(content))

        return access_token[b'oauth_token'].decode('utf-8'), access_token[b'oauth_token_secret'].decode('utf-8')
