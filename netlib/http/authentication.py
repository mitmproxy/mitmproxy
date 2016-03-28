from __future__ import (absolute_import, print_function, division)
from argparse import Action, ArgumentTypeError
import binascii


def parse_http_basic_auth(s):
    words = s.split()
    if len(words) != 2:
        return None
    scheme = words[0]
    try:
        user = binascii.a2b_base64(words[1]).decode("utf8", "replace")
    except binascii.Error:
        return None
    parts = user.split(':')
    if len(parts) != 2:
        return None
    return scheme, parts[0], parts[1]


def assemble_http_basic_auth(scheme, username, password):
    v = binascii.b2a_base64((username + ":" + password).encode("utf8")).decode("ascii")
    return scheme + " " + v


class NullProxyAuth(object):

    """
        No proxy auth at all (returns empty challange headers)
    """

    def __init__(self, password_manager):
        self.password_manager = password_manager

    def clean(self, headers_):
        """
            Clean up authentication headers, so they're not passed upstream.
        """

    def authenticate(self, headers_):
        """
            Tests that the user is allowed to use the proxy
        """
        return True

    def auth_challenge_headers(self):
        """
            Returns a dictionary containing the headers require to challenge the user
        """
        return {}


class BasicProxyAuth(NullProxyAuth):
    CHALLENGE_HEADER = 'Proxy-Authenticate'
    AUTH_HEADER = 'Proxy-Authorization'

    def __init__(self, password_manager, realm):
        NullProxyAuth.__init__(self, password_manager)
        self.realm = realm

    def clean(self, headers):
        del headers[self.AUTH_HEADER]

    def authenticate(self, headers):
        auth_value = headers.get(self.AUTH_HEADER)
        if not auth_value:
            return False
        parts = parse_http_basic_auth(auth_value)
        if not parts:
            return False
        scheme, username, password = parts
        if scheme.lower() != 'basic':
            return False
        if not self.password_manager.test(username, password):
            return False
        self.username = username
        return True

    def auth_challenge_headers(self):
        return {self.CHALLENGE_HEADER: 'Basic realm="%s"' % self.realm}


class PassMan(object):

    def test(self, username_, password_token_):
        return False


class PassManNonAnon(PassMan):

    """
        Ensure the user specifies a username, accept any password.
    """

    def test(self, username, password_token_):
        if username:
            return True
        return False


class PassManHtpasswd(PassMan):

    """
        Read usernames and passwords from an htpasswd file
    """

    def __init__(self, path):
        """
            Raises ValueError if htpasswd file is invalid.
        """
        import passlib.apache
        self.htpasswd = passlib.apache.HtpasswdFile(path)

    def test(self, username, password_token):
        return bool(self.htpasswd.check_password(username, password_token))


class PassManSingleUser(PassMan):

    def __init__(self, username, password):
        self.username, self.password = username, password

    def test(self, username, password_token):
        return self.username == username and self.password == password_token


class AuthAction(Action):

    """
    Helper class to allow seamless integration int argparse. Example usage:
    parser.add_argument(
        "--nonanonymous",
        action=NonanonymousAuthAction, nargs=0,
        help="Allow access to any user long as a credentials are specified."
    )
    """

    def __call__(self, parser, namespace, values, option_string=None):
        passman = self.getPasswordManager(values)
        authenticator = BasicProxyAuth(passman, "mitmproxy")
        setattr(namespace, self.dest, authenticator)

    def getPasswordManager(self, s):  # pragma: no cover
        raise NotImplementedError()


class SingleuserAuthAction(AuthAction):

    def getPasswordManager(self, s):
        if len(s.split(':')) != 2:
            raise ArgumentTypeError(
                "Invalid single-user specification. Please use the format username:password"
            )
        username, password = s.split(':')
        return PassManSingleUser(username, password)


class NonanonymousAuthAction(AuthAction):

    def getPasswordManager(self, s):
        return PassManNonAnon()


class HtpasswdAuthAction(AuthAction):

    def getPasswordManager(self, s):
        return PassManHtpasswd(s)
