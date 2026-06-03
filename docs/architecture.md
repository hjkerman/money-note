# 아키텍처

`money-note`는 기존 Excel 가계부의 운용 방식을 유지하면서, 당월 기록을 웹과 향후 앱에서 조작하기 위한 개인 가계부 시스템이다.

## 기본 원칙

- 서버 DB를 원본 데이터로 사용한다.
- Excel 파일은 초기 import와 필요할 때 만드는 snapshot export로 취급한다.
- 공개 공유 화면은 청구/타인정산 읽기 전용만 제공한다.
- 공개 화면에는 계좌번호, 송금 링크, 개인정보를 넣지 않는다.
- 유머와 평가는 `judgment` 모듈에 모아둔다.

## 구성

- 백엔드: FastAPI + SQLite
- Excel 처리: openpyxl
- 프론트엔드: Vite + React + TypeScript
- 배포: Docker Compose
- 향후 macOS 앱: 웹 UI를 Tauri로 wrapping
- 향후 모바일 앱: Android 중심으로 별도 검토

## 데이터 흐름

1. Excel 파일을 `scripts/import_xlsx.py`로 DB에 import한다.
2. 웹 앱은 API를 통해 DB를 조회/수정한다.
3. 추가/삭제/확인 같은 조작은 즉시 서버에 저장된다.
4. 분류 변경은 화면에 pending 상태로 모였다가 `변경 사항 저장` 버튼을 눌러 서버에 저장된다.
5. 필요하면 `/api/export`로 DB 내용을 Excel snapshot으로 export한다.

## 주요 화면 구조

- `요약 / 인사이트`: 카드대금, 송금/예치, 동결자산, 유동성 등 계산값
- `당월`: 당월 지출, 청구, 타인정산, 할부
- `고정지출`: 현금성 고정지출과 카드 정기결제
- `동결`: 사지 말지 보류한 항목. 확인 시 당월 기록 편입 가능
- `현금흐름`: 현금 입출금 기록
- `통계 보기`: 소비 통계와 월별 기록을 함께 표시

## 판단 모듈

프론트 판단 모듈은 `frontend/src/judgment.ts`다.

담당:

- 당월 지출 분류 라벨
- 청구 자동 분류
- 소비 통계 문구
- 가족카드 한도 감시 문구

백엔드 판단 모듈은 `backend/app/services/judgment.py`다.

담당:

- 청구 공유 화면 상단 문구
- 타인정산 공유 화면 상단 문구
- 어머니께 보이는 청구 공유 화면의 가계부 한 줄 평가

자세한 설명은 `frontend/src/judgment.README.md`를 본다.

## Excel 호환

당월 지출은 앱에서 `사용처`와 `사용항목`으로 나눠 입력할 수 있다.
DB에는 두 필드를 보존하고, `title`에는 기존 Excel 호환 형식인 `[사용처] 사용항목`을 저장한다.
Excel export는 기존처럼 `title`을 `당월 기록!C`에 기록한다.

## 월마감

월마감은 `current`의 일반 지출을 `archive`로 복사하고 current에서 삭제한다.
카드 정기결제와 같은 planned 항목은 current에 남는다.
할부 항목은 월마감 때 잔여 개월이 1씩 줄고, 0이 되면 비활성화된다.
