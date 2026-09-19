"""
로컬 SQLite에 인증 정보, 종목 목록, 개인 설정을 저장하는 모듈.

저장 방식
- 비밀번호: PBKDF2-HMAC-SHA256 해시 + 임의 솔트. 복호화할 필요가 없으므로 암호화가 아니라 해시로 보관한다.
- 개인 설정(기본 종목, RSI 임계값 등): 개인 정보로 보고 app_secret의 Fernet으로 암호화해서 저장한다.
- 종목 마스터 목록: 공개 정보이므로 평문으로 저장한다.
"""

import os
import sys
import json
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

DB_FILENAME = "stock_analyzer.db"
DEFAULT_USERNAME = "admin"

# 최초 1회 계정 생성 시 사용할 비밀번호. 환경변수가 있으면 그 값을 우선 사용한다.
INITIAL_PASSWORD_ENV = "STOCK_APP_PASSWORD"
FALLBACK_INITIAL_PASSWORD = "P@ssw0rd"

PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 4

# 개인 설정 기본값. DB에 저장된 값이 없을 때만 사용된다.
DEFAULT_PREFS: Dict[str, Any] = {
    "symbol": "AAPL",
    "rsi_diff_value": 5,
    "rsi_diff_period": 1,
    "rsi_buy": 30,
    "rsi_sell": 70,
}

# 최초 실행 시 tickers 테이블에 넣을 미국 시가총액 상위 종목.
# 이후에는 DB가 원본이므로 이 목록을 고쳐도 기존 DB에는 반영되지 않는다.
SEED_TICKERS: List[str] = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "LLY", "TSLA", "AVGO",
    "JPM", "UNH", "V", "XOM", "JNJ", "MA", "PG", "HD", "COST", "MRK",
    "ABBV", "CRM", "CVX", "AMD", "NFLX", "PEP", "KO", "BAC", "WMT", "TMO",
    "LIN", "MCD", "ADBE", "DIS", "CSCO", "ACN", "ABT", "INTU", "QCOM", "WFC",
    "DHR", "GE", "IBM", "CAT", "NOW", "TXN", "VZ", "AMGN", "COP", "PM",
    "PFE", "ISRG", "SPGI", "BA", "UNP", "HON", "NKE", "SYK", "RTX", "GS",
    "LOW", "PLD", "BKNG", "ELV", "MS", "T", "BLK", "DE", "INTC", "MDT",
    "VRTX", "REGN", "AMT", "LMT", "ADP", "MMC", "CB", "PANW", "CI", "TMUS",
    "BSX", "PGR", "SCHW", "ETN", "CMCSA", "C", "FI", "MU", "ZTS", "KLAC",
    "NEE", "LRCX", "SNPS", "CDNS", "TJX", "WM", "SHW", "GD", "MO", "SO",
]


def get_db_path() -> str:
    """DB 파일 경로를 반환합니다. STOCK_APP_DB 환경변수로 덮어쓸 수 있습니다."""
    override = os.environ.get("STOCK_APP_DB")
    if override:
        return os.path.abspath(override)

    # PyInstaller로 묶인 경우 _MEIPASS는 임시·읽기전용이므로 실행 파일 옆에 저장한다.
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, DB_FILENAME)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash_password(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


# ---------------------------------------------------------------- 초기화

def init_db() -> None:
    """테이블을 만들고 최초 계정·종목 목록을 채웁니다. (여러 번 호출해도 안전)"""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username            TEXT PRIMARY KEY,
                password_hash       BLOB    NOT NULL,
                salt                BLOB    NOT NULL,
                iterations          INTEGER NOT NULL,
                is_initial_password INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT    NOT NULL,
                updated_at          TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                symbol     TEXT PRIMARY KEY,
                name       TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL
            )
        """)
        # 개인 설정은 값 전체를 암호화해서 encrypted_value 한 칸에 넣는다.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                username        TEXT PRIMARY KEY,
                encrypted_value TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
        """)

        row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        if row["cnt"] == 0:
            initial_password = os.environ.get(INITIAL_PASSWORD_ENV) or FALLBACK_INITIAL_PASSWORD
            salt = secrets.token_bytes(SALT_BYTES)
            conn.execute(
                """
                INSERT INTO users
                    (username, password_hash, salt, iterations, is_initial_password, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (DEFAULT_USERNAME, _hash_password(initial_password, salt), salt,
                 PBKDF2_ITERATIONS, _now(), _now()),
            )

        row = conn.execute("SELECT COUNT(*) AS cnt FROM tickers").fetchone()
        if row["cnt"] == 0:
            conn.executemany(
                "INSERT INTO tickers (symbol, name, sort_order, is_active, created_at) VALUES (?, NULL, ?, 1, ?)",
                [(symbol, index, _now()) for index, symbol in enumerate(SEED_TICKERS)],
            )

        # 로그인 요구 여부 기본값: 0(끔) — 기존 동작(메인 화면 바로 표시)을 유지한다.
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES ('require_login', '0', ?)",
            (_now(),),
        )


# ---------------------------------------------------------------- 비밀번호

def verify_password(username: str, password: str) -> bool:
    """비밀번호가 맞는지 확인합니다. 타이밍 공격을 피하기 위해 compare_digest를 사용합니다."""
    if not password:
        return False

    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash, salt, iterations FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return False

    candidate = _hash_password(password, row["salt"], row["iterations"])
    return hmac.compare_digest(candidate, row["password_hash"])


def set_password(username: str, new_password: str) -> None:
    """비밀번호를 새 솔트로 다시 해싱해 저장합니다."""
    salt = secrets.token_bytes(SALT_BYTES)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE users
               SET password_hash = ?, salt = ?, iterations = ?, is_initial_password = 0, updated_at = ?
             WHERE username = ?
            """,
            (_hash_password(new_password, salt), salt, PBKDF2_ITERATIONS, _now(), username),
        )


