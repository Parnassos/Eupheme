import re
import eupheme.response as response


class Route:
    """Represents a route served by the application."""

    def __init__(self, pattern, resource):
        """Instantiates a route.

        The argument 'pattern' is assumed to be a valid regular expression.
        """

        self.pattern = re.compile(pattern)
        self.resource = resource


class RouteManager:
    """Manages all routes served by the application."""

    def __init__(self):
        """Instantiates a route manager with an empty routing table."""

        self.routes = []

    def add(self, pattern, resource):
        """
        Adds a route for the regular expression 'pattern' pointing to the
        resource 'resource'. Routes will be matched in their order of adding.
        """

        self.routes.append(Route(pattern, resource))

    def match(self, path):
        """
        Attemps to find a match for requested path 'path' and returns a pair
        of the associated resource and the subpatterns matched on the path, in
        that order. Raises HttpNotFoundException if no matching path is found.
        """

        for route in self.routes:
            match = route.pattern.match(path)
            if match:
                return route.resource, match.groups()

        raise response.HttpNotFoundException(path)
