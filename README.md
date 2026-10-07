# Auto-DD

로컬 실행 기반 **DB 명세 자동화 · 데이터 카탈로그 · ERD 스튜디오**.
2026 IDP 계획서의 PostgreSQL/BigQuery 메타데이터 추출, Excel/JSON 명세 생성, 실행 파일 패키징과 로컬 AI 설명 제안을 구현합니다.

## 바로 실행

[GitHub Releases](https://github.com/ChoiSangJin/IDP-2026/releases)에서 운영체제에 맞는 실행 파일을 다운로드합니다.

- Windows: `Auto-DD.exe` 실행. 로컬 브라우저 창이 열립니다. 종료는 콘솔에서 `Ctrl+C`.
- Linux x86_64: `tar -xzf Auto-DD-linux-x86_64.tar.gz`, `./Auto-DD`.
- `Auto-DD.exe serve --port 0`으로 사용 가능한 포트를 자동 선택합니다.
- 브라우저가 열리지 않으면 콘솔에 출력된 실행 주소를 해당 기기의 브라우저에 입력합니다.
- 체크섬은 Release의 `SHA256SUMS`와 비교합니다 (`Get-FileHash` 또는 `sha256sum`).

인터넷 없이 직접 테이블을 만들고, JSON을 열고, Excel/JSON/SVG/Mermaid를 내보낼 수 있습니다. UI에 외부 CDN·폰트·분석 도구가 없습니다. 앱은 외부 서버가 아닌 **이 기기의 `127.0.0.1`에서만** 실행됩니다. 여러 사용자가 공유하는 서버용 서비스는 아닙니다.

## 주요 기능

| 기능 | 동작 |
|---|---|
| PostgreSQL | 테이블·뷰·물리화 뷰, 순서대로 컬럼, 타입, NULL, 기본값, 코멘트, 복합 PK/FK 추출 |
| BigQuery | 테이블·뷰 메타데이터, 중첩 RECORD, REPEATED 타입, 설명, 선언된 PK/FK 추출 |
| 카탈로그 | 이름·컬럼·설명 검색, 테이블/컬럼/설명/기본값 편집 |
| 명세 | Excel의 Tables/Columns/Relationships 시트, 편집 가능한 JSON |
| ERD | 테이블 드래그·방향키 이동, 관계 추가·삭제, 자동 배치, SVG·Mermaid 내보내기 |
| 로컬 AI | 기기의 Ollama로 빈 설명만 제안. 기존 설명 유지. 실제 행 데이터는 읽거나 보내지 않음 |
| CLI | JSON/샘플/DB에서 명세·관계도 생성. 배치 작업에 사용 |

ERD/카탈로그 편집은 원본 DB를 수정하지 않습니다. **편집 내용은 메모리에만 유지되므로 종료 전에 JSON으로 내보내세요.** JSON을 다시 가져오면 관계와 배치도 복원됩니다. 추출 범위 밖의 테이블에 대한 FK는 명세에는 남고, ERD에는 대상 미포함으로 표시됩니다. Mermaid 관계는 일반적인 FK 표현이며 nullable/unique에 따른 정확한 카디널리티 추론은 제공하지 않습니다.

## 소스에서 개발

Python 3.11 이상 (검증/CI: 3.12).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m auto_dd
```

UI에서 `예제 열기`로 전체 흐름을 즉시 확인할 수 있습니다. `examples/catalog.json`도 포함됩니다.

```bash
auto-dd export --source sample --format xlsx --output specification.xlsx
auto-dd export --input examples/catalog.json --format svg --output erd.svg
auto-dd export --input examples/catalog.json --format mmd --output erd.mmd
auto-dd serve --no-browser --port 8765
```

## 온프레미스 · 폐쇄망

대상 OS에서 빌드한 실행 파일을 반입하면 Python 설치 없이 사용할 수 있습니다. Linux 빌드는 glibc 버전 호환성이 필요하며, 오래된 배포판은 해당 배포판에서 직접 빌드하세요. 소스 배포용 오프라인 wheelhouse 준비법과 DB 인증 설정은 [운영 가이드](docs/OPERATIONS.md)를 확인하세요.

- PostgreSQL은 로컬/내부 DB까지 네트워크 경로와 메타데이터 읽기 권한이 필요합니다.
- BigQuery는 Google 서비스이므로 완전 폐쇄망에서 직접 연결할 수 없습니다. 연결 가능한 기기에서 JSON을 추출해 폐쇄망에 반입할 수 있습니다.
- AI는 선택 기능입니다. Ollama와 모델을 인터넷이 가능한 환경에서 미리 준비해 반입하세요. 앱이 모델을 다운로드하지 않습니다.

## 테스트와 실행 파일 빌드

```bash
python -m pytest -q
python scripts/build.py
# Windows: python scripts/smoke_binary.py dist/Auto-DD.exe
python scripts/smoke_binary.py dist/Auto-DD
```

실제 PostgreSQL 통합 테스트는 테스트 전용 DB에 `AUTO_DD_TEST_PG_DSN`을 설정합니다. 테스트는 `auto_dd_test` 스키마를 만들고 삭제합니다. 운영 DB에 실행하지 마세요. 미설정 시 해당 테스트만 skipped로 표시됩니다. CI는 PostgreSQL 17 컨테이너에서 이 검증을 수행하며 Windows/Linux 실행 파일을 각각 빌드하고 내보내기까지 확인합니다.

`v*` 태그의 CI가 모두 통과하면 GitHub Release에 두 실행 파일과 SHA-256 체크섬이 게시됩니다. Windows EXE는 Windows CI에서만 생성되며 Linux 파일을 EXE로 이름만 바꾸지 않습니다.
