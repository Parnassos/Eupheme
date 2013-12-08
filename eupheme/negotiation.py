import decimal

import eupheme.response as response


class Negotiable:
    """Represents a property that can be negotiated."""

    @property
    def quality(self):
        """The mime quality parameter as a decimal."""

        try:
            return decimal.Decimal(self.parameters['q'])
        except KeyError:
            return decimal.Decimal('1')

    def __contains__(self, other):
        """
        Should be overridden to return True when the negotiable 'other' will
        satisfy this negotiable when chosen.
        """

        raise NotImplementedError

    def __gt__(self, other):
        """
        Should be overridden to return True when this negotiable is stricter
        than the negotiable 'other'.
        """

        raise NotImplementedError


class Broker:
    """Brokers incoming HTTP requests.

    Contains methods that concern themselves with choosing the best options
    based on those preferred by the client and supported by the server. Methods
    will throw the appropriate HttpException when negotiations break down.
    """

    def __init__(self, charsets, default_charset, methods, default_mimetype):
        """
        Instantiates a broker object which can offer the character sets in
        'charsets' and the methods in 'methods'. If no character set is
        requested, it will fall back to 'default_charset'. Likewise, if no
        content type is requested, 'default_mimetype' will be chosen.
        """

        self.charsets = charsets
        self.default_charset = default_charset
        self.methods = methods
        self.default_mimetype = default_mimetype

    def closest_match(self, requested, offer):
        """
        Returns the closest match for the negotiable 'offer' among those in
        'requested'. Throws a ValueError when no matching offer is found.
        """

        return max(req for req in requested if offer in req)

    def best_offer(self, requested, offered):
        """
        Returns the offer from 'offered' that is assigned the highest quality
        among the negotiables in 'requested'. Returns None if none of the
        offers made satisfies any of the requested negotiables.
        """

        best = None
        best_quality = None

        for offer in offered:
            try:
                # Find the most specific match for this offer.
                match = self.closest_match(requested, offer)
            except ValueError:
                # This offer does not satisfy any request.
                continue

            # Check if this offer represents a better (client-assigned) quality
            # than any offer we have been able to make.
            if best is None or best_quality < match.quality:
                best = offer
                best_quality = match.quality

        return best

    def negotiate_endpoint(self, method, resource):
        """
        Negotiates the endpoint for the HTTP method 'method' when requested for
        the resource 'resource'.
        """

        if method not in self.methods:
            # Method is not known by the server -- RFC2616 section 5.1.1.
            raise response.HttpNotImplementedException()

        if method not in resource.allowed_methods:
            # Method not allowed for this resource -- RFC2616 section 5.1.1.
            raise response.HttpMethodNotAllowedException(resource.allowed_methods)

        try:
            return getattr(resource, method.lower())
        except AttributeError:
            # Endpoint method is missing, though it should be there.
            raise response.HttpInternalServerErrorException()

    def negotiate_charset(self, accepted):
        """
        Negotiates the character set, given the sets accepted by the client in
        'accepted'. Returns the negotiated character set.
        """

        if accepted is None:
            # if the Accept-Charset header is not present, any character set
            # is acceptable in the response -- RFC2616 section 14.2.
            charset = self.default_charset
        else:
            charset = self.best_offer(accepted, self.charsets)

            if charset is None:
                # If we support none of the character sets requested by the
                # client, we reject the request -- RFC2616 section 14.2.
                raise response.HttpNotAcceptableException()

        return charset

    def negotiate_input(self, request, endpoint):
        """
        Negotiates the input mime type when 'request' is routed to 'endpoint'.
        Returns the data when accepted, None when there is no input data.
        """

        if request.content_length is None or request.content_type is None:
            # No input content given, nothing to negotiate about.
            return

        if request.content_type not in endpoint.consumes:
            # We cannot parse the content type -- RFC2616 section 10.4.16.
            raise response.HttpUnsupportedMediaTypeException()

        if request.content_length is not None:
            return request.read_entity()
        else:
            return None

    def negotiate_output(self, request, endpoint):
        """
        Negotiates the output mime type when 'request' is routed to 'endpoint'.
        Returns the negotiated mime type on success.
        """

        if request.accept is None:
            # If the Accept header is absent, then the client is assumed to
            # accept any content type -- RFC2616 section 14.1.
            mimetype = self.default_mimetype
        else:
            mimetype = self.best_offer(request.accept, endpoint.produces)
            if mimetype is None:
                # If we cannot generate any of the content types requested,
                # we should reject the request -- RFC2616 section 14.1.
                raise response.HttpNotAcceptableException()

        return mimetype
