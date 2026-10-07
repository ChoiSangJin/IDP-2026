# 운영 및 배포 가이드

## PostgreSQL

UI 연결창의 예시:

```text
host=db.internal port=5432 dbname=warehouse user=catalog_reader sslmode=verify-full sslrootcert=/path/to/company-ca.pem
```

비밀번호는 필요할 때 연결창에 입력하거나 PostgreSQL이 지원하는 `.pgpass`/`PGPASSFILE`을 사용합니다. 파일 권한을 제한하세요. 접속 문자열은 앱 파일이나 로그에 저장하지 않습니다. 원격 연결에서 TLS 검증을 유지하고 사내 CA를 지정하세요. 기본값의 libpq TLS 설정은 조직 정책에 맞게 직접 지정해야 합니다.

CLI는 `AUTO_DD_PG_DSN`을 사용합니다. 비밀번호를 명령행 인자로 전달하지 않습니다.

```bash
auto-dd export --source postgresql --schemas public,analytics --format json --output catalog.json
```

추출은 `REPEATABLE READ READ ONLY` 트랜잭션과 30초 SQL 제한을 사용합니다. 사용자 행은 SELECT하지 않습니다. 읽기 계정은 대상 스키마·객체 메타데이터를 볼 수 있어야 합니다. 500개 테이블/테이블당 2000컬럼 제한이 있으므로 큰 DB는 스키마 단위로 나눠 추출하세요. 특수 권한/RLS에 따른 보이는 메타데이터의 범위는 DB 정책을 따릅니다.

## BigQuery

기기에서 Google의 Application Default Credentials를 구성합니다 (`gcloud auth application-default login` 또는 조직에서 제공한 서비스 계정/워크로드 인증). 서비스 계정 파일 사용 시 `GOOGLE_APPLICATION_CREDENTIALS`에 로컬 경로를 지정합니다. 앱이 이 파일을 수집하거나 카탈로그에 포함하지 않습니다. 대상 데이터셋의 `bigquery.tables.list/get` 권한(예: `roles/bigquery.metadataViewer`)과 조직 인증 정책을 확인하세요. UI에 키를 업로드할 필요가 없습니다.

```bash
auto-dd export --source bigquery --project my-project --dataset warehouse --format xlsx --output specification.xlsx
```

Google API 및 해당 인증 경로의 네트워크 접근이 필요합니다. 완전 폐쇄망에서는 추출한 JSON을 반입해 조회·편집·ERD·문서 생성을 사용하세요. 실제 BigQuery 접속은 사용자의 계정/데이터셋이 있을 때 별도 확인해야 합니다.

## 로컬 AI

기기에 Ollama를 설치하고 모델을 준비한 후 Ollama 서버를 시작합니다. 예를 들어 `qwen2.5:7b` 모델을 미리 설치하고 UI의 `로컬 AI 설명 제안`을 실행합니다. 앱은 HTTP `127.0.0.1:11434/api/generate`만 사용하고, 프록시를 거치지 않습니다. 테이블을 순차 처리하며 요청당 120초 제한이 있습니다. 모델이 없거나 실패하면 현재 카탈로그를 유지합니다. 추론 결과는 정확성을 검토하세요. 자체 모델 다운로드·런타임 설치는 선택 기능에 포함되지 않습니다.

## 폐쇄망 소스 설치

반입 대상과 동일한 OS·CPU·Python 버전의 연결 가능한 기기에서:

```bash
python -m pip download -r requirements.lock -d wheelhouse
```

프로젝트 소스와 wheelhouse를 안전한 경로로 반입한 후:

```bash
python -m pip install --no-index --find-links wheelhouse -r requirements.lock
python -m pip install --no-build-isolation --no-deps -e .
python -m auto_dd
```

패키지 검증을 비활성화하지 않고 신뢰하는 반입 경로와 조직의 파일 검증 절차를 사용하세요. 재현 가능한 설치를 위해 `requirements.lock`에 검증한 버전을 고정했습니다. PyInstaller는 각 OS에서 직접 빌드합니다.

## 로컬 서비스 범위

앱은 loopback에만 바인딩하고 실행마다 새 접근 토큰을 생성합니다. 토큰은 실행 URL의 fragment에 포함되고 브라우저 sessionStorage에 유지됩니다. API는 이 토큰과 Origin/Host를 검사합니다. 원격 바인딩, 공용 웹 배포, 다중 사용자 로그인은 현재 제공하지 않습니다. 사내 서버의 다중 사용자 카탈로그는 계획서의 선택 확장 항목이며 별도 인증·권한·저장소 설계가 필요합니다.

카탈로그와 내보낸 파일에는 스키마 이름, 테이블/컬럼 설명 등 내부 메타데이터가 들어갑니다. 대상 기기의 접근 제어와 조직의 문서 관리 정책에 따라 보관하세요. 인터넷에 메타데이터를 자동 업로드하는 기능은 없습니다.
