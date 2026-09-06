from worldsmith.secrets import SecretStore


def test_secret_store_round_trip_without_real_keyring(monkeypatch):
    values = {}
    monkeypatch.setattr("worldsmith.secrets.keyring.set_password", lambda service, name, value: values.__setitem__((service, name), value))
    monkeypatch.setattr("worldsmith.secrets.keyring.get_password", lambda service, name: values.get((service, name)))
    monkeypatch.setattr("worldsmith.secrets.keyring.delete_password", lambda service, name: values.pop((service, name), None))

    assert SecretStore.set("openai", "test-key") is True
    assert SecretStore.get("openai") == "test-key"
    SecretStore.set("openai", "")
    assert SecretStore.get("openai") == ""
