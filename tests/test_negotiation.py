import decimal

import eupheme.negotiation as negotiation
import eupheme.mime as mime

# Mime types that we will be using for testing, from least to most specific.
any_any = mime.MimeType('*', '*')
text_any = mime.MimeType('text', '*')
text_plain = mime.MimeType('text', 'plain')
text_plain_foo = mime.MimeType('text', 'plain', foo='oof')
text_plain_bar = mime.MimeType('text', 'plain', bar='rab')
text_plain_both = mime.MimeType('text', 'plain', foo='oof', bar='rab')


def test_matches():
    """A subtype matches for a supertype, but not vice versa."""

    # All types match for the wildcard type
    assert any_any in any_any
    assert text_any in any_any
    assert text_plain in any_any
    assert text_plain_foo in any_any
    assert text_plain_bar in any_any
    assert text_plain_both in any_any

    # All text types match the text/* type
    assert any_any not in text_any
    assert text_any in text_any
    assert text_plain in text_any
    assert text_plain_foo in text_any
    assert text_plain_bar in text_any
    assert text_plain_both in text_any

    # All plain text types match the text/plain type
    assert text_any not in text_plain
    assert text_plain in text_plain
    assert text_plain_foo in text_plain
    assert text_plain_bar in text_plain
    assert text_plain_both in text_plain

    # Parameters further restrict the plain type
    assert text_plain not in text_plain_foo
    assert text_plain not in text_plain_bar
    assert text_plain_foo not in text_plain_bar
    assert text_plain_bar not in text_plain_foo

    # Parameters in text_plain_both are a superset and therefore more specific
    # than the text/plain types having only one parameter.
    assert text_plain_both in text_plain_bar
    assert text_plain_both in text_plain_foo
    assert text_plain_bar not in text_plain_both
    assert text_plain_foo not in text_plain_both


def test_specific():
    """
    Mime types are orderable with the least specific types as least elements of
    the sequence.
    """

    assert any_any < text_any
    assert text_any < text_plain
    assert text_plain < text_plain_foo
    assert text_plain < text_plain_foo
    assert text_plain_foo < text_plain_both
    assert text_plain_bar < text_plain_both


def test_assign_quality():
    """
    Requested mime types are assigned the appropriate quality.
    """

    # This test is adapted from RFC2616 section 14.1.
    text_html_1 = mime.MimeType.parse('text/html;level=1')
    text_html_2 = mime.MimeType.parse('text/html;level=2')
    text_html_3 = mime.MimeType.parse('text/html;level=3')
    text_html = mime.MimeType.parse('text/html')
    text_plain = mime.MimeType.parse('text/plain')
    image_jpeg = mime.MimeType.parse('image/jpeg')

    offered = [
        text_html_1,
        text_html_2,
        text_html_3,
        text_html,
        text_plain,
        image_jpeg,
    ]

    requested = [
        mime.MimeType.parse('text/*;q=0.3'),
        mime.MimeType.parse('text/html;q=0.7'),
        mime.MimeType.parse('text/html;level=1'),
        mime.MimeType.parse('text/html;level=2;q=0.4'),
        mime.MimeType.parse('*/*;q=0.5'),
    ]

    # Initialize a dummy broker.
    broker = negotiation.Broker(None, None, None, None)

    # Test that all requested types are assigned the right priority, that of
    # the offered type that matches them best.
    match_text_html_1 = broker.closest_match(requested, text_html_1)
    assert match_text_html_1.quality == decimal.Decimal('1')

    match_text_html_2 = broker.closest_match(requested, text_html_2)
    assert match_text_html_2.quality == decimal.Decimal('0.4')

    match_text_html_2 = broker.closest_match(requested, text_html_3)
    assert match_text_html_2.quality == decimal.Decimal('0.7')

    match_text_html = broker.closest_match(requested, text_html)
    assert match_text_html.quality == decimal.Decimal('0.7')

    match_text_plain = broker.closest_match(requested, text_plain)
    assert match_text_plain.quality == decimal.Decimal('0.3')

    match_image_jpeg = broker.closest_match(requested, image_jpeg)
    assert match_image_jpeg.quality == decimal.Decimal('0.5')

    # Test that the offered type of the highest client-assigned quality is
    # selected by the negotiation algorithm.
    assert broker.best_offer(requested, offered) == text_html_1
