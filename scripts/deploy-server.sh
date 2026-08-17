#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${MONEY_NOTE_DEPLOY_ENV:-$ROOT_DIR/.env.deploy}"
FORCE=0

die() {
  printf '오류: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy-server.sh [--force]

Pulls the configured branch on the server, rebuilds changed backend/frontend
areas, deploys the web dist, and verifies API health. --force rebuilds both
areas even when the recorded deployed commit has no relevant changes.
Configuration is read from .env.deploy by default. Set MONEY_NOTE_DEPLOY_ENV
to use a different file.
EOF
}

case "${1:-}" in
  "") ;;
  --force) FORCE=1 ;;
  --help|-h)
    usage
    exit 0
    ;;
  *) die "지원하지 않는 인자입니다. --help를 확인하세요." ;;
esac
[[ $# -le 1 ]] || die "지원하지 않는 인자입니다. --help를 확인하세요."

[[ -f "$ENV_FILE" ]] || die "$ENV_FILE 파일이 없습니다. .env.deploy.example을 복사해 설정하세요."
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${MONEY_NOTE_DEPLOY_HOST:?MONEY_NOTE_DEPLOY_HOST is required}"
: "${MONEY_NOTE_DEPLOY_USER:?MONEY_NOTE_DEPLOY_USER is required}"
MONEY_NOTE_DEPLOY_PORT="${MONEY_NOTE_DEPLOY_PORT:-32619}"
MONEY_NOTE_DEPLOY_BRANCH="${MONEY_NOTE_DEPLOY_BRANCH:-main}"
MONEY_NOTE_DEPLOY_REPO_PATH="${MONEY_NOTE_DEPLOY_REPO_PATH:-/opt/money-note}"
MONEY_NOTE_DEPLOY_WEB_ROOT="${MONEY_NOTE_DEPLOY_WEB_ROOT:-/var/www/money}"
MONEY_NOTE_DEPLOY_IDENTITY_FILE="${MONEY_NOTE_DEPLOY_IDENTITY_FILE:-}"

[[ "$MONEY_NOTE_DEPLOY_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || die "배포 호스트 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_USER" =~ ^[A-Za-z0-9._-]+$ ]] || die "배포 사용자 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_PORT" =~ ^[0-9]+$ ]] || die "SSH 포트는 숫자여야 합니다."
[[ "$MONEY_NOTE_DEPLOY_BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || die "배포 브랜치 형식이 올바르지 않습니다."
[[ "$MONEY_NOTE_DEPLOY_REPO_PATH" =~ ^/[A-Za-z0-9._/-]+$ ]] || die "서버 repo 경로는 공백 없는 절대경로여야 합니다."
[[ "$MONEY_NOTE_DEPLOY_WEB_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]] || die "웹 루트는 공백 없는 절대경로여야 합니다."
if [[ -n "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]]; then
  [[ -f "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]] || die "SSH identity file을 찾을 수 없습니다: $MONEY_NOTE_DEPLOY_IDENTITY_FILE"
fi

for command_name in git ssh; do
  command -v "$command_name" >/dev/null 2>&1 || die "$command_name 명령을 찾을 수 없습니다."
done

cd "$ROOT_DIR"
[[ -z "$(git status --porcelain)" ]] || die "작업 트리가 깨끗하지 않습니다. 커밋 후 배포하세요."
current_branch="$(git branch --show-current)"
[[ "$current_branch" == "$MONEY_NOTE_DEPLOY_BRANCH" ]] || die "현재 브랜치가 $MONEY_NOTE_DEPLOY_BRANCH 이 아닙니다: $current_branch"
git fetch --quiet origin "$MONEY_NOTE_DEPLOY_BRANCH"
local_head="$(git rev-parse HEAD)"
remote_head="$(git rev-parse "origin/$MONEY_NOTE_DEPLOY_BRANCH")"
[[ "$local_head" == "$remote_head" ]] || die "현재 커밋이 origin/$MONEY_NOTE_DEPLOY_BRANCH 에 push되지 않았습니다."

target="${MONEY_NOTE_DEPLOY_USER}@${MONEY_NOTE_DEPLOY_HOST}"
control_path="/tmp/mn-s-$$-%C"
ssh_command=(
  ssh
  -p "$MONEY_NOTE_DEPLOY_PORT"
  -o "ControlMaster=auto"
  -o "ControlPersist=60"
  -o "ControlPath=$control_path"
)
if [[ -n "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" ]]; then
  ssh_command+=(-i "$MONEY_NOTE_DEPLOY_IDENTITY_FILE" -o IdentitiesOnly=yes)
fi

cleanup() {
  status=$?
  trap - EXIT
  "${ssh_command[@]}" -O exit "$target" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

printf '서버 배포를 시작합니다: %s (%s)\n' "$target" "${local_head:0:12}"
"${ssh_command[@]}" "$target" bash -s -- \
  "$MONEY_NOTE_DEPLOY_REPO_PATH" \
  "$MONEY_NOTE_DEPLOY_WEB_ROOT" \
  "$MONEY_NOTE_DEPLOY_BRANCH" \
  "$FORCE" <<'REMOTE_SCRIPT'
set -euo pipefail

repo_path="$1"
web_root="$2"
branch="$3"
force="$4"
deployed_ref="$repo_path/.git/money-note-deployed-commit"

cd "$repo_path"
[[ -z "$(git status --porcelain)" ]] || {
  printf '오류: 서버 작업 트리에 로컬 변경이 있습니다. 배포를 중단합니다.\n' >&2
  git status --short >&2
  exit 1
}
[[ "$(git branch --show-current)" == "$branch" ]] || {
  printf '오류: 서버의 현재 브랜치가 %s가 아닙니다.\n' "$branch" >&2
  exit 1
}

git fetch --quiet origin "$branch"
git merge --ff-only "origin/$branch"
new_head="$(git rev-parse HEAD)"
old_deployed=""
if [[ -f "$deployed_ref" ]]; then
  old_deployed="$(tr -d '[:space:]' < "$deployed_ref")"
fi

backend_changed=0
frontend_changed=0
if [[ "$force" == "1" || -z "$old_deployed" ]] \
  || ! git cat-file -e "$old_deployed^{commit}" 2>/dev/null \
  || ! git merge-base --is-ancestor "$old_deployed" "$new_head"; then
  backend_changed=1
  frontend_changed=1
elif [[ "$old_deployed" != "$new_head" ]]; then
  changed_files="$(git diff --name-only "$old_deployed" "$new_head")"
  if grep -Eq '^(backend/|docker-compose\.yml$)' <<<"$changed_files"; then
    backend_changed=1
  fi
  if grep -Eq '^frontend/' <<<"$changed_files"; then
    frontend_changed=1
  fi
fi

if [[ "$frontend_changed" == "1" ]]; then
  command -v npm >/dev/null 2>&1 || {
    printf '오류: 서버에 npm이 없습니다.\n' >&2
    exit 1
  }
  command -v rsync >/dev/null 2>&1 || {
    printf '오류: 서버에 rsync가 없습니다.\n' >&2
    exit 1
  }
  [[ -d "$web_root" && -w "$web_root" ]] || {
    printf '오류: 웹 루트가 없거나 배포 사용자에게 쓰기 권한이 없습니다: %s\n' "$web_root" >&2
    exit 1
  }
  cd "$repo_path/frontend"
  if [[ ! -f .env.production ]]; then
    printf 'VITE_API_BASE_URL=\n' > .env.production
  fi
  npm ci --no-audit --no-fund
  npm run build
  [[ -s dist/index.html ]] || {
    printf '오류: frontend/dist/index.html이 생성되지 않았습니다.\n' >&2
    exit 1
  }
fi

if [[ "$backend_changed" == "1" ]]; then
  cd "$repo_path"
  docker compose config --quiet
  docker compose up --build -d
fi

if [[ "$frontend_changed" == "1" ]]; then
  rsync -a --delete "$repo_path/frontend/dist/" "$web_root/"
fi

curl --fail --silent --show-error http://127.0.0.1:18080/health >/dev/null
printf '%s\n' "$new_head" > "$deployed_ref.tmp"
mv -f "$deployed_ref.tmp" "$deployed_ref"

printf '서버 배포 완료: %s\n' "${new_head:0:12}"
printf '백엔드 재빌드: %s\n' "$backend_changed"
printf '프론트엔드 재빌드: %s\n' "$frontend_changed"
REMOTE_SCRIPT
