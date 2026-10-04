# Owner-approved recurring canonicalization

자동 호환은 계속 immutable proof-only다. Timestamp/content/금액/발생일/위치 또는 유일 후보로 source/epoch를 추측하지 않는다. 아래는 **별도 one-time offline 운영 도구**의 계약이며 배포나 live DB 적용 허가가 아니다.

소유자가 검토한 R01–R11은 YES 11 / NO 0 / UNSURE 0이다. Human attestation은 정확히 승인된 source ID → child ID/payment key/location/confirmation epoch 매핑의 근거다. 이를 일반적인 자동 matching rule로 확대하지 않는다. 실제 매핑·금융 기준값·fingerprint는 비공개 운영 manifest에만 있고 Git에는 합성 테스트만 둔다.

## 적용 범위

`scripts/canonicalize-recurring.py`는 기존 current 구조의 DB version 3/4만 받는다. Source FK가 이미 명시적으로 일치하는 expense의 **모두 NULL인 child `confirmed_month`, `confirmed_at` 두 열만** 채운다. Source ID 자체 누락, 부분 epoch, 기존 epoch 덮어쓰기는 지원하지 않는다. Planned source의 확인/날짜, principal, auxiliary/0원 override, content, payment key, current/archive 위치, 결제·현금흐름·설정은 수정하지 않는다. 기존 revision trigger의 UPDATE당 한 번 증가만 별도 allowlist에 포함한다. `user_version`은 도구가 변경하지 않고 이후 정상 startup이 기존 version 4 checkpoint를 수행한다.

Closed historical epoch는 child에만 기록한다. 9월 archive가 10월 source 확인을 대체하거나 reset source의 현행 reserve를 소비하지 않는다. 같은 source의 다른 월은 별개 epoch이며 한 source/month 또는 child/key를 중복 승인할 수 없다. 이미 지급된 archive 삭제 금지 등 정상 금융 lifecycle 규칙도 그대로다.

## Manifest와 검토 경계

로컬 JSON은 `format_version=1`, `purpose=owner-approved-recurring-canonicalization`이다.

- `mappings`: `review_id`, `source_planned_id`, `child_location`, `child_id`, `stable_key`, `confirmed_month`, `confirmed_at`, `owner_decision=YES`의 명시적 목록만.
- `approved_review_ids`, `approved_mappings_sha256`: 승인된 목록의 정확한 집합과 digest.
- `review_fingerprint`: 해당 source/child와 competing sibling/key의 **전체 행** guard. 같은 key의 NULL-source도 버리지 않는다. Content/금액 포함은 stale-review 검사이지 ownership 추론이 아니다.
- `state_fingerprint`: schema, 모든 persistent table, sequence, revision, user_version의 결정적 전체 상태 digest. 보수적인 guard 때문에 금융과 무관한 DB 변경도 새 manifest 검토를 요구할 수 있다.
- `as_of_date`, `financial_baseline`: 검토한 authoritative Summary 기준값. 비교 날짜는 실행 시 앱의 실제 오늘과 같아야 한다. 날짜가 지나도 같은 오래된 기준으로 apply할 수 없다.

`build_manifest(connection, explicit_mappings, date, reviewed_summary)`는 이미 승인한 입력에 guard만 묶고 목록을 늘리지 않는다. Operator는 파일 **외부에서 확인한 SHA-256**을 `--approved-manifest-sha256`으로 pin한다. Manifest를 바꾼 뒤 임의로 hash만 다시 계산하는 것은 owner approval이 아니다. Digest는 변경 검출이지 소유자 인증/signature 시스템이 아니므로 파일·승인 채널·운영 권한을 함께 보호한다.

Epoch-less 원본은 current strict Summary가 의도적으로 거부한다. Validator를 끄거나 가상 결과를 원본 계산처럼 취급하지 않는다. 이 경우 같은 원본 fingerprint와 날짜에 대응하는 보존된 authoritative 계산 또는 검증된 당시 런타임의 **새 COPY에서의 read-only 계산**을 baseline으로 검토한다. Provenance를 별도 운영 증거로 보존한다. 도구는 canonicalized 결과를 현재 strict Summary/current v7 exporter로 검사하고 모든 named metric을 baseline과 정확히 비교한다. Raw principal/discount/burden/cash/payment component도 별도로 전후 비교하고 모든 persistent field diff를 검사한다. 신뢰할 수 있는 기준값이 없으면 적용하지 않는다.

