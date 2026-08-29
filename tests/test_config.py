from config import load_environment


def test_load_environment_reads_dotenv_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=local-test-value\nOPENAI_MODEL=test-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    assert load_environment(env_file) is True
    assert __import__("os").environ["OPENAI_API_KEY"] == "local-test-value"
    assert __import__("os").environ["OPENAI_MODEL"] == "test-model"


def test_load_environment_does_not_override_existing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_MODEL", "shell-model")

    load_environment(env_file)

    assert __import__("os").environ["OPENAI_MODEL"] == "shell-model"
