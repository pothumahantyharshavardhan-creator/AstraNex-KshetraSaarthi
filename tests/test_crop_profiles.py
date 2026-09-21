from backend.services import crop_profiles


def test_tomato_profile_loads_and_matches_v32_defaults():
    profile = crop_profiles.get_profile('tomato')
    assert profile is not None
    assert profile['validation_status'] == 'NOT_FIELD_VALIDATED'
    assert crop_profiles.moisture_threshold('tomato', 'seedling') == 38
    assert crop_profiles.moisture_threshold('tomato', 'fruiting') == 44


def test_unconfigured_crop_falls_back_to_default_without_fabricating():
    assert crop_profiles.get_profile('maize') is None
    assert crop_profiles.moisture_threshold('maize', 'seedling', default=40) == 40


def test_unsupported_growth_stage_is_reported_not_guessed():
    assert crop_profiles.stage_supported('tomato', 'dormant') is False
    assert crop_profiles.stage_supported('tomato', 'flowering') is True
    # Unconfigured crop: never claim stage support it can't back up.
    assert crop_profiles.stage_supported('maize', 'flowering') is False


def test_list_crops_includes_seeded_profiles():
    crops = crop_profiles.list_crops()
    assert 'tomato' in crops and 'wheat' in crops and 'rice' in crops
