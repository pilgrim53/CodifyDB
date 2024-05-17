import gnupg
import json
from decouple import config


class PasswordManager():
    def __init__(self):
        passphrase = config('APP_NAME')
        password_file = config('APP_FILE')
        gpg = gnupg.GPG()
        gpg.encoding = 'utf-8'

        with open(password_file, 'rb') as credentials:
            creds = credentials.read()
            self.login_info = json.loads(str(gpg.decrypt(creds, passphrase=passphrase)))

    def get(self, credential: str):
        return self.login_info[credential]
