"""
Test the full HTTP to SciToken serialize and deserialize
"""

import os
import sys
import unittest
import threading
import base64

# Allow unittests to be run from within the project base.
if os.path.exists("src"):
    sys.path.append("src")
if os.path.exists("../src"):
    sys.path.append("../src")

import scitokens

import cryptography.utils
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.backends import default_backend

try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# For use in the HTTP Serve test class
#test_kid = ""
TEST_N = 0
TEST_E = 0

def bytes_from_long(data):
    """
    Create a base64 encoded string for an integer
    """
    return base64.urlsafe_b64encode(cryptography.utils.int_to_bytes(data)).decode('ascii')

class OauthRequestHandler(BaseHTTPRequestHandler):
    """
    Request handler for the HTTP requests to authenticate deserialization of a SciToken
    """
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/json')
        self.end_headers()

    def do_GET(self): # pylint: disable=invalid-name
        """
        Receive the GET command for the oauth certs
        """
        global TEST_N
        global TEST_E
        self._set_headers()
        to_write = ""
        if self.path == "/.well-known/openid-configuration":
            to_write = json.dumps({"jwks_uri": "http://localhost:8080/oauth2/certs"})
        elif self.path == "/oauth2/certs":
            key_info = {}
            #key_info['kid'] = test_kid
            key_info['n'] = bytes_from_long(TEST_N)
            key_info['e'] = bytes_from_long(TEST_E)
            key_info['kty'] = "RSA"
            key_info['alg'] = "RS256"
            to_write = json.dumps({'keys': [key_info]})
        self.wfile.write(to_write.encode())



class TestDeserialization(unittest.TestCase):
    """
    Test the deserialization of a SciToken
    """

    def setUp(self):
        # Start a web server to act as the "issuer"
        server_address = ('', 8080)
        httpd = HTTPServer(server_address, OauthRequestHandler)
        self.thread = threading.Thread(target=httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        del self.thread

    def test_deserialization(self):
        """
        Perform the deserialization test
        """
        global TEST_N
        global TEST_E
        private_key = generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        token = scitokens.SciToken(key=private_key)
        token.update_claims({"test": "true"})
        serialized_token = token.serialize(issuer="http://localhost:8080/")

        public_numbers = private_key.public_key().public_numbers()
        TEST_E = public_numbers.e
        TEST_N = public_numbers.n

        self.assertEqual(len(serialized_token.decode('utf8').split(".")), 3)

        scitoken = scitokens.SciToken.deserialize(serialized_token, insecure=True)

        self.assertIsInstance(scitoken, scitokens.SciToken)



if __name__ == '__main__':
    unittest.main()
