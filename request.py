import urllib.parse
import response


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

        # TODO: Not the exact format we can expect on this header.
        self.accept = environ.get('HTTP_ACCEPT', None)
        if self.accept is not None:
            self.accept = self.accept.split(',')

        # TODO: Like the accept header, the format for this may differ.
        self.accept_charset = environ.get('HTTP_ACCEPT_CHARSET', None)
        if self.accept_charset is not None:
            self.accept_charset = environ['HTTP_ACCEPT_CHARSET'].split(',')

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
