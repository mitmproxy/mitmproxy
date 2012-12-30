import binascii
import contrib.md5crypt as md5crypt

class NullProxyAuth():
    """ No proxy auth at all (returns empty challange headers) """
    def __init__(self, password_manager=None):
        self.password_manager = password_manager
        self.username = ""

    def authenticate(self, auth_value):
        """ Tests that the specified user is allowed to use the proxy (stub) """
        return True

    def auth_challenge_headers(self):
        """ Returns a dictionary containing the headers require to challenge the user """
        return {}

    def get_username(self):
        return self.username


class BasicProxyAuth(NullProxyAuth):

    def __init__(self, password_manager, realm="mitmproxy"):
        NullProxyAuth.__init__(self, password_manager)
        self.realm = "mitmproxy"

    def authenticate(self, auth_value):
        if (not auth_value) or (not auth_value[0]):
            print "ROULI: no auth specified"
            return False;
        try:
            scheme, username, password = self.parse_authorization_header(auth_value[0])
        except:
            print "ROULI: Malformed Proxy-Authorization header"
            return False
        if scheme.lower()!='basic':
            print "ROULI: Unexpected Authorization scheme"
            return False
        if not self.password_manager.test(username, password):
            print "ROULI: authorization failed!"
            return False
        self.username = username
        return True

    def auth_challenge_headers(self):
        return {'Proxy-Authenticate':'Basic realm="%s"'%self.realm}

    def parse_authorization_header(self, auth_value):
        print "ROULI: ", auth_value
        words = auth_value.split()
        print "ROULI basic auth: ", words
        scheme = words[0]
        user = binascii.a2b_base64(words[1])
        print "ROULI basic auth user: ", user
        username, password = user.split(':')
        return scheme, username, password

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
    """ Read usernames and passwords from a file created by Apache htpasswd"""

    def __init__(self, filehandle):
        PasswordManager.__init__(self)
        entries = (line.strip().split(':') for line in filehandle)
        valid_entries = (entry for entry in entries if len(entry)==2)
        self.usernames = {username:token for username,token in valid_entries}


    def test(self, username, password_token):
        if username not in self.usernames:
            print "ROULI: username not in db"
            return False
        full_token = self.usernames[username]
        dummy, magic, salt, hashed_password = full_token.split('$')
        expected = md5crypt.md5crypt(password_token, salt, '$'+magic+'$')
        print "ROULI: password", binascii.hexlify(expected), binascii.hexlify(full_token), expected==full_token
        return expected==full_token

class SingleUserPasswordManager(PasswordManager):

    def __init__(self, username, password):
        PasswordManager.__init__(self)
        self.username = username
        self.password = password

    def test(self, username, password_token):
        return self.username==username and self.password==password_token
