from contracts import BrandMatchRequest, BrandMatchResult, ImageSource


def test_brand_match_request_assumes_a_user_image_unless_told_otherwise():
    # A person's screenshot may hold personal data, so forgetting the field must be the private choice.
    request = BrandMatchRequest(image_b64="aGVsbG8=", current_domain="exemplo.com")
    assert request.image_source is ImageSource.USER_IMAGE


def test_brand_match_request_accepts_a_page_screenshot():
    request = BrandMatchRequest(image_b64="aGVsbG8=", image_source="page_screenshot")
    assert request.image_source is ImageSource.PAGE_SCREENSHOT


def test_brand_match_result_keeps_an_unconfirmed_brand_apart_from_a_match():
    result = BrandMatchResult(possible_brand="Nubank", similarity=0.75)
    assert result.matched_brand is None
    assert result.is_spoofing is False
    assert result.possible_brand == "Nubank"
