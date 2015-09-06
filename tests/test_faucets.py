""" Testing module for eupheme.faucets.

This file contains the testcases used to test the functionality of the
various faucets used in Eupheme.

"""

import eupheme.faucets as faucets
import eupheme.mime as mime

import nose
from json import loads


def test_parse_strings():
    """Determine if parse_strings returns objects properly."""

    strings = [
        'text/html',
        'application/json',
        mime.MimeType('text', 'plain')
    ]

    mimes = [x for x in faucets.parse_strings(strings)]

    # Confirm the length
    assert len(mimes) == 3

    # Make sure the things we asked for are in the list
    assert mime.MimeType('text', 'html') in mimes
    assert mime.MimeType('application', 'json') in mimes
    assert strings[2] in mimes


# Test all the decorators at once
def test_decorator_lengths():
    """Combined decorator test.

    Determines if the produces, consumes and template decorators apply
    correctly and return correct data of the right length.

    """

    @faucets.produces(
        'text/html', 'application/json',
        'text/plain', 'text/html')
    @faucets.consumes('text/html', 'application/json')
    @faucets.template('index.html')
    def test():
        return True

    assert len(test.produces) == 3
    assert len(test.consumes) == 2
    assert test.template == 'index.html'


def test_formfaucet():
    """Test FormFaucet handling of incoming data.

    Determines if decoding of unicode strings and ordinary ascii works as
    intended.

    """

    formfaucet = faucets.FormFaucet()
    result1 = formfaucet.incoming(
        faucets.Flow(
            faucets.Flow.IN,
            b'%E3%83%8B%E3%83%A3%E3%83%BC=test&silly=rawr'
        )
    )

    result2 = formfaucet.incoming(
        faucets.Flow(
            faucets.Flow.IN,
            b'key=test&key=hohum&nope='
        )
    )

    assert len(result1) == 2
    assert result1['ニャー'] == ['test'] and result1['silly'] == ['rawr']
    assert len(result2) == 1 and len(result2['key']) == 2
    assert result2['key'] == ['test', 'hohum']


def test_jinjafaucet():
    """Test if JinjaFaucet uses the specified template.

    Determines if the JinjaFaucet uses the template specified using the
    template decorator.

    """

    @faucets.template('test_template.html')
    def test():
        pass

    jinja = faucets.JinjaFaucet('tests/')

    flow = faucets.Flow(
        faucets.Flow.OUT,
        {
            'data': 'Some test data',
            'ニャー': 'Nyaa~'
        },
        endpoint=test
    )

    result = jinja.outgoing(flow)

    assert '<title>Test template</title>' in result
    assert 'Some test data' in result
    assert 'Test data:' in result


def test_jsonfaucet():
    """Test if JsonFaucet properly dumps data as JSON."""

    def test():
        pass

    json = faucets.JsonFaucet()

    result = json.outgoing(
        faucets.Flow(
            faucets.Flow.OUT,
            {
                'data': 'Some test data',
                'ニャー': 'Nyaa~'
            },
            endpoint=test
        )
    )

    assert 'Some test data' in result
    assert 'Nyaa~' in result
    assert r'\u30cb\u30e3\u30fc' in result


class A:
    a = 'test'
    b = 'test2'

    def to_json_compat(self):
        return {'a': self.a, 'b': self.b}


def test_jsonencoder():
    """ Test if the EuphemeJsonEncoder works as intended. """
    encoder = faucets.EuphemeJsonEncoder()

    a_obj = A()
    json_data = encoder.encode(a_obj)
    json_obj = loads(json_data)

    assert json_obj['a'] == 'test'
    assert json_obj['b'] == 'test2'


def test_jsonfaucet_encoder():
    """ Test if the JsonFaucet properly dumps custom data. """
    jsonf = faucets.JsonFaucet()
    data = {'a': 'testing', 'obj': A()}

    result = jsonf.outgoing(
        faucets.Flow(
            faucets.Flow.OUT, data
        )
    )

    result_obj = loads(result)

    assert result_obj['a'] == 'testing'
    assert result_obj['obj']['a'] == 'test'
    assert result_obj['obj']['b'] == 'test2'


@nose.tools.raises(TypeError)
def test_jsonfaucet_encoder_exception():
    """ Test if the JsonFaucet throws an exception as expected. """
    jsonf = faucets.JsonFaucet()

    class B:
        pass

    data = {'a': 'testing', 'obj': B()}

    result = jsonf.outgoing(
        faucets.Flow(
            faucets.Flow.OUT, data
        )
    )

    print(result)
