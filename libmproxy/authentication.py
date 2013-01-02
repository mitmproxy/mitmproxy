import binascii
import contrib.md5crypt as md5crypt

class NullProxyAuth():
    """
        No proxy auth at all (returns empty challange headers)
    """
    def __init__(self, password_manager):
        self.password_manager = password_manager
        self.username = ""

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
        try:
            scheme, username, password = self.parse_auth_value(auth_value[0])
        except ValueError:
            return False
        if scheme.lower()!='basic':
            return False
        if not self.password_manager.test(username, password):
            return False
        self.username = username
        return True

    def auth_challenge_headers(self):
        return {self.CHALLENGE_HEADER:'Basic realm="%s"'%self.realm}

    def unparse_auth_value(self, scheme, username, password):
        v = binascii.b2a_base64(username + ":" + password)
        return scheme + " " + v

    def parse_auth_value(self, auth_value):
        words = auth_value.split()
        if len(words) != 2:
            raise ValueError("Invalid basic auth credential.")
        scheme = words[0]
        try:
            user = binascii.a2b_base64(words[1])
        except binascii.Error:
            raise ValueError("Invalid basic auth credential: user:password pair not valid base64: %s"%words[1])
        parts = user.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid basic auth credential: decoded user:password pair not valid: %s"%user)
        return scheme, parts[0], parts[1]


class PasswordManager():
    def __init__(self):
        pass

    def test(self, username, password_token):
        return False


class PermissivePasswordManager(PasswordManager):
    def __init__(self):
        PasswordManager.__init__(self)

    def test(self, username, password_token):
        if username:
            return True
        return False


class HtpasswdPasswordManager(PasswordManager):
    """
        Read usernames and passwords from a file created by Apache htpasswd
    """
    def __init__(self, filehandle):
        PasswordManager.__init__(self)
        entries = (line.strip().split(':') for line in filehandle)
        valid_entries = (entry for entry in entries if len(entry)==2)
        self.usernames = {username:token for username,token in valid_entries}

    def test(self, username, password_token):
        if username not in self.usernames:
            return False
        full_token = self.usernames[username]
        dummy, magic, salt, hashed_password = full_token.split('$')
        expected = md5crypt.md5crypt(password_token, salt, '$'+magic+'$')
        return expected==full_token


class SingleUserPasswordManager(PasswordManager):
    def __init__(self, username, password):
        PasswordManager.__init__(self)
        self.username = username
        self.password = password

    def test(self, username, password_token):
        return self.username==username and self.password==password_token
