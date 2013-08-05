import decimal
import nose

import eupheme.mime as mime
import eupheme.negotiation as negotiation

# Character sets and their qualities that we will be testing against.
ascii = mime.CharacterSet('ascii', quality='0.5')
ascii_alias = mime.CharacterSet('iso-ir-6', quality='0.5')
utf8 = mime.CharacterSet('utf-8', quality='1')
utf16 = mime.CharacterSet('utf-16')


def test_charset_alias():
    """An alias for a character set fills the satisfies its counterpart."""

    assert ascii in ascii_alias
    assert ascii_alias in ascii


def test_charset_parse():
    """A character set string and associated quality parse correctly."""

    parsed = mime.CharacterSet.parse('utf-8; q=0.5')
    assert parsed.codec.name == 'utf-8'
    assert parsed.quality == decimal.Decimal('0.5')
    assert parsed in utf8
    assert utf8 in parsed


@nose.tools.raises(LookupError)
def test_charset_unknown():
    """LookupError is thrown when a character set is unknown."""

    mime.CharacterSet('unknown-charset')


@nose.tools.raises(ValueError)
def test_charset_invalid():
    """ValueError is thrown then a character set string cannot be parsed."""

    mime.CharacterSet.parse('@no such charset@; q=0.1')


def test_charset_negotiate():
    """The character set of the highest quality is picked among the options."""

    broker = negotiation.Broker(None, utf16, None, None)

    # An alias of ASCII should quality too.
    assert broker.best_offer([ascii_alias], [ascii]) is ascii

    # UTF-8 is available, but not requested by the client.
    assert broker.best_offer([ascii], [ascii, utf8]) is ascii

    # None of the options requested is available on the server.
    assert broker.best_offer([utf8], [ascii]) is None

    # There are multiple options available, choose one of highest quality.
    assert broker.best_offer([utf8, ascii], [utf8, ascii]) is utf8

    # Only UTF-8 is requested, and it is available.
    assert broker.best_offer([utf8], [utf8, ascii]) is utf8
