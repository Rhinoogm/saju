from app.config import Settings


def test_blank_cors_origin_regex_disables_regex() -> None:
    settings = Settings(cors_origin_regex="")

    assert settings.cors_origin_regex is None


def test_llm_completion_token_defaults_are_large_enough_for_final_reading() -> None:
    settings = Settings(_env_file=None)

    assert settings.ollama_num_predict == 4096
    assert settings.groq_max_completion_tokens == 4096
