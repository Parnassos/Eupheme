import urllib.parse
import jinja2
import json


def produces(*mimetypes):
    """Decorator that sets content types produced by an endpoint."""

    def wrapper(func):
        func.produces = set(mimetypes)
        return func
    return wrapper


def consumes(*mimetypes):
    """Decorator that sets acceptable input content types for an endpoint."""

    def wrapper(func):
        func.consumes = set(mimetypes)
        return func
    return wrapper


class FaucetManager:
    """Manages incoming as well as outgoing faucets.

    Keeps track of which faucets are registered for which mime types. Also
    dispatches incoming and outgoing requests to the appropriate faucet.
    """

    def __init__(self):
        """
        Instantiates a faucet manager with an empty mapping for incoming and
        outgoing faucets.
        """

        self.faucets_incoming = {}
        self.faucets_outgoing = {}

    def add(self, mapping, faucet):
        """
        Adds a faucet 'faucet' to the mapping 'mapping' for all its mime types.
        """

        for mimetype in faucet.mimetypes:
            mapping[mimetype] = faucet

    def add_incoming(self, faucet):
        """Adds an incoming faucet 'faucet' to the incoming faucet mapping."""

        self.add(self.faucets_incoming, faucet)

    def add_outgoing(self, faucet):
        """Adds an outgoing faucet 'faucet' to the outgoing faucet mapping."""

        self.add(self.faucets_outgoing, faucet)

    def process_incoming(self, mimetype, data):
        """
        Processes an incoming request by calling the appropriate faucet.
        Returns the data to be consumed as processed by the faucet called.
        """

        return self.faucets_incoming[mimetype].incoming(data)

    def process_outgoing(self, mimetype, data):
        """
        Processes an outgoing response by calling the appropriate faucet.
        Returns the data to be served as processed by the faucet called.
        """

        return self.faucets_outgoing[mimetype].outgoing(data)


class IncomingFaucet:
    """Faucet that processes incoming data from the request body."""

    mimetypes = None

    def incoming(self, method, data):
        raise NotImplementedError


class OutgoingFaucet:
    """Faucet that processes outgoing data in the response body."""

    mimetypes = None

    def outgoing(self, method, result):
        raise NotImplementedError


class FormFaucet(IncomingFaucet):
    """Faucet that processes urlencoded form data."""

    mimetypes = {'application/x-www-form-urlencoded'}

    def incoming(self, data):
        return urllib.parse.parse_qs(data)


class JinjaFaucet(OutgoingFaucet):
    """
    Faucet that processes outgoing data by calling the jinja2 template engine.
    """

    mimetypes = {'text/html'}

    def __init__(self, template_location):
        self.environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_location),
        )

    def outgoing(self, data):
        # TODO: Figure out how to locate the template.
        template = self.environment.get_template('default.html')
        return template.render(data)


class JsonFaucet(OutgoingFaucet):
    """
    Faucet that processes outgoing data by encoding it in JSON.
    """

    mimetypes = {'application/json'}

    def outgoing(self, data):
        # TODO: Allow serialization of objects.
        # TODO: Mechanism to selectively exclude items from the output.

        return json.dumps(data)
