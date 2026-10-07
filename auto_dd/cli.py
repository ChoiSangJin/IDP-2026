import argparse
import os
from pathlib import Path
import sys
import threading
import webbrowser
from werkzeug.serving import make_server
from .model import load
from .sample import sample
from .extract import postgres, bigquery
from .export import export


def main(argv=None):
    # Frozen Python ignores PYTHONUTF8; Windows redirected logs must still handle Korean.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Auto-DD — 로컬 DB 명세 · 카탈로그 · ERD")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="로컬 UI 실행 (기본 동작)")
    serve.add_argument("--port", type=int, default=8765, help="0: 사용 가능한 포트 자동 선택")
    serve.add_argument("--no-browser", action="store_true")
    generate = commands.add_parser("export", help="명세/ERD 내보내기")
    generate.add_argument("--source", choices=["json", "sample", "postgresql", "bigquery"], default="json")
    generate.add_argument("--input", help="카탈로그 JSON 경로")
    generate.add_argument("--schemas", default="public")
    generate.add_argument("--project")
    generate.add_argument("--dataset")
    generate.add_argument("--format", choices=["xlsx", "json", "svg", "mmd"], required=True)
    generate.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command in (None, "serve"):
        from .web import create_app
        app = create_app()
        port = getattr(args, "port", 8765)
        try:
            server = make_server("127.0.0.1", port, app, threaded=True)
        except SystemExit:
            print("포트가 사용 중입니다. serve --port 0 을 사용하세요.", file=sys.stderr)
            return 1
        url = f"http://127.0.0.1:{server.server_port}/#token={app.config['TOKEN']}"
        print("Auto-DD 실행 주소: "+url, flush=True)
        if not getattr(args, "no_browser", False):
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    try:
        if args.source == "sample":
            data = sample()
        elif args.source == "json":
            if not args.input:
                parser.error("--input이 필요합니다.")
            data = load(args.input)
        elif args.source == "postgresql":
            if not os.environ.get("AUTO_DD_PG_DSN"):
                parser.error("AUTO_DD_PG_DSN 환경변수가 필요합니다 (비밀번호를 인자로 전달하지 마세요).")
            data = postgres(os.environ["AUTO_DD_PG_DSN"], args.schemas.split(","))
        else:
            data = bigquery(args.project, args.dataset)
        Path(args.output).write_bytes(export(data, args.format))
        print(f"{len(data['tables'])}개 테이블 → {args.output}")
        return 0
    except Exception:
        print("명세 생성 실패. 입력 형식, DB 읽기 권한·인증·연결 및 출력 경로를 확인하세요.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
