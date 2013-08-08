import urllib.parse
import jinja2
import json

import eupheme.mime as mime


def parse_strings(mimetypes):
    """
    Iterates through 'mimetypes' and returns a generator in which every string
    is replaced by its parsed MimeType instance.
    """

    for mimetype in mimetypes:
        if isinstance(mimetype, str):
            yield mime.MimeType.parse(mimetype)
        else:
            yield mimetype


def produces(*mimetypes):
    """Decorator that sets content types produced by an endpoint."""

    def wrapper(func):
        func.produces = set(parse_strings(mimetypes))
        return func
    return wrapper


def consumes(*mimetypes):
    """Decorator that sets acceptable input content types for an endpoint."""

    def wrapper(func):
        func.consumes = set(parse_strings(mimetypes))
        return func
    return wrapper


def template(template):
    """Decorator that associates an endpoint with a template."""

    def wrapper(func):
        func.template = template
        return func

    return wrapper


class Flow:
    """Data class used for data flowing in and out of faucets."""

    IN = 'in'
    OUT = 'out'

    data = None
    direction = None
    endpoint = None

    def __init__(self, direction, data, endpoint=None):
        """Instantiates a new flow object."""

        self.direction = direction
        self.data = data
        self.endpoint = endpoint


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

    def process_incoming(self, mimetype, flow):
        """
        Processes an incoming request by calling the appropriate faucet.
        Returns the data to be consumed as processed by the faucet called.
        """

        return self.faucets_incoming[mimetype].incoming(flow)

    def process_outgoing(self, mimetype, flow):
        """
        Processes an outgoing response by calling the appropriate faucet.
        Returns the data to be served as processed by the faucet called.
        """

        return self.faucets_outgoing[mimetype].outgoing(flow)


class IncomingFaucet:
    """Faucet that processes incoming data from the request body."""

    mimetypes = None

    def incoming(self, flow):
        raise NotImplementedError


class OutgoingFaucet:
    """Faucet that processes outgoing data in the response body."""

    mimetypes = None

    def outgoing(self, flow):
        raise NotImplementedError


class FormFaucet(IncomingFaucet):
    """Faucet that processes urlencoded form data."""

    mimetypes = {
        mime.MimeType('application', 'x-www-form-urlencoded')
    }

    def sniff_charset(self, qs):
        """
        Decodes the query string and looks for an entry with the name
        _charset_. If it finds it, that's the charset the form was sent in,
        otherwise it returns None and lets the caller decide what charset
        to use.
        """

        # For information on why we're doing this see:
        # http://www.w3.org/TR/html5/forms.html#url-encoded-form-data

        # Decode the form data and drop any non-ascii values,then parse it.
        querydata = qs.decode('ascii', 'ignore')
        querystring = urllib.parse.parse_qs(querydata)

        # If _charset_ is found in the query string we return that, otherwise
        # we'll just return None and let the caller decide what to do.
        if '_charset_' in querystring:
            return querystring['_charset_'][0]
        else:
            return None

    def incoming(self, flow):
        # TODO: Configurable default charset
        charset = self.sniff_charset(flow.data) or 'utf-8'
        return urllib.parse.parse_qs(flow.data.decode(charset))


class JinjaFaucet(OutgoingFaucet):
    """
    Faucet that processes outgoing data by calling the jinja2 template engine.
    """

    mimetypes = {
        mime.MimeType('text', 'html')
    }

    def __init__(self, template_location):
        self.environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_location),
        )

    def outgoing(self, flow):
        try:
            template = self.environment.get_template(flow.endpoint.template)
        except AttributeError:
            template = self.environment.get_template('default.html')

        return template.render(flow.data)


class JsonFaucet(OutgoingFaucet):
    """
    Faucet that processes outgoing data by encoding it in JSON.
    """

    mimetypes = {
        mime.MimeType('application', 'json')
    }

    def outgoing(self, flow):
        # TODO: Allow serialization of objects.
        # TODO: Mechanism to selectively exclude items from the output.

        return json.dumps(flow.data)
