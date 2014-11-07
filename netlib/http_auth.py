from __future__ import (absolute_import, print_function, division)
from argparse import Action, ArgumentTypeError
from . import http


class NullProxyAuth():
    """
        No proxy auth at all (returns empty challange headers)
    """
    def __init__(self, password_manager):
        self.password_manager = password_manager

    def clean(self, headers):
        """
            Clean up authentication headers, so they're not passed upstream.
        """
        pass

    def authenticate(self, headers):
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
        auth_value = headers.get(self.AUTH_HEADER, [])
        if not auth_value:
            return False
        parts = http.parse_http_basic_auth(auth_value[0])
        if not parts:
            return False
        scheme, username, password = parts
        if scheme.lower()!='basic':
            return False
        if not self.password_manager.test(username, password):
            return False
        self.username = username
        return True

    def auth_challenge_headers(self):
        return {self.CHALLENGE_HEADER:'Basic realm="%s"'%self.realm}


class PassMan():
    def test(self, username, password_token):
        return False


class PassManNonAnon:
    """
        Ensure the user specifies a username, accept any password.
    """
    def test(self, username, password_token):
        if username:
            return True
        return False


class PassManHtpasswd:
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


class PassManSingleUser:
    def __init__(self, username, password):
        self.username, self.password = username, password

    def test(self, username, password_token):
        return self.username==username and self.password==password_token


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

    def getPasswordManager(self, s): # pragma: nocover
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

