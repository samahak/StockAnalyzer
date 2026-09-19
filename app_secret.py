"""
민감 정보 암호화 모듈.

- 비밀번호는 복호화할 필요가 없으므로 이 모듈이 아니라 app_db의 PBKDF2 해시로 처리한다.
- 나중에 다시 읽어야 하는 개인 정보(사용자 설정 등)는 이 모듈의 Fernet(AES-128-CBC + HMAC)으로
  암호화해서 SQLite에 저장한다.

키 관리
- 환경변수 STOCK_APP_SECRET_KEY 가 있으면 그 값을 키로 사용한다. (권장)
- 없으면 DB 파일 옆의 .secret.key 파일을 사용하고, 없으면 새로 만든다(권한 0600).
- 키 파일이 사라지면 암호화된 값은 복구할 수 없으므로, 복호화 실패 시 예외 대신 기본값으로 처리한다.
"""

import os
import stat
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

SECRET_KEY_ENV = "STOCK_APP_SECRET_KEY"
KEY_FILENAME = ".secret.key"

_fernet: Optional[Fernet] = None


def _key_path() -> str:
    from app_db import get_db_path  # 순환 import 방지를 위해 함수 안에서 import

    return os.path.join(os.path.dirname(get_db_path()), KEY_FILENAME)


def _load_or_create_key() -> bytes:
    env_key = os.environ.get(SECRET_KEY_ENV)
    if env_key:
        return env_key.encode("utf-8")

    path = _key_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().strip()

    key = Fernet.generate_key()
    # 먼저 0600으로 만들고 나서 쓴다 (생성과 권한 설정 사이의 틈을 없앤다)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "wb") as f:
        f.write(key)

    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt_text(plain_text: str) -> str:
    """문자열을 암호화해 저장 가능한 토큰 문자열로 돌려줍니다."""
    return _get_fernet().encrypt(plain_text.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> Optional[str]:
    """암호화된 토큰을 복호화합니다. 키가 바뀌었거나 값이 깨졌으면 None을 반환합니다."""
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
