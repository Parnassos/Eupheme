import re
import codecs

import eupheme.negotiation as negotiation

# A token as described in RFC2045 section 5.1. Consists of any ASCII character
# except non-printable ones, spaces as well as ( ) < > @ , ; \ " [ ] ? =
RE_TOKEN = re.compile(r'^[^\x00-\x20\x80-\xff()<>@,;:\\"/\[\]?=]+$')


class MimeParameters:
    # The rough structure for a type parameter; c.f. to RFC2045 section 5.1.
    RE_PARAMETER = re.compile('^(?P<key>\w+)=(?P<value>.*)$', re.DOTALL)

    # A quoted string as specified in RFC822 section 3.3.
    RE_QUOTED_STRING = re.compile(
        r'^"('
        # qtext: any ASCII character excepting <"> and "\".
        # All carriage returns (\r) must be followed by a line feed (\n).
        r'[^\\\"\r\x80-\xff]|' '\r\n|'
        # quoted-pair: any ASCII character prepended with a backslash.
        r'\\[\x00-\x7f]'
        r')*"$'
    )

    def __init__(self, encoded=None, **parameters):
        """
        Creates a MimeParameters instance, parsed from the parameters in
        the 'encoded' argument. Further parameters can be specified as keyword
        arguments.
        """

        # Copy over the keyword arguments
        self.values = {}
        for key, value in parameters.items():
            self[key] = value

        if encoded is None:
            return  # Do not bother parsing if we have no encoded parameters.

        # Parse additional parameters specified in the mimetype.
        for parameter in encoded.split(';'):
            parameter = parameter.strip()
            if not parameter:
                continue  # Skip empty parameters

            match = self.RE_PARAMETER.match(parameter)
            if match is None:
                raise ValueError('Invalid parameter: {0}'.format(parameter))

            key = match.group('key')
            value = match.group('value')

            # Value can either be a token or a quoted string
            if RE_TOKEN.match(value):
                self[key] = value
            elif self.RE_QUOTED_STRING.match(value):
                # We got a quoted string, unquote
                self[key] = re.sub(r'\\(.)', r'\1', value[1:-1])
            else:
                raise ValueError('Invalid parameter value: {0}'.format(value))

    def __str__(self):
        """Encodes the MimeParameters back into a string."""

        encoded = []
        for key, value in self.values.items():
            if not RE_TOKEN.match(value):
                # The token cannot be encoded directly, escape any character
                # that needs quoting in a quoted-string (quotes, backslashes
                # and carriage returns not followed by a newline).
                value = '"{0}"'.format(
                    re.sub(r'("|\\|\r(!?\n))', r'\\\1', value))

            encoded.append('{0}={1}'.format(key, value))
        return '; '.join(encoded)

    def __getitem__(self, key):
        """Returns the value for the parameter 'key', if it exists."""

        return self.values[key]

    def __setitem__(self, key, value):
        """Sets the value for the parameter 'key' to 'value'."""

        self.values[key] = str(value)

    def __contains__(self, key):
        """Returns a boolean indicating the existence of parameter 'key'."""

        return key in self.values

    def __len__(self):
        """
        Returns the number of parameters, excluding the (reserved) quality
        parameter if it exists.
        """

        return len(self.values)-1 if 'q' in self else len(self.values)

    def __le__(self, other):
        """
        Returns a boolean indicating whether all parameters (excluding the
        quality parameter) are contained in the instance 'other'.
        """

        for key, value in self.values.items():
            if key != 'q' and (key not in other or other[key] != self[key]):
                return False
        return True


