"""Module containing classes that pertain to forming an HTTP response."""

STATUS_OK = '200 OK'


class HttpException(Exception):
    """Base class for exceptions that may occur while processing a request."""

    status = None

    def __init__(self, headers=None):
        self.headers = headers or {}

    def as_response(self):
        """Returns the exception in the form of a Response object."""

        return Response(status=self.status, headers=self.headers)


class HttpNotFoundException(HttpException):
    """The requested resource could not be found."""

    status = '404 Not Found'

    def __init__(self, path):
        super().__init__()
        self.path = path


class HttpMovedPermanentlyException(HttpException):
    """The requested resource has moved permanently."""

    status = '301 Moved Permanently'

    def __init__(self, location):
        super().__init__()
        self.location = location


class HttpBadRequestException(HttpException):
    """The client has issued an invalid request."""
    status = '400 Bad Request'


class HttpMethodNotAllowedException(HttpException):
    """The method requested is not allowed for the resource."""

    status = '405 Method Not Allowed'

    def __init__(self, allowed):
        super().__init__()
        # An 'Allow' header accompanies this response -- RFC2616 section 14.7.
        self.headers['Allow'] = ', '.join(allowed)


class HttpNotAcceptableException(HttpException):
    """An option requested by the client cannot be produced by the server."""

    status = '406 Not Acceptable'


class HttpUnsupportedMediaTypeException(HttpException):
    """The server cannot process the media type sent."""

    status = '415 Unsupported Media Type'


class HttpInternalServerErrorException(HttpException):
    """An internal error occurred on the server."""

    status = '500 Internal Server Error'


class Response:
    """A response to an HTTP request."""

    def __init__(self, status=None, headers=None, mimetype=None, charset=None):
        """Instantiates a response.

        The 'status' argument is the HTTP response status. It defaults to the
        'OK' response. The 'headers' argument can be a dictionary containing a
        key-value mapping of headers. Its default value is an empty dictionary.
        The 'mimetype' and 'charset' arguments are the response content-type
        and character set respectively.
        """

        self.status = status or STATUS_OK
        self.headers = headers or {}
        self.mimetype = mimetype
        self.charset = charset

    def serve(self, start_response):
        """
        Serves a response to the WSGI callable 'start_response'. If the
        'mimetype' and 'charset' attributes are specified, an appropriate
        Content-Type header is included in the response.
        """

        if self.mimetype is not None and self.charset is not None:
            self.headers['Content-Type'] = '{0}; charset={1}'.format(
                self.mimetype,
                self.charset
            )

        start_response(self.status, list(self.headers.items()))
