import json
import os
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
RATE_LIMIT_SECONDS = 60
LOCAL_TIMEZONE = ZoneInfo("Asia/Yekaterinburg")
recent_submissions = {}


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def normalize_phone(raw_phone: str) -> str:
    digits = re.sub(r"\D", "", raw_phone or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return "+" + digits
    if len(digits) == 10:
        return "+7" + digits
    return ""


def build_telegram_message(phone: str, message: str) -> str:
    timestamp = datetime.now(LOCAL_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    details = message.strip() if message.strip() else "Не указано"
    return (
        "Новая заявка с сайта Мастер72\n\n"
        f"Телефон: {phone}\n"
        f"Что нужно сделать: {details}\n"
        f"Время: {timestamp}"
    )


def send_to_telegram(phone: str, message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError("Telegram env vars are missing")

    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": build_telegram_message(phone, message),
        }
    ).encode("utf-8")

    request = Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"Telegram HTTP error: {error.code}") from error
    except URLError as error:
        raise RuntimeError("Telegram is unreachable") from error

    if not response_payload.get("ok"):
        raise RuntimeError("Telegram API rejected the message")


def is_rate_limited(client_ip: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    last_seen = recent_submissions.get(client_ip, 0)

    # Drop stale entries on the same pass to keep the dict small.
    stale_before = now - (RATE_LIMIT_SECONDS * 5)
    for ip, timestamp in list(recent_submissions.items()):
        if timestamp < stale_before:
            del recent_submissions[ip]

    if now - last_seen < RATE_LIMIT_SECONDS:
        return True

    recent_submissions[client_ip] = now
    return False


class LeadHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/lead":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.respond_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": "Некорректные данные формы."},
            )
            return

        phone = normalize_phone(str(payload.get("phone", "")))
        message = str(payload.get("message", "")).strip()
        company = str(payload.get("company", "")).strip()

        if not phone:
            self.respond_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": "Введите корректный номер телефона."},
            )
            return

        if company:
            self.respond_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "message": "Не удалось отправить заявку."},
            )
            return

        if is_rate_limited(self.client_address[0]):
            self.respond_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {
                    "ok": False,
                    "message": "Слишком много попыток. Попробуйте ещё раз через минуту.",
                },
            )
            return

        try:
            send_to_telegram(phone, message)
        except RuntimeError as error:
            self.respond_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "message": str(error)},
            )
            return

        self.respond_json(
            HTTPStatus.OK,
            {"ok": True, "message": "Заявка отправлена. Скоро свяжемся с вами."},
        )

    def respond_json(self, status: HTTPStatus, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    load_env_file()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "4173"))
    server = ThreadingHTTPServer((host, port), LeadHandler)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
