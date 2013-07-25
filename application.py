import logbook

import eupheme.faucets as faucets
import eupheme.request as request
import eupheme.response as response
import eupheme.routing as routing


class Application:
    """A Eupheme web application.

    Represents a running representation. It is responsible for accepting
    requests and dispatching them to the appropriate endpoint. It also performs
    content negotiation based on request parameters.

    An instance of this class is a valid WSGI callable as specified in PEP3333.
    """

    # TODO: Make these configurable in a nice way.
    charsets = {'utf-8'}
    methods = {'GET', 'POST', 'PUT'}

    DEFAULT_CHARSET = 'utf-8'
    DEFAULT_MIMETYPE = 'text/html'

    def __init__(self):
        """
        Instantiates a new application, with empty routing and faucet tables.
        """

        self.routes = routing.RouteManager()
        self.faucets = faucets.FaucetManager()
        self.logger = logbook.Logger('Application')

    def negotiate_accept(self, accepted, supported):
        """
        Attempts to find the option of the highest preference in the 'accepted'
        iterable among those in the 'supported' iterable and returns it.
        Returns None when none of the accepted options is supported.
        """

        # TODO: This is not conformant to RFC2616. We should read the
        # quality parameter and evaluate options in that order.
        for accept in accepted:
            if accept in supported:
                return accept

    def negotiate(self, req, handler):
        """
        Negotiates the response options based on the specifications of the
        request found in 'req'. The request is assumed to be routed to
        'handler'. Returns a tuple containing the associated endpoint, the
        negotiated character set and response content type, in that order.
        May throw an HttpException if negotiation fails at any point.
        """

        if req.method not in self.methods:
            # Method is not known by the server -- RFC2616 section 5.1.1.
            raise response.HttpNotImplementedException()

        if req.method not in handler.allowed_methods:
            # Method not allowed for this resource -- RFC2616 section 5.1.1.
            raise response.HttpMethodNotAllowedException(self.allowed_methods)

        if req.accept_charset is None:
            # if the Accept-Charset header is not present, any character set
            # is acceptable in the response -- RFC2616 section 14.2.
            charset = self.DEFAULT_CHARSET
        else:
            charset = self.negotiate_accept(req.accept_charset, self.charsets)

            if charset is None:
                # If we support none of the character sets requested by the
                # client, we reject the request -- RFC2616 section 14.2.
                raise response.HttpNotAcceptableException()

        try:
            endpoint = getattr(handler, req.method.lower())

            if req.accept is None or \
               (len(req.accept) == 1 and req.accept[0] == '*/*'):
                # If the Accept header is absent, then the client is assumed to
                # accept any content type -- RFC2616 section 14.1.
                # An Accept header containing */* indicates that the
                # client accepts any content type as response as well.
                mimetype = self.DEFAULT_MIMETYPE
            else:
                mimetype = self.negotiate_accept(req.accept, endpoint.produces)
                if mimetype is None:
                    # If we cannot generate any of the content types requested,
                    # we should reject the request -- RFC2616 section 14.1.
                    raise response.HttpNotAcceptableException()

            if req.content_length is not None and \
               req.content_type is not None and \
               req.content_type not in endpoint.consumes:
                # We cannot parse the content type -- RFC2616 section 10.4.16.
                raise response.HttpUnsupportedMediaTypeException()

        except AttributeError:
            # Endpoint or produces attribute is missing
            raise response.HttpInternalServerErrorException()

        return endpoint, mimetype, charset

    def __call__(self, environ, start_response):
        """
        Handles an incoming WSGI request; c.f. PEP3333 for parameter details.
        """

        try:
            # Parse the incoming request to a more convenient object.
            req = request.Request(environ, start_response)

            resource, args = self.routes.match(req.path)
            endpoint, mimetype, charset = self.negotiate(req, resource)

            # If there is an entity included in this request, load it and run
            # it through the appropriate faucet for this endpoint. The endpoint
            # supports this content type, since content negotiation succeeded.
            if req.content_length is not None:
                entity = req.read_entity()
                data = self.faucets.process_incoming(req.content_type, entity)
            else:
                data = None

            # TODO: Not all HTTP verbs conventionally expect data.
            # How do we encapsulate this nicely for resource endpoints?
            result = endpoint(data, *args, **req.query)

            # Run the produced data through a faucet for the outgoing mimetype.
            data = self.faucets.process_outgoing(mimetype, result)

            # We made it! Spit out the actual response.
            resp = response.Response(mimetype=mimetype, charset=charset)
            resp.serve(start_response)
            yield data.encode(charset)

        except response.HttpException as e:
            # An error occured which we can report to the user.
            e.as_response().serve(start_response)
