import decimal
import nose

import eupheme.mime as mime


def test_mimetype_type_wildcard():
    """Type wildcard mime types can be parsed."""

    parsed = mime.MimeType.parse('*/*')
    assert parsed.type == '*' and parsed.subtype == '*'


def test_mimetype_subtype_wildcard():
    """Subtype wildcard mime types can be parsed."""

    parsed = mime.MimeType.parse('text/*')
    assert parsed.type == 'text' and parsed.subtype == '*'


@nose.tools.raises(ValueError)
def test_mimetype_invalid_wildcard():
    """A subtype wildcard in a mime type requires a type wildcard."""

    mime.MimeType.parse('*/test')


def test_mimetype_extended_type():
    """Extended mime types (prepended with 'x-') are allowed."""

    parsed = mime.MimeType.parse('x-test/test')
    assert parsed.type == 'x-test' and parsed.subtype == 'test'


@nose.tools.raises(ValueError)
def test_mimetype_fail_unknown_type():
    """Unknown mime types are rejected."""

    mime.MimeType.parse('test/*')


@nose.tools.raises(ValueError)
def test_mimetype_fail_invalid_type():
    """Non-token mime types are rejected."""

    mime.MimeType.parse('a>b/c')


@nose.tools.raises(ValueError)
def test_mimetype_fail_invalid_subtype():
    """Non-token mime subtypes are rejected."""

    mime.MimeType.parse('a/b[c')


def test_mimetype_quality_property():
    """The mime quality parameter is parsed and exposed as a property."""

    parsed = mime.MimeType.parse('text/plain; q=0.5')
    assert parsed.type == 'text' and parsed.subtype == 'plain'
    assert isinstance(parsed.quality, decimal.Decimal)
    assert parsed.quality == decimal.Decimal('0.5')


def test_mimetype_encode():
    """A mime type can be encoded as a string again."""

    mimetype = mime.MimeType('text', 'plain', level=1, foo='bar')
    assert isinstance(mimetype.parameters['level'], str)

    # Python dictionaries do not guarantee order, check for alternatives.
    assert (str(mimetype) == 'text/plain; foo=bar; level=1' or
            str(mimetype) == 'text/plain; level=1; foo=bar')
