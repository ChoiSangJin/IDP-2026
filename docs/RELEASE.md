Auto-DD 1.0.0 — 로컬 DB 명세 자동화 및 ERD 스튜디오

- PostgreSQL/BigQuery 메타데이터 수집 및 Excel/JSON 명세서 생성
- 카탈로그 검색 및 테이블·컬럼·설명 편집
- ERD 배치, 복합 외래키 편집, SVG/Mermaid 내보내기
- 로컬 Ollama 기반 빈 설명 제안 (모델 별도 설치)
- Windows EXE / Linux 실행 파일. 로컬 기기에서 실행, 외부 CDN 없음

Windows: Auto-DD.exe 실행. Linux: tar -xzf Auto-DD-linux-x86_64.tar.gz 후 ./Auto-DD 실행.
편집 결과는 종료 전에 JSON으로 저장하세요. 원본 DB는 수정하지 않습니다.

PostgreSQL은 접근 가능한 DB와 읽기 계정이 필요합니다. BigQuery는 ADC 및 Google API 연결이 필요하며 완전 폐쇄망에서는 추출된 JSON을 반입해 사용하세요. SHA256SUMS로 다운로드 파일을 검증할 수 있습니다.
