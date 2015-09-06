from eupheme.cookies import CookieManager, InvalidOperationException
import codecs
import nose


CookieManager.key = "bzuz8RDABLhqt"
CookieManager.codec = codecs.lookup('utf-8')
cookies = CookieManager()
cookies_ro = CookieManager.load({'testcookie': 'testval'}, ro=True)


def test_valid_cookie():
    """ Test if valid cookies are read correctly """
    cookies.set_cookie('testcookie', 'someval')

    cookie = cookies.get_cookie('testcookie')

    assert cookie == 'someval'


def test_nonexistent_cookie():
    """ Test loading an non-existent cookie """
    ex_cookie = cookies.get_cookie('testcookie')
    non_cookie = cookies.get_cookie('noncookie')

    assert ex_cookie == 'someval'
    assert non_cookie is None


def pass_nonexistent_signed_cookie():
    """ Test loading a non-existent signed cookie """
    cookie = cookies.get_signed_cookie('noncookie')

    assert cookie is None


def test_unsigned_cookie():
    """ Test loading an unsigned cookie as signed """
    cookie = cookies.get_signed_cookie('testcookie')

    assert cookie is None


def test_invalid_signed_cookie():
    """ Test loading an invalid signed cookie """
    cookies.set_cookie('invalid_signed', 'Z2FvZ2Fv|1402054940|8cf643ba920ac8233ab6238670ea2322554d9576b92cf51a6d29ce67')
    cookie = cookies.get_signed_cookie('invalid_signed')

    assert cookie is None


def test_valid_signed_cookie():
    """ Test loading a valid signed cookie """
    cookies.set_signed_cookie('valid_signed', 'gaogao')

    cookie = cookies.get_signed_cookie('valid_signed')
    assert cookie is not None
    assert cookie == 'gaogao'


@nose.tools.raises(InvalidOperationException)
def test_nokey_signed_cookie():
    """ Test if signing a cookie without a key errors """
    cookies.key = None

    # Handle the exception to restore the key and then raise the error
    # again to let nose detect it.
    try:
        cookies.set_signed_cookie('gaogao', 'test')
    except InvalidOperationException as e:
        cookies.key = CookieManager.key
        raise e


@nose.tools.raises(InvalidOperationException)
def test_read_only_manager():
    """ Test setting a cookie on a read only manager """
    # Try reading some before triggering an exception
    cookie = cookies_ro.get_cookie('testcookie')
    assert cookie == 'testval'
    # This should raise an InvalidOperationException
    cookies_ro.set_cookie('gaogao', 'test')
