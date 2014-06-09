""" Eupheme cookie module.

This module contains code related to cookie handling such as setting and
getting cookies on requests and responses. Types of cookies are normal
plaintext cookies as well as signed cookies that are hard to forge.

Cookie signing code is based on the code used in python-tornado for signing
cookies. See: http://www.tornadoweb.org/en/stable/_modules/tornado/web.html

"""


import hmac
from hashlib import sha224
from http.cookies import SimpleCookie
from time import time
from base64 import b64encode, b64decode


class InvalidOperationException(RuntimeError):

    """ Exception class for CookieManager for invalid operations.

    This class is used for when the user tries to make CookieManager set a
    cookie when the manager is in read-only mode (such as when used in
    request objects). Or when trying to make it sign a cookie without having
    a secret key set.

    """

    pass


class CookieManager:

    """ Class responsible for cookie management.

    The CookieManager class is responsible for handling setting and
    retrieval of cookies for both the Response and Request classes to ensure
    that all code related to cookies are stored in one place.

    This class also has code for using signed cookies, which is based on the
    code used in Tornado for doing cookie signing.

    """

    key = None

    def __init__(self, ro=False):
        """ Create a new cookie manager. """

        self.cookies = SimpleCookie()
        self.key = CookieManager.key
        self.ro = ro

    def __iter__(self):
        return iter(self.cookies)

    @staticmethod
    def load(input, ro=False):
        """ Create a new CookieManager from an environment variable.

        This method uses the contents of an environment variable and passes it
        to the SimpleCookie class for parsing and uses that as the cookies
        stored in the CookieManager.

        Returns a CookieManager object.

        """
        obj = CookieManager(ro=ro)
        obj.cookies = SimpleCookie(input)

        return obj

    def set_cookie(self, name, value, domain=None, expires=None,
                   httponly=False, secure=False):
        """ Add a new cookie to the cookie manager. """
        if self.ro:
            raise InvalidOperationException(
                "This CookieManager instance is in read only mode"
            )

        self.cookies[name] = value

        # Only set attributes that have been requested
        if domain is not None:
            self.cookies[name]["domain"] = domain

        if expires is not None:
            self.cookies[name]["expires"] = expires

        if httponly:
            self.cookies[name]["httponly"] = True

        if secure:
            self.cookies[name]["secure"] = True

    def get_cookie(self, name):
        """ Get the cookie with the specified name.

        Returns a cookie from the SimpleCookie object or None if the there is
        no cookie by that name.

        """

        try:
            return self.cookies[name].value
        except KeyError:
            return None

    def get_signed_cookie(self, name):
        """ Get the signed cooking with the specified name.

        Returns a verified cookie from the SimpleCookie object or None if
        there is no cookie by that name or the signature is invalid.

        """
        result = None
        cookie = self.get_cookie(name)
        if cookie is not None:
            vals = cookie.split('|')

            # Anything else than 3 splits is not a signed cookie we created.
            if len(vals) == 3:
                value = vals[0]
                timestamp = vals[1]

                # Compare the hexdigest of the fetched cookie with one built
                # using the components available in the cookie.
                if hmac.compare_digest(
                        vals[2],
                        signature(
                            self.key, name, value,
                            timestamp, CookieManager.codec
                        ).hexdigest()
                ):
                    result = CookieManager.codec.decode(b64decode(value))[0]

        return result

    def set_signed_cookie(self, name, value, domain=None, expires=None,
                          httponly=False, secure=False):
        """ Set a signed cookie.

        Signed cookies are cookies signed using a secret key. The signed
        components of the cookie are the name, the value (in base64 form)
        and a timestamp. This should be used where it's important that
        cookies are not forged.

        """
        self.set_cookie(
            name,
            signed_value(
                self.key, name,
                value, time(),
                CookieManager.codec
            ),
            domain=domain,
            expires=expires,
            httponly=httponly,
            secure=secure
        )


def signed_value(secret, name, value, timestamp, codec):
    """ Create a string with an encoded value, a timestamp and a signature.

    Signed values are signed using HMAC-SHA-224. Signed values are a
    combination of a the name of the cookie, the value of the cookie, and the
    timestamp.

    Returns a string with a value, a timestamp and a signature to be used
    as a signed cookie.

    """
    value = b64encode(codec.encode(value)[0]).decode('ascii')
    sig = signature(secret, name, value, timestamp, codec)

    # Return the value for use in a cookie.
    return '|'.join([
        value,
        str(int(timestamp)),
        sig.hexdigest()
    ])


def signature(secret, name, value, timestamp, codec):
    """ Create a signature for use as signature in a signed cookie.

    This method takes name, value and a timestamp to generate a signature
    using the secret key to try to make sure that signed cookies
    can't be forged.

    Returns a HMAC object.

    """

    # If there's no secret key then there's nothing to do and
    # something is terribly wrong.
    if secret is None:
        raise InvalidOperationException("No secret key set for cookie signing")

    # Create a nenw hmac and start updating it
    sig = hmac.new(codec.encode(secret)[0], digestmod=sha224)
    ts = str(int(timestamp))

    # Encode the string with delimiters to prevent problems with transfering
    # bits from the base64 encoded payload to the timestamp. See:
    # http://www.tornadoweb.org/en/stable/_modules/tornado/web.html
    # and the function decode_signed_value.
    sigvalue = '|'.join([
        name,
        value,
        ts
    ])

    sig.update(codec.encode(sigvalue)[0])

    return sig