def change_password(username: str, current_password: str, new_password: str,
                    confirm_password: str) -> Tuple[bool, str]:
    """현재 비밀번호를 확인한 뒤 교체합니다. (성공여부, 안내문구)를 반환합니다."""
    if not verify_password(username, current_password):
        return False, "현재 비밀번호가 일치하지 않습니다."

    if new_password != confirm_password:
        return False, "새 비밀번호와 확인 값이 서로 다릅니다."

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"새 비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다."

    if new_password == current_password:
        return False, "현재 비밀번호와 다른 값을 입력하세요."

    set_password(username, new_password)
    return True, "비밀번호가 변경되었습니다."


def uses_initial_password(username: str = DEFAULT_USERNAME) -> bool:
    """아직 최초 발급 비밀번호를 그대로 쓰고 있는지 여부."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT is_initial_password FROM users WHERE username = ?", (username,)
        ).fetchone()

    return bool(row["is_initial_password"]) if row else False


# ---------------------------------------------------------------- 앱 설정

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()

    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, _now()),
        )


def is_login_required() -> bool:
    """로그인 화면을 거칠지 여부. DB의 require_login 값으로 제어합니다."""
    return get_setting("require_login", "0") == "1"


def set_login_required(required: bool) -> None:
    set_setting("require_login", "1" if required else "0")


# ---------------------------------------------------------------- 종목 목록

def get_tickers() -> List[str]:
    """화면에 보여줄 종목 심볼 목록을 정렬해서 반환합니다."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT symbol FROM tickers WHERE is_active = 1 ORDER BY sort_order, symbol"
        ).fetchall()

    return [row["symbol"] for row in rows]


def add_ticker(symbol: str, name: Optional[str] = None) -> None:
    """목록에 없는 종목을 추가합니다. 이미 있으면 다시 활성화만 합니다."""
    symbol = symbol.strip().upper()
    if not symbol:
        return

    with _connect() as conn:
        max_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS m FROM tickers").fetchone()["m"]
        conn.execute(
            """
            INSERT INTO tickers (symbol, name, sort_order, is_active, created_at) VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(symbol) DO UPDATE SET is_active = 1, name = COALESCE(excluded.name, tickers.name)
            """,
            (symbol, name, max_order + 1, _now()),
        )


def remove_ticker(symbol: str) -> None:
    """목록에서 숨깁니다. (행을 지우지 않고 is_active만 내린다)"""
    with _connect() as conn:
        conn.execute("UPDATE tickers SET is_active = 0 WHERE symbol = ?", (symbol.strip().upper(),))


# ---------------------------------------------------------------- 개인 설정 (암호화 저장)

def get_user_prefs(username: str = DEFAULT_USERNAME) -> Dict[str, Any]:
    """저장된 개인 설정을 복호화해 반환합니다. 없거나 복호화에 실패하면 기본값을 돌려줍니다."""
    from app_secret import decrypt_text

    with _connect() as conn:
        row = conn.execute(
            "SELECT encrypted_value FROM user_prefs WHERE username = ?", (username,)
        ).fetchone()

    prefs = dict(DEFAULT_PREFS)
    if row is None:
        return prefs

    decrypted = decrypt_text(row["encrypted_value"])
    if decrypted is None:
        return prefs

    try:
        stored = json.loads(decrypted)
    except json.JSONDecodeError:
        return prefs

    # 알고 있는 키만 받아들여, 예전 버전의 값이 남아 있어도 안전하게 동작하도록 한다.
    prefs.update({key: value for key, value in stored.items() if key in DEFAULT_PREFS})
    return prefs


def save_user_prefs(prefs: Dict[str, Any], username: str = DEFAULT_USERNAME) -> None:
    """개인 설정을 암호화해서 저장합니다."""
    from app_secret import encrypt_text

    payload = {key: prefs.get(key, DEFAULT_PREFS[key]) for key in DEFAULT_PREFS}
    encrypted = encrypt_text(json.dumps(payload, ensure_ascii=False))

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_prefs (username, encrypted_value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                encrypted_value = excluded.encrypted_value,
                updated_at = excluded.updated_at
            """,
            (username, encrypted, _now()),
        )


if __name__ == "__main__":
    # 점검용 실행: python app_db.py
    init_db()
    print(f"DB 경로            : {get_db_path()}")
    print(f"로그인 요구 여부   : {is_login_required()}")
    print(f"초기 비밀번호 사용 : {uses_initial_password()}")
    print(f"등록 종목 수       : {len(get_tickers())}")
    print(f"개인 설정          : {get_user_prefs()}")
