import nose

import eupheme.mime as mime


@nose.tools.raises(ValueError)
def test_mimeparameter_invalid_key():
    """Mime parameter keys should be valid tokens."""

    mime.MimeParameters('fo"o=bar')


@nose.tools.raises(ValueError)
def test_mimeparameter_invalid_value():
    """Unquoted mime parameter values should be valid tokens."""

    mime.MimeParameters('foo=b:ar')


def test_mimeparameter_single_property():
    """A single mime parameter can be parsed correctly."""

    parsed = mime.MimeParameters('foo=bar')
    assert parsed['foo'] == 'bar'
    assert len(parsed) == 1


def test_mimeparameter_multiple_properties():
    """Multiple mime parameters can be parsed correctly."""

    parsed = mime.MimeParameters('foo=bar; asd=qwe')
    assert parsed['foo'] == 'bar'
    assert parsed['asd'] == 'qwe'
    assert len(parsed) == 2


def test_mimeparameter_quality_property():
    """Mime quality parameters are not counted towards the length."""

    parsed = mime.MimeParameters('foo=bar; q=0.5')
    assert parsed['foo'] == 'bar'
    assert parsed['q'] == '0.5'
    assert len(parsed) == 1


def test_mimeparameter_quoted():
    """Characters forbidden in mime parameter values are allowed in quotes."""

    # Note the escaped backslash that is to be unquoted
    parsed = mime.MimeParameters('foo="bar"; asd="qwe@ <>[]\r\n\\\\"')
    assert parsed['foo'] == 'bar'
    assert parsed['asd'] == "qwe@ <>[]\r\n\\"
    assert len(parsed) == 2


@nose.tools.raises(ValueError)
def test_mimeparameter_linefeed():
    """Lonely linefeeds are forbidden in tokens."""

    mime.MimeParameters('foo=bar\rbaz')
