import urllib.parse
import http.cookies

import eupheme.response as response
import eupheme.mime as mime
import eupheme.cookies as cookies


class Request:
    """A request issued by a client."""

    def __init__(self, environ, start_response):
        """
        Takes a parameter dictionary 'environ' and a callable 'start_response'
        as specified by PEP3333 and initializes values of interest to us,
        parsing them where necessary.
        """

        self.start_response = start_response
        self.environ = environ

        # Presence of these keys is guaranteed by PEP3333
        self.method = environ['REQUEST_METHOD']
        self.body = environ['wsgi.input']
        self.cookies = cookies.CookieManager.load(environ['HTTP_COOKIE'], ro=True)

        # These keys may or may not be present, or empty if they are.
        self.content_type = environ.get('CONTENT_TYPE', None)
        self.content_length = environ.get('CONTENT_LENGTH', None)
        if self.content_length:
            try:
                self.content_length = int(self.content_length)
            except ValueError:
                # Content-Length header is present but not numeric, violating
                # the format in RFC2616 section 14.13.
                raise response.HttpBadRequestException()

        if not self.content_length:
            self.content_length = None

        # Iterate through the content types accepted by the client
        if 'HTTP_ACCEPT' in environ:
            self.accept = set()
            for accept in environ['HTTP_ACCEPT'].split(','):
                try:
                    self.accept.add(mime.MimeType.parse(accept.strip()))
                except ValueError:
                    raise response.HttpBadRequestException()
        else:
            self.accept = None

        # Iterate through the character sets requested by the client.
        if 'HTTP_ACCEPT_CHARSET' in environ:
            self.accept_charset = set()
            for charset_string in environ['HTTP_ACCEPT_CHARSET'].split(','):
                try:
                    self.accept_charset.add(mime.CharacterSet.parse(
                        charset_string.strip()
                    ))
                except LookupError:
                    # We cannot find the character set requested, carry on.
                    continue
                except ValueError:
                    # The character set was malformed, drop everything.
                    raise response.HttpBadRequestException()
        else:
            # Signals that the user did not request any character set in
            # particular. Note how this is different from not being able to
            # find any of the requested sets; in this case, we can choose.
            self.accept_charset = None

        self.path, self.query = self.parse_path(environ.get('PATH_INFO', ''))

    def parse_path(self, path):
        """
        Parses the http path in 'path'. Returns a tuple of the path component
        and the parsed query string as a dictionary, in that order.
        """

        parsed = urllib.parse.urlparse(path)
        return parsed.path, urllib.parse.parse_qs(parsed.query)

    def read_entity(self):
        """Reads the entity from the request and returns it."""

        # TODO: This is not actually how an entity is read. Refer to RFC2616
        # section 4.4 for details on how to implement this properly.
        if self.content_length is not None:
            return self.body.read(self.content_length)
        else:
            return self.body.read()
