import keyring

SERVICE_NAME = "TaskFlow"
KEY_NAME = "gemini_api_key"

def get_api_key() -> str:
    try:
        return keyring.get_password(SERVICE_NAME, KEY_NAME) or ""
    except Exception:
        return ""

def set_api_key(value: str) -> None:
    value = value.strip()
    if value:
        keyring.set_password(SERVICE_NAME, KEY_NAME, value)
    else:
        try:
            keyring.delete_password(SERVICE_NAME, KEY_NAME)
        except keyring.errors.PasswordDeleteError:
            pass
