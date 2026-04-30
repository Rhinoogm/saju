from app.config import Settings


def test_blank_cors_origin_regex_disables_regex() -> None:
    settings = Settings(cors_origin_regex="")

    assert settings.cors_origin_regex is None


def test_llm_completion_token_defaults_are_large_enough_for_final_reading() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "gemini"
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.ollama_num_predict == 4096
    assert settings.groq_max_completion_tokens == 5000
    assert settings.groq_max_request_tokens == 6000
    assert settings.gemini_max_output_tokens == 5000
    assert settings.llm_custom_questions_max_output_tokens == 1200
    assert settings.llm_final_reading_max_output_tokens == 5000
    assert settings.llm_debug_metrics_enabled is False
