import logbook

import eupheme.faucets as faucets
import eupheme.request as request
import eupheme.response as response
import eupheme.routing as routing
import eupheme.negotiation as negotiation
import eupheme.mime as mime
import eupheme.config as config


class Application:
    """A Eupheme web application.

    Represents a running representation. It is responsible for accepting
    requests and dispatching them to the appropriate endpoint. It also performs
    content negotiation based on request parameters.

    An instance of this class is a valid WSGI callable as specified in PEP3333.
    """

    def __init__(self, path=None):
        """
        Instantiates a new application, with empty routing and faucet tables.
        """

        self.routes = routing.RouteManager()
        self.faucets = faucets.FaucetManager()

        conf = config.load(path)

        faucets.FormFaucet.default_charset = \
            conf.default.charset.codec.name

        self.broker = negotiation.Broker(
            charsets=conf.charsets,
            default_charset=conf.default.charset,
            methods=conf.methods,
            default_mimetype=conf.default.mimetype
        )

        self.logger = logbook.Logger('Application')

    def __call__(self, environ, start_response):
        """
        Handles an incoming WSGI request; c.f. PEP3333 for parameter details.
        """

        try:
            # Parse the incoming request to a more convenient object.
            req = request.Request(environ, start_response)

            # Determine the resource that's the object of this request, and
            # any arguments to it.
            resource, args = self.routes.match(req.path)

            # Obtain the endpoint that handles the method for this resource.
            endpoint = self.broker.negotiate_endpoint(req.method, resource)

            # Pick a character set that we will use for the output
            charset = self.broker.negotiate_charset(req.accept_charset)

            # Choose the content type to be used for the output
            mimetype = self.broker.negotiate_output(req, endpoint)

            # Gather the input for this request, if there is any.
            data = self.broker.negotiate_input(req, endpoint)

            # If there is an entity included in this request, run it through
            # the appropriate faucet for this endpoint.
            if data is not None:
                data = self.faucets.process_incoming(
                    req.content_type,
                    faucets.Flow(faucets.Flow.IN, data)
                )

            # Call on the endpoint to do the actual data processing.
            # TODO: Not all HTTP verbs conventionally expect data.
            # How do we encapsulate this nicely for resource endpoints?
            result = endpoint(data, *args, **req.query)

            # Run the produced data through a faucet for the outgoing mimetype.
            output = self.faucets.process_outgoing(
                mimetype,
                faucets.Flow(faucets.Flow.OUT, result, endpoint=endpoint)
            )

            # Synthesize the negotiated mimetype and charset
            mimetype = mime.MimeType(
                mimetype.type,
                mimetype.subtype,
                charset=charset.codec.name
            )

            # We made it! Spit out the actual response.
            resp = response.Response(mimetype=mimetype)
            resp.serve(start_response)
            encoded, length = charset.codec.encode(output)
            yield encoded

        except response.HttpException as e:
            # An error occured which we can report to the user.
            e.as_response().serve(start_response)