class MimeType(negotiation.Negotiable):
    # The rough structure for a MIME type; c.f. RFC2045 section 5.1.
    RE_MIMETYPE = re.compile(r'^(?P<type>.+)/'
                             r'(?P<subtype>.+?)'
                             r'(?P<parameters>;.*)?$')

    # Media types as registered with IANA, refer to
    # http://www.iana.org/assignments/media-types
    MEDIA_TYPES = [
        'application',
        'audio',
        'example',
        'image',
        'message',
        'model',
        'multipart',
        'text',
        'video'
    ]

    def __init__(self, type_, subtype, **parameters):
        """
        Instantiates a mimetype with type 'type_' and subtype 'subtype'.
        Additional type parameters can be passed as keyword arguments.
        """

        if not RE_TOKEN.match(type_):
            raise ValueError('Invalid type token: {0}'.format(type_))

        if not RE_TOKEN.match(subtype):
            raise ValueError('Invalid subtype token: {0}'.format(subtype))

        # The media type needs to be a known one or indicated as an extension.
        # There's a sundry of subtypes in the wild, thus we allow any subtype.
        if not self.media_type_valid(type_):
            raise ValueError('Invalid media type: "{0}"'.format(type_))

        self.type = type_
        self.subtype = subtype
        self.parameters = MimeParameters(**parameters)

        # Types such as '*/html' are not allowed.
        if self.type == '*' and self.subtype != '*':
            raise ValueError('Type wildcard without subtype wildcard')

    @classmethod
    def parse(cls, encoded):
        """Parses a string into a MimeType instance."""

        match = cls.RE_MIMETYPE.match(encoded)
        if match is None:
            raise ValueError('Could not parse mimetype: {0}'
                             .format(encoded))

        mimetype = cls(match.group('type'), match.group('subtype'))
        mimetype.parameters = MimeParameters(match.group('parameters'))
        return mimetype

    def media_type_valid(self, value):
        """
        Checks whether a media type is either one of the types registered with
        IANA, or an extension field prefixed with an 'x-'.
        """

        return (value == '*' or
                value in self.MEDIA_TYPES or
                value.lower().startswith("x-"))

    def __str__(self):
        """Returns a string representation of the mime type."""

        if not len(self.parameters):
            return "{0}/{1}".format(self.type, self.subtype)

        return "{0}/{1}; {2}".format(self.type,
                                     self.subtype,
                                     str(self.parameters))

    def __contains__(self, other):
        """
        Returns a boolean indicating whether the mimetype 'other' is satisfied
        by the present mimetype.
        """

        # The */* media range will satisfy all content types.
        if self.type == '*':
            return True

        # If the type is explicitly given, they must match.
        if self.type != other.type:
            return False

        # The TYPE/* range will satisfy all subtypes of TYPE.
        if self.subtype == '*':
            return True

        # If the subtype is explicitly given, they must match.
        if self.subtype != other.subtype:
            return False

        # If type and subtype match, the parameters of the contained type
        # should be a superset of the containing type. This is not mentioned
        # explicitly in RFC2616, but it appears to be true in the example of
        # section 14.1.
        return self.parameters <= other.parameters

    def __gt__(self, other):
        """
        Returns a boolean indicating whether the mimetype 'other' is stricter
        than the present mimetype.
        """

        # If the other type has wildcards and we don't, we are stricter.
        if other.type == '*' and self.type != '*':
            return True
        if other.subtype == '*' and self.subtype != '*':
            return True

        # If we have more parameters, we are stricter too. Further ordering in
        # case of the same number of parameters depends on the subtypes being
        # ordered and is therefore outside the scope of this implementation.
        return len(self.parameters) > len(other.parameters)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class CharacterSet(negotiation.Negotiable):
    """Represents a character set."""

    # Rough format as in RFC2616 section 14.2.
    RE_CHARSET = re.compile(r'^(?P<name>.+?)(?P<params>;.*)?$')

    def __init__(self, name, quality='1'):
        """Instantiates a charset with name 'name' and quality 'quality'."""

        self.codec = codecs.lookup(name)
        self.parameters = MimeParameters(q=quality)

    @classmethod
    def parse(cls, encoded):
        """
        Parses an encoded character set and its parameters and returns the
        result. The expected format is as in RFC2616 section 14.2.
        """

        match = cls.RE_CHARSET.match(encoded)
        if match is None:
            raise ValueError('Invalid character set: {0}'.format(encoded))

        # The charset set name must be a valid token; c.f. RFC2616 section 3.4
        if RE_TOKEN.match(match.group('name')) is None:
            raise ValueError('Invalid token: {0}'.format(encoded))

        charset = cls(match.group('name'))
        if match.group('params') is not None:
            charset.parameters = MimeParameters(match.group('params'))

        return charset

    def __contains__(self, other):
        """Checks whether this character set is satisfied by 'other'."""

        # Compare codecs rather than their names to account for aliases. For
        # example, iso-ir-6 is an alias of ASCII.
        return self.codec == other.codec

    def __lt__(self, other):
        """Imposes an alphabetical ordering on canonical codec names."""

        # Since there is no way of telling whether one codec satisfies another,
        # we simply order them alphabetically.
        return self.codec.name < other.codec.name