## 필수 backup → dry-run → apply

향후 별도 승인된 maintenance window에서 application writes가 race하지 않도록 보호한다. 이번 개발 tranche는 live 운영에 적용하지 않는다.

1. Fresh SQLite **Online Backup**을 별도 파일로 만들고 integrity_check=ok, foreign_key_check=0, SHA-256와 backup manifest를 검증한다. Backup은 standalone/quiescent여야 한다. 오래된 검토용 사본을 fresh live backup이라고 주장하지 않는다.
2. 그 fresh backup의 새 COPY에서 관계가 여전히 승인한 행인지 검토한다. Full-state/relationship fingerprint 또는 날짜가 바뀌면 새 manifest/financial baseline/외부 approval digest를 검토한다. 변경된 관계는 owner 재검토 대상이다.
3. 아래 dry-run을 실행한다. `--apply`가 없으면 commit하지 않는다. 도구는 target을 read-only로 열어 일관된 Online Backup을 메모리에 만들고 모두 적용/검증 후 **ROLLBACK**한다. Target byte/logical 상태는 불변이다.

```sh
.venv/bin/python scripts/canonicalize-recurring.py \
  --db /private/copy.sqlite3 --manifest /private/approved.json \
  --approved-manifest-sha256 APPROVED_SHA256 \
  --verified-backup /private/fresh-online-backup.sqlite3 --backup-sha256 BACKUP_SHA256 \
  --dry-run --report /private/dry-run.json
```

4. Named 금융 차이/raw component 차이가 모두 **0원**, metadata allowlist 외 변경 없음, canonical Snapshot 검증 통과를 독립 검토한다. Receipt SHA-256도 pin한다. Historical COPY 실험만 보존된 날짜의 `MONEY_NOTE_TODAY`를 사용할 수 있고 향후 live 작업에서는 달력을 위조하지 않는다.
5. 별도 live 실행 승인 이후에만 같은 manifest/fresh backup/receipt로 `--apply --dry-run-receipt ... --receipt-sha256 ...`를 사용한다. BEGIN IMMEDIATE 안에서 backup logical state와 모든 guard를 다시 검사한다. 모든 매핑과 strict graph/money/Summary/export/field-diff 검증을 **단일 transaction**에서 끝낸 뒤 commit한다. 하나 실패하면 전부 rollback한다. CLI report는 새 파일만 0600으로 생성해 기존 artifact를 덮어쓰지 않는다.
6. 정상 startup→반복 startup→Summary→새 canonical v7 export→isolated restore/restart를 검증한다. Backup 정책에 따라 새 canonical recovery Snapshot을 새 baseline으로 보존한다. **옛 23개 recovery Snapshot은 재작성하지 않는다.**

Receipt는 manifest/backup/before-state/after-state/정확한 changed rows와 금융 차이를 모두 bind한다. Apply에서도 재계산하므로 receipt가 validator를 대신하지 않는다. 운영 파일들은 비공개로 보존하고 일반 로그에 원본 거래 내역을 출력하지 않는다.

## 실패·재실행

같은 manifest 재적용은 changed fingerprint 또는 이미 채워진 epoch로 **거부/무변경**한다. 새로운 identity나 financial write를 만들지 않는다. 중단 시 원본 또는 전부 canonicalized 상태만 durable하다. Report filesystem/transport 실패는 commit 후 발생할 수도 있으므로 `operation not confirmed`를 rollback 보장으로 읽지 않는다. DB/manifest/report를 확인하고 새 manifest나 재시도를 자동 생성하지 않는다.

Live 신규 입력, 미승인 유사 행, partial/malformed 관계를 일반적으로 복구하지 않는다. Automatic startup/restore proof는 unchanged이며 manifest 없이는 기존 11개 epoch-less 관계가 계속 거부된다. 사본의 0원 검증은 production 배포 준비 판정이 아니다.
