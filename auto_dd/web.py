import hmac
import secrets
from flask import Flask, jsonify, request, send_file, send_from_directory
from io import BytesIO
from .model import validate
from .sample import sample
from .extract import postgres, bigquery
from .export import export
from .ai import describe


def create_app(token=None):
    app = Flask(__name__, static_folder="static", static_url_path="/assets")
    app.config.update(MAX_CONTENT_LENGTH=16*1024*1024, TOKEN=token or secrets.token_urlsafe(32))

    @app.before_request
    def protect():
        # Reject DNS rebinding and cross-origin access to the local desktop service.
        if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
            return jsonify(error="로컬 호스트만 허용됩니다."), 403
        if request.path.startswith("/api/"):
            if not hmac.compare_digest(request.headers.get("X-Auto-DD-Token", ""), app.config["TOKEN"]):
                return jsonify(error="앱 실행 주소로 다시 접속하세요."), 403
            origin = request.headers.get("Origin")
            if origin and origin != request.host_url.rstrip("/"):
                return jsonify(error="외부 사이트 요청은 허용하지 않습니다."), 403

    @app.after_request
    def secure(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", version="1.0.0")

    @app.get("/api/sample")
    def demo():
        return jsonify(sample())

    @app.post("/api/validate")
    def import_catalog():
        return jsonify(validate(request.get_json()))

    @app.post("/api/extract")
    def extract_catalog():
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError("연결 정보가 필요합니다.")
        if body.get("source") == "postgresql":
            if not isinstance(body.get("dsn"), str) or not body["dsn"].strip():
                raise ValueError("PostgreSQL 접속 문자열을 입력하세요.")
            schemas = body.get("schemas", ["public"])
            if not isinstance(schemas, list) or not schemas or any(not isinstance(s, str) or not s for s in schemas):
                raise ValueError("스키마 목록을 입력하세요.")
            try:
                return jsonify(postgres(body["dsn"], schemas))
            except Exception:
                # Driver errors can echo user-supplied connection strings.
                return jsonify(error="PostgreSQL 연결·추출 실패. 서버 주소, 읽기 권한, 인증서와 접속 정보를 확인하세요."), 502
        if body.get("source") == "bigquery":
            try:
                return jsonify(bigquery(body.get("project"), body.get("dataset")))
            except Exception:
                return jsonify(error="BigQuery 연결·추출 실패. ADC 인증, 프로젝트·데이터셋, 메타데이터 읽기 권한과 네트워크를 확인하세요."), 502
        raise ValueError("지원하지 않는 데이터 소스입니다.")

    @app.post("/api/export/<kind>")
    def download(kind):
        payload = export(request.get_json(), kind)
        types = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 "json": "application/json", "svg": "image/svg+xml", "mmd": "text/plain"}
        return send_file(BytesIO(payload), mimetype=types[kind], as_attachment=True, download_name=f"auto-dd.{kind}")

    @app.post("/api/ai")
    def ai():
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError("카탈로그와 모델 이름을 입력하세요.")
        data = validate(body.get("catalog"))
        try:
            return jsonify(describe(data, body.get("model", "qwen2.5:7b")))
        except Exception:
            return jsonify(error="로컬 Ollama 설명 생성 실패. 127.0.0.1:11434 서버와 미리 설치한 모델을 확인하세요. 기존 카탈로그는 유지됩니다."), 502

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify(error="요청 JSON 형식이 올바르지 않습니다."), 400

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="파일이 너무 큽니다. 최대 16MB입니다."), 413

    return app
