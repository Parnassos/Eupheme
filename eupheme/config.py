"""Configuration module.

This module deals with the config object used by the Application class to
make some parts of the application's behaviour configurable.

"""

import yaml
import eupheme.mime as mime


class Config:

    """Config class.

    A slightly neater way of accessing the yaml config file instead of
    dictionaries.

    """

    defaults = {
        'charsets': {'utf-8', 'ascii'},
        'methods': {'GET', 'POST', 'PUT'},
        'default':
        {
            'mimetype': 'text/html',
            'charset': 'utf-8'
        }
    }

    def __init__(self, data):
        """Create a new Config instance."""

        for key in data:
            if isinstance(data[key], dict):
                setattr(self, key, Config(data[key]))
            else:
                # Anything that isn't a dict we probably want as
                # a final property.
                setattr(self, key, data[key])

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __repr__(self):
        return repr(self.__dict__)


def load(path=None):
    """Create a new config instance.

    Create a new config instance that loads the contents of the
    provided path and tries to parse it as yaml.

    Returns a Config object.

    """

    # If no path was provided just create an empty dict
    if path is None:
        data = {}
    else:
        yml = open(path, 'r')
        data = yaml.safe_load(yml)

    # Make sure defaults are set valid and then turn them into
    # objects usable by our code.
    data = _check_defaults(data)
    _verify(data)
    return _objectify(data)


def _verify(data):
    """Verify the contents of the config and points out any errors."""

    # Make sure the lengths of all the keys are correct
    assert len(data['charsets']) > 0, \
        'Must support at least one charset'

    assert len(data['methods']) > 0, \
        'Must support at least one method'

    # Make sure the default charset is in the list of supported charsets
    assert data['default']['charset'] in data['charsets'], \
        'Default charset has to be in the list of supported charsets'


def _objectify(data):
    """Transform the data into a proper Config object.

    Takes a dict with information and returns a proper Config object.

    """

    conf = Config(data)

    # Convert the charsets into CharacterSet objects
    conf.charsets = set(
        mime.CharacterSet.parse(charset) for charset in conf.charsets
    )

    # Make sure methods is a set rather than a list
    conf.methods = set(conf.methods)

    conf.default.charset = mime.CharacterSet.parse(conf.default.charset)
    conf.default.mimetype = mime.MimeType.parse(conf.default.mimetype)

    return conf


def _check_defaults(data):
    """Make sure the default values are available in the dictionary.

    Makes sure all the default values are filled, also makes sure
    missing keys are added to the dict.

    Returns a dict with default data filled where necessary.

    """

    # Make sure data is not none whn we reach the the actual checks
    if data is None:
        data = {}

    # If there's no default key at all, add it
    if 'default' not in data:
        data['default'] = Config.defaults['default']

    config = data['default']
    defaults = data['default']

    # Set the default values if any of the keys are missing
    if 'mimetype' not in config:
        config['mimetype'] = defaults['mimetype']

    if 'charset' not in config:
        config['charset'] = defaults['charset']

    config = data
    defaults = Config.defaults

    if 'charsets' not in data:
        config['charsets'] = defaults['charsets']

    if 'methods' not in data:
        config['methods'] = defaults['methods']

    return config
