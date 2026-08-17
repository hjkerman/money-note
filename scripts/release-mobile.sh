#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${MONEY_NOTE_DEPLOY_ENV:-$ROOT_DIR/.env.deploy}"
APK_PATH="$ROOT_DIR/mobile/build/app/outputs/flutter-apk/app-release.apk"

die() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/release-mobile.sh

Builds, verifies, and atomically deploys the signed Money-Note release APK.
Configuration is read from .env.deploy by default. Set MONEY_NOTE_DEPLOY_ENV
to use a different file.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
[[ $# -eq 0 ]] || die "지원하지 않는 인자입니다. --help를 확인하세요."

[[ -f "$ENV_FILE" ]] || die "$ENV_FILE 파일이 없습니다. .env.deploy.example을 복사해 설정하세요."
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${MONEY_NOTE_API_BASE_URL:?MONEY_NOTE_API_BASE_URL is required}"
: "${MONEY_NOTE_DEPLOY_HOST:?MONEY_NOTE_DEPLOY_HOST is required}"
: "${MONEY_NOTE_DEPLOY_USER:?MONEY_NOTE_DEPLOY_USER is required}"
: "${MONEY_NOTE_DEPLOY_REMOTE_APK_PATH:?MONEY_NOTE_DEPLOY_REMOTE_APK_PATH is required}"
MONEY_NOTE_DEPLOY_PORT="${MONEY_NOTE_DEPLOY_PORT:-32619}"
MONEY_NOTE_DEPLOY_BRANCH="${MONEY_NOTE_DEPLOY_BRANCH:-main}"
MONEY_NOTE_DEPLOY_IDENTITY_FILE="${MONEY_NOTE_DEPLOY_IDENTITY_FILE:-}"

[[ "$MONEY_NOTE_API_BASE_URL" == https://* ]] || die "release API 주소는 https://여야 합니다."
[[ "$MONEY_NOTE_DEPLOY_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || die "배포 호스트 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_USER" =~ ^[A-Za-z0-9._-]+$ ]] || die "배포 사용자 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_PORT" =~ ^[0-9]+$ ]] || die "SSH 포트는 숫자여야 합니다."
[[ "$MONEY_NOTE_DEPLOY_BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || die "배포 브랜치 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_REMOTE_APK_PATH" =~ ^/[A-Za-z0-9._/-]+$ ]] || die "원격 APK 경로는 공백 없는 절대경로여야 합니다."
if [[ -n "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]]; then
  [[ -f "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]] || die "SSH identity file을 찾을 수 없습니다: $MONEY_NOTE_DEPLOY_IDENTITY_FILE"
fi

for command_name in git flutter scp ssh; do
  command -v "$command_name" >/dev/null 2>&1 || die "$command_name 명령을 찾을 수 없습니다."
done
if command -v shasum >/dev/null 2>&1; then
  sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }
elif command -v sha256sum >/dev/null 2>&1; then
  sha256_file() { sha256sum "$1" | awk '{print $1}'; }
else
  die "SHA-256 계산 명령을 찾을 수 없습니다."
fi

cd "$ROOT_DIR"
[[ -z "$(git status --porcelain)" ]] || die "작업 트리가 깨끗하지 않습니다. 커밋 후 배포하세요."
current_branch="$(git branch --show-current)"
[[ "$current_branch" == "$MONEY_NOTE_DEPLOY_BRANCH" ]] || die "현재 브랜치가 $MONEY_NOTE_DEPLOY_BRANCH 이 아닙니다: $current_branch"
git fetch --quiet origin "$MONEY_NOTE_DEPLOY_BRANCH"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse "origin/$MONEY_NOTE_DEPLOY_BRANCH")" ]] \
  || die "현재 커밋이 origin/$MONEY_NOTE_DEPLOY_BRANCH 에 push되지 않았습니다."

version="$(awk '$1 == "version:" { print $2; exit }' mobile/pubspec.yaml)"
[[ -n "$version" ]] || die "mobile/pubspec.yaml에서 앱 버전을 읽지 못했습니다."
printf 'Money-Note %s release 검증을 시작합니다.\n' "$version"

(
  cd mobile
  flutter clean
  flutter pub get
  flutter analyze
  flutter test
  flutter build apk --release \
    --dart-define="MONEY_NOTE_API_BASE_URL=$MONEY_NOTE_API_BASE_URL"
)

[[ -s "$APK_PATH" ]] || die "release APK가 생성되지 않았습니다: $APK_PATH"
local_sha="$(sha256_file "$APK_PATH")"
remote_dir="${MONEY_NOTE_DEPLOY_REMOTE_APK_PATH%/*}"
remote_temp="${MONEY_NOTE_DEPLOY_REMOTE_APK_PATH}.uploading.$(date -u +%Y%m%dT%H%M%SZ).$$"
target="${MONEY_NOTE_DEPLOY_USER}@${MONEY_NOTE_DEPLOY_HOST}"
control_path="${TMPDIR:-/tmp}/mn-deploy-$$-%C"

common_options=(
  -o "ControlMaster=auto"
  -o "ControlPersist=60"
  -o "ControlPath=$control_path"
)
ssh_command=(ssh -p "$MONEY_NOTE_DEPLOY_PORT" "${common_options[@]}")
scp_command=(scp -P "$MONEY_NOTE_DEPLOY_PORT" "${common_options[@]}")
if [[ -n "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]]; then
  ssh_command+=(-i "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" -o IdentitiesOnly=yes)
  scp_command+=(-i "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" -o IdentitiesOnly=yes)
fi

uploaded=0
cleanup() {
  status=$?
  trap - EXIT
  if [[ $status -ne 0 && $uploaded -eq 1 ]]; then
    "${ssh_command[@]}" "$target" "rm -f -- '$remote_temp'" >/dev/null 2>&1 || true
  fi
  "${ssh_command[@]}" -O exit "$target" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

"${ssh_command[@]}" "$target" "test -d '$remote_dir' && test -w '$remote_dir'" \
  || die "원격 APK 디렉터리가 없거나 쓸 수 없습니다: $remote_dir"

printf 'APK를 임시 경로로 전송합니다.\n'
"${scp_command[@]}" "$APK_PATH" "$target:$remote_temp"
uploaded=1

remote_sha="$("${ssh_command[@]}" "$target" "sha256sum '$remote_temp' | awk '{print \$1}'")"
if [[ "$local_sha" != "$remote_sha" ]]; then
  die "업로드한 APK의 SHA-256이 로컬 파일과 일치하지 않습니다."
fi

"${ssh_command[@]}" "$target" \
  "chmod 0644 '$remote_temp' && mv -f '$remote_temp' '$MONEY_NOTE_DEPLOY_REMOTE_APK_PATH'"
uploaded=0

printf '배포 완료: Money-Note %s\n' "$version"
printf '원격 경로: %s\n' "$MONEY_NOTE_DEPLOY_REMOTE_APK_PATH"
printf 'SHA-256: %s\n' "$local_sha"
