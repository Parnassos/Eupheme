"""Module containing classes that pertain to forming an HTTP response."""
import eupheme.cookies


STATUS_OK = '200 OK'


class HttpException(Exception):
    """Base class for exceptions that may occur while processing a request."""

    status = None

    def __init__(self, headers=None):
        self.headers = headers or {}

    def as_response(self):
        """Returns the exception in the form of a Response object."""

        return Response({}, status=self.status, headers=self.headers)


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
        super().__init__({'Location': location})
        self.location = location


class HttpMovedException(HttpException):
    """ The requested resource can be found elsewhere. """

    status = '302 Found'

    def __init__(self, location):
        super().__init__({'Location': location})
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


class HttpNotImplementedException(HttpException):
    """Unrecognized method requested by the client."""

    status = '501 Not Implemented'


class Response:
    """A response to an HTTP request."""

    def __init__(self, data, status=None, headers=None, mimetype=None):
        """Instantiates a response.

        The 'status' argument is the HTTP response status. It defaults to the
        'OK' response. The 'headers' argument can be a dictionary containing a
        key-value mapping of headers. Its default value is an empty dictionary.
        The 'mimetype' and 'charset' arguments are the response content-type
        and character set respectively.
        """

        self.status = status or STATUS_OK
        self.data = data

        # The headers has to be a list since there can be several Set-Cookie
        # headers for example.
        self.headers = headers or {}
        self.mimetype = mimetype
        self.cookies = eupheme.cookies.CookieManager()

    def serve(self, start_response):
        """
        Serves a response to the WSGI callable 'start_response'. If the
        'mimetype' and 'charset' attributes are specified, an appropriate
        Content-Type header is included in the response.
        """

        if self.mimetype is not None:
            self.headers['Content-Type'] = str(self.mimetype)

        headers = list(self.headers.items())
        for key in self.cookies:
            cookie = self.cookies.cookies[key]
            cookiestr = cookie.output().split(':')
            headers.append((cookiestr[0], cookiestr[1].strip()))

        start_response(self.status, headers)

    @staticmethod
    def redirect(url, permanent=False):
        """ Redirect from one page to another.

        Returns a response object containing no data that redirects
        the user to the provided URL. This can be used when redirecting
        on pages where there is a need to set a cookie or otherwise return
        some data that is not possible to do using HttpExceptions.

        """
        resp = Response(
            {},
            status=HttpMovedPermanentlyException.status if permanent
            else HttpMovedException.status
        )
        resp.headers['Location'] = url

        return resp
