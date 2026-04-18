from app.config import Settings


def test_blank_cors_origin_regex_disables_regex() -> None:
    settings = Settings(cors_origin_regex="")

    assert settings.cors_origin_regex is None
