"""Money Note's fixed-host deployment; only --apply may change production.

The shell entrypoints use only Python's standard library. Production data and
configuration are never copied into a checkout, build context or release.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = Path("/opt/money-note")
WEB = Path("/var/www/money")
CONTAINER = "money-note-api-1"
PROJECT = "money-note"
SOURCE_PATHS = (
    "backend/app", "backend/scripts", "backend/Dockerfile", "backend/.dockerignore",
    "backend/requirements.lock", "docker-compose.yml", "frontend/src", "frontend/public",
    "frontend/index.html", "frontend/package.json", "frontend/package-lock.json",
    "frontend/tsconfig.json", "frontend/tsconfig.node.json",
    "frontend/vite.config.ts",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def plain(path):
    require(path.is_absolute() and path.resolve() == path, f"Symlink/relative path rejected: {path}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment():
    # Compose must get production values exclusively from the production .env.
    return {key: value for key, value in os.environ.items()
            if not key.startswith(("MONEY_NOTE_", "COMPOSE_", "VITE_"))}


def run(args, *, cwd=ROOT, sensitive=False):
    result = subprocess.run(args, cwd=cwd, env=environment(), capture_output=True)
    if result.returncode:
        detail = "" if sensitive else (result.stdout + result.stderr).decode(errors="replace")[-4000:]
        raise RuntimeError(f"Command failed: {args[0]} {args[1]}\n{detail}")
    return result.stdout.decode().strip()


def settings():
    values = {"MONEY_NOTE_DEPLOY_BRANCH": "main",
              "MONEY_NOTE_API_BASE_URL": "https://money.hjkerman.re.kr"}
    path = Path(os.environ.get("MONEY_NOTE_DEPLOY_ENV", str(ROOT / ".env.deploy")))
    plain(path)
    require(not path.is_relative_to(PRODUCTION), "Use a developer .env.deploy, not production config")
    if path.exists():
        require(path.is_file() and path.stat().st_mode & 0o077 == 0,
                ".env.deploy must be a private regular file (chmod 600)")
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            require(separator and key in values, "Replace legacy .env.deploy using the local example")
            values[key] = value.strip()
    return values


def source_revision(branch, *, clean):
    plain(ROOT)
    require(not ROOT.is_relative_to(PRODUCTION) and not ROOT.is_relative_to(WEB),
            "Develop and build in the separate Git working copy")
    require(run(["git", "rev-parse", "--show-toplevel"]) == str(ROOT), "Expected checkout root")
    require(run(["git", "branch", "--show-current"]) == branch, f"Expected branch: {branch}")
    if clean:
        require(not run(["git", "status", "--porcelain"]), "Commit all changes before building/deploying")
    return run(["git", "rev-parse", "HEAD"])


def production_paths():
    for path in (PRODUCTION, WEB, PRODUCTION / ".env", PRODUCTION / "data",
                 PRODUCTION / "data/money-note.sqlite3", PRODUCTION / "downloads",
                 PRODUCTION / ".local-deploy"):
        plain(path)
    require(PRODUCTION.is_dir() and WEB.is_dir(), "Expected existing production and web directories")
    require((PRODUCTION / ".env").is_file(), "Production .env is required")
    require((PRODUCTION / ".env").stat().st_mode & 0o077 == 0, "Production .env must remain private")
    require((PRODUCTION / "data/money-note.sqlite3").is_file(), "Expected existing production DB")
    require((PRODUCTION / "downloads").is_dir(), "Expected existing downloads directory")
    require(os.access(PRODUCTION, os.W_OK) and os.access(WEB, os.W_OK),
            "Deployment user must own writable production/control and web directories")


def atomic_copy(source, destination, mode=0o644):
    plain(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    fd, temporary = tempfile.mkstemp(prefix=".money-note-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(source.read_bytes())
            os.fchmod(stream.fileno(), mode)
            if destination.exists():
                previous = destination.stat()
                require(previous.st_uid == os.getuid(), f"Unexpected file owner: {destination}")
                os.fchown(stream.fileno(), previous.st_uid, previous.st_gid)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_json(path, value):
    plain(path)
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def compose(directory):
    return ["docker", "compose", "--project-name", PROJECT,
            "--project-directory", str(PRODUCTION), "--env-file", str(PRODUCTION / ".env"),
            "-f", str(directory / "docker-compose.yml"), "-f", str(directory / "image.json")]


def image_override(directory, image):
    save_json(directory / "image.json", {"services": {"api": {"image": image, "pull_policy": "never"}}})


def validate_compose(directory):
    config = json.loads(run(compose(directory) + ["config", "--format", "json"], sensitive=True))
    require(set(config["services"]) == {"api"}, "Only the Money Note API service may be deployed")
    api = config["services"]["api"]
    volumes = {(item["source"], item["target"], bool(item.get("read_only")))
               for item in api.get("volumes", []) if item["type"] == "bind"}
    require(len(api.get("volumes", [])) == 2 and volumes == {
        (str(PRODUCTION / "data"), "/app/data", False),
        (str(PRODUCTION / "downloads"), "/app/downloads", True),
    }, "Production data/download bind mounts changed; explicit migration review required")
    require(api.get("environment", {}).get("MONEY_NOTE_DB_PATH") == "/app/data/money-note.sqlite3",
            "Production SQLite location must remain unchanged")
    ports = api.get("ports", [])
    require(len(ports) == 1 and ports[0].get("host_ip") == "127.0.0.1"
            and str(ports[0].get("published")) == "18080" and ports[0].get("target") == 8000,
            "Expected loopback production port 18080")
    require(api.get("read_only") is True and "no-new-privileges:true" in api.get("security_opt", []),
            "Production container protections must remain enabled")


def live_image():
    project = run(["docker", "inspect", "--format",
                   '{{index .Config.Labels "com.docker.compose.project"}}', CONTAINER])
    require(project == PROJECT, "Unexpected production Compose project")
    mounts = json.loads(run(["docker", "inspect", "--format", "{{json .Mounts}}", CONTAINER]))
    require({(m["Source"], m["Destination"], m["RW"]) for m in mounts} == {
        (str(PRODUCTION / "data"), "/app/data", True),
        (str(PRODUCTION / "downloads"), "/app/downloads", False),
    }, "Running container uses unexpected persistent paths")
    return run(["docker", "inspect", "--format", "{{.Image}}", CONTAINER])


def health():
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=2) as response:
                if json.load(response) == {"status": "ok"}:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Production API health check failed")


def activate(directory):
    validate_compose(directory)
    run(compose(directory) + ["up", "--detach", "--no-build", "--pull", "never", "--no-deps", "api"])
    expected = json.loads((directory / "image.json").read_text())["services"]["api"]["image"]
    expected_id = run(["docker", "image", "inspect", "--format", "{{.Id}}", expected])
    require(live_image() == expected_id, "Running image differs from the prepared image")
    health()


def stage_source(revision):
    work = ROOT / "work/deploy"
    plain(work)
    work.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f"{revision[:12]}-", dir=work))
    archive = subprocess.check_output(["git", "archive", revision, *SOURCE_PATHS], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            require(member.isfile() or member.isdir(), "Build archive cannot contain links or special files")
            require(not path.is_absolute() and ".." not in path.parts
                    and not any(part.startswith(".env") or part in {"data", "downloads", "secrets", ".git"}
                                for part in path.parts)
                    and path.suffix not in {".db", ".sqlite3", ".jks", ".keystore"},
                    f"Non-deployable archive member: {path}")
        tar.extractall(stage, filter="data")
    return stage


def web_files(dist):
    require((dist / "index.html").is_file() and (dist / "index.html").stat().st_size > 0,
            "Missing frontend index.html")
    require((dist / ".well-known/assetlinks.json").is_file(), "Missing Android assetlinks.json")
    require(any((dist / "assets").glob("*.js")), "Missing built JavaScript assets")
    files = []
    for path in dist.rglob("*"):
        plain(path)
        require(path.is_file() or path.is_dir(), "Unexpected static artifact")
        if path.is_file():
            relative = path.relative_to(dist)
            target = WEB / relative
            plain(target)
            if relative.parts[0] == "assets" and target.exists():
                require(sha(path) == sha(target), f"Immutable asset collision: {relative}")
            files.append(relative)
    return sorted(files, key=lambda path: (path == Path("index.html"), str(path)))


@contextmanager
def build_lock():
    # Retention must not remove another invocation's in-progress staging tree.
    directory = ROOT / 'work/deploy'
    plain(directory)
    directory.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(directory / '.build.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


@contextmanager
def deploy_lock():
    control = PRODUCTION / ".local-deploy"
    plain(control)
    control.mkdir(mode=0o700, exist_ok=True)
    require(control.stat().st_uid == os.getuid() and control.stat().st_mode & 0o077 == 0,
            "Production deployment control directory must be private and owned by deploy user")
    descriptor = os.open(control / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield control
    finally:
        os.close(descriptor)


def restore(backup):
    plain(backup)
    manifest = json.loads((backup / "backup.json").read_text())
    if manifest["backend"]:
        activate(backup)
    for name in manifest["web_files"]:
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "Invalid backup path")
        source, target = backup / "web" / relative, WEB / relative
        plain(source)
        plain(target)
        if source.exists():
            atomic_copy(source, target, source.stat().st_mode & 0o777)
        elif target.exists():
            # Only a newly introduced root file from this attempt; hashed assets are retained.
            target.unlink()
    current = PRODUCTION / ".local-deploy/current.json"
    if manifest["previous"] is None:
        if current.exists():
            current.unlink()
    else:
        save_json(current, manifest["previous"])


def cleanup_server(control):
    """After success, keep current artifacts plus exactly one rollback attempt."""
    current = json.loads((control / "current.json").read_text())
    kept_backup = control / "backups" / current["attempt"]
    manifest = json.loads((kept_backup / "backup.json").read_text())
    keep_assets = set(current["assets"]) | set(manifest["assets"])
    for name in set(current["managed_assets"]) - keep_assets:
        relative = Path(name)
        require(relative.parts[0] == "assets" and ".." not in relative.parts,
                "Invalid managed asset path")
        target = WEB / relative
        plain(target)
        target.unlink(missing_ok=True)
    current["managed_assets"] = sorted(keep_assets)
    save_json(control / "current.json", current)
    keep_runtime = {Path(current["runtime"])}
    if manifest["previous"]:
        keep_runtime.add(Path(manifest["previous"]["runtime"]))
    old_image = json.loads((kept_backup / "image.json").read_text())["services"]["api"]["image"]
    keep_images = {live_image(), old_image}
    kept_tags = {}
    for directory in keep_runtime:
        override = directory / "image.json"
        if override.is_file():
            tag = json.loads(override.read_text())["services"]["api"]["image"]
            if tag.startswith("money-note-local:"):
                kept_tags[tag] = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag])
    keep_attempts = {current["attempt"]}
    if manifest["previous"]:
        keep_attempts.add(manifest["previous"]["attempt"])
    for base in (control / "releases", ROOT / "work/deploy"):
        plain(base)
        if not base.exists():
            continue
        for directory in base.iterdir():
            if directory in keep_runtime or directory.name in keep_attempts:
                continue
            if not re.fullmatch(r"[a-f0-9]{12}-[a-z0-9_]+", directory.name):
                continue
            plain(directory)
            image_file = directory / "image.json"
            if image_file.exists():
                tag = json.loads(image_file.read_text())["services"]["api"]["image"]
                # Never run a global prune or remove a legacy/foreign image.
                if tag.startswith("money-note-local:"):
                    try:
                        image_id = run(["docker", "image", "inspect", "--format", "{{.Id}}", tag])
                    except RuntimeError:
                        image_id = None
                    # Repeated builds can share an image ID. Remove obsolete tags
                    # when a retained runtime tag still protects that same image.
                    if image_id and tag not in kept_tags and (
                        image_id not in keep_images or image_id in kept_tags.values()
                    ):
                        run(["docker", "image", "rm", tag])
            shutil.rmtree(directory)
    for backup in (control / "backups").iterdir():
        if backup != kept_backup and re.fullmatch(r"[a-f0-9]{12}-[a-z0-9_]+", backup.name):
            plain(backup)
            shutil.rmtree(backup)


def apply_server(stage, revision, backend, frontend, previous, old_image):
    with deploy_lock() as control:
        production_paths()
        pending = control / "pending.json"
        require(not pending.exists(), "Unfinished deployment: use --rollback ATTEMPT --apply first")
        current = control / "current.json"
        actual = json.loads(current.read_text()) if current.exists() else None
        require(actual == previous and live_image() == old_image, "Production changed during build; retry")
        attempt = stage.name
        release, backup = control / "releases" / attempt, control / "backups" / attempt
        plain(release)
        plain(backup)
        release.mkdir(parents=True)
        backup.mkdir(parents=True)
        old_compose = Path(previous["runtime"]) if previous else PRODUCTION
        plain(old_compose)
        shutil.copy2(old_compose / "docker-compose.yml", backup / "docker-compose.yml")
        image_override(backup, old_image)
        files = web_files(stage / "frontend/dist") if frontend else []
        mutable = [path for path in files if path.parts[0] != "assets"]
        for relative in mutable:
            if (WEB / relative).exists():
                target = backup / "web" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(WEB / relative, target)
        existing_assets = {
            str(path.relative_to(WEB)) for path in (WEB / "assets").rglob("*") if path.is_file()
        }
        old_assets = previous["assets"] if previous else sorted(existing_assets)
        new_assets = [str(path) for path in files if path.parts[0] == "assets"] if frontend else old_assets
        save_json(backup / "backup.json", {
            "backend": backend, "web_files": [str(path) for path in mutable], "previous": previous,
            "assets": old_assets,
        })
        if backend:
            shutil.copy2(stage / "docker-compose.yml", release / "docker-compose.yml")
            shutil.copy2(stage / "image.json", release / "image.json")
        save_json(pending, {"attempt": attempt})
        try:
            if backend:
                activate(release)
            else:
                health()
            for relative in files:
                atomic_copy(stage / "frontend/dist" / relative, WEB / relative)
            save_json(current, {"commit": revision, "runtime": str(release if backend else old_compose),
                                "attempt": attempt, "assets": new_assets,
                                "managed_assets": sorted(existing_assets | set(new_assets))})
        except BaseException:
            try:
                restore(backup)
                pending.unlink()
            except BaseException as failure:
                raise RuntimeError(f"Rollback incomplete; retain {backup}; pending deployment blocks retries") from failure
            raise
        pending.unlink()
        print(f"Deployed {revision}; backup/rollback attempt: {attempt}")
        try:
            cleanup_server(control)
        except (OSError, RuntimeError) as error:
            print(f"Deployment succeeded; retention cleanup needs retry: {error}")


def server(args, revision):
    production_paths()
    current = PRODUCTION / ".local-deploy/current.json"
    plain(current)
    previous = json.loads(current.read_text()) if current.exists() else None
    if args.rollback:
        require(re.fullmatch(r"[a-f0-9]{12}-[a-z0-9_]+", args.rollback), "Invalid rollback attempt")
        backup = PRODUCTION / ".local-deploy/backups" / args.rollback
        require((backup / "backup.json").is_file(), "Rollback backup is missing")
        print(f"Rollback artifact plan: {backup}; DB and .env remain in place")
        if args.apply:
            with deploy_lock() as control:
                pending = control / "pending.json"
                selected = json.loads(pending.read_text())["attempt"] if pending.exists() else (
                    previous["attempt"] if previous else None)
                require(selected == args.rollback, "Only the current or interrupted attempt may be rolled back")
                restore(backup)
                if pending.exists():
                    pending.unlink()
        return
    old_image = live_image()
    backend = frontend = True
    if previous and not args.force:
        try:
            changed = run(["git", "diff", "--name-only", previous["commit"], revision]).splitlines()
            backend = any(path.startswith("backend/") or path == "docker-compose.yml" for path in changed)
            frontend = any(path.startswith("frontend/") for path in changed)
        except RuntimeError:
            pass
    print(f"Committed source: {revision}; backend={backend}; frontend={frontend}")
    print(f"Build: {ROOT / 'work/deploy'}; production: {PRODUCTION}; web: {WEB}")
    if not args.apply and not args.stage_only:
        print("Dry run: no build, production writes, service changes, fetch or push")
        return
    stage = stage_source(revision)
    if frontend:
        run(["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
             "--env", "npm_config_cache=/tmp/npm-cache", "--env", "VITE_API_BASE_URL=",
             "--volume", f"{stage / 'frontend'}:/app", "--workdir", "/app", "node:22-alpine",
             "sh", "-c", "npm ci --no-audit --no-fund && npm run build"])
        web_files(stage / "frontend/dist")
    if backend:
        image = f"money-note-local:{stage.name}"
        # Record ownership before building, including an interrupted build's tag.
        image_override(stage, image)
        run(["docker", "build", "--tag", image, str(stage / "backend")])
        require(run(["docker", "image", "inspect", "--format", "{{.Config.User}}", image])
                in {"money-note", "1000", "1000:1000"}, "Expected non-root runtime user")
        validate_compose(stage)
    print(f"Prepared artifacts: {stage}")
    if args.apply:
        apply_server(stage, revision, backend, frontend, previous, old_image)


def mobile(args, revision, config):
    require(not args.rollback and not args.force, "Mobile supports --dry-run, --stage-only or --apply")
    production_paths()
    target = PRODUCTION / "downloads/money-note.apk"
    plain(target)
    require(config["MONEY_NOTE_API_BASE_URL"].startswith("https://"), "Release API must use HTTPS")
    print(f"Signed APK plan: {revision} -> {target}; no API/Apache restart")
    if not args.apply and not args.stage_only:
        print("Dry run: Flutter/JDK/signing prerequisites required only for building")
        return
    require(shutil.which("flutter"), "Flutter is not installed; use the documented Android build environment")
    signing = ROOT / "mobile/android/key.properties"
    plain(signing)
    require(signing.is_file() and signing.stat().st_mode & 0o077 == 0,
            "Existing private release signing config required (key.properties, chmod 600)")
    for command in (["flutter", "pub", "get"], ["flutter", "analyze"], ["flutter", "test"],
                    ["flutter", "build", "apk", "--release",
                     f"--dart-define=MONEY_NOTE_API_BASE_URL={config['MONEY_NOTE_API_BASE_URL']}"]):
        run(command, cwd=ROOT / "mobile")
    apk = ROOT / "mobile/build/app/outputs/flutter-apk/app-release.apk"
    plain(apk)
    require(apk.is_file() and apk.stat().st_size > 0, "Release APK missing")
    require(source_revision(config["MONEY_NOTE_DEPLOY_BRANCH"], clean=True) == revision,
            "Checkout changed during APK build; commit changes and rebuild")
    digest = sha(apk)
    print(f"Prepared APK SHA-256: {digest}")
    if args.apply:
        with deploy_lock() as control:
            require(not (control / "pending.json").exists(), "Complete interrupted server deployment first")
            backup = control / "apk-backups"
            plain(backup)
            backup.mkdir(mode=0o700, exist_ok=True)
            backup_file = backup / f"{sha(target)}.apk" if target.exists() else None
            if backup_file:
                shutil.copy2(target, backup_file)
            fd, temp = tempfile.mkstemp(prefix=".money-note-apk-", dir=target.parent)
            os.close(fd)
            try:
                shutil.copyfile(apk, temp)
                require(sha(Path(temp)) == digest, "Staged APK hash mismatch")
                atomic_copy(Path(temp), target)
            finally:
                Path(temp).unlink(missing_ok=True)
            require(sha(target) == digest, "Published APK hash mismatch")
            save_json(control / "apk-current.json", {"commit": revision, "sha256": digest})
            # A successful publication retains only the immediately preceding APK.
            previous_digest = sha(backup_file) if backup_file else None
            for old in backup.glob("*.apk"):
                if old.name != f"{previous_digest}.apk":
                    plain(old)
                    old.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=("server", "mobile"))
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="default; read-only deployment plan")
    modes.add_argument("--stage-only", action="store_true", help="build locally; do not change production")
    modes.add_argument("--apply", action="store_true", help="explicit production deployment operation")
    parser.add_argument("--force", action="store_true", help="rebuild both server areas")
    parser.add_argument("--rollback", metavar="ATTEMPT", help="restore current/interrupted artifact backup")
    args = parser.parse_args()
    require(not (args.rollback and args.stage_only), "Rollback cannot use --stage-only")
    config = settings()
    revision = source_revision(config["MONEY_NOTE_DEPLOY_BRANCH"], clean=args.apply or args.stage_only)
    def execute():
        if args.target == "server":
            server(args, revision)
        else:
            mobile(args, revision, config)

    if args.apply or args.stage_only:
        with build_lock():
            execute()
    else:
        execute()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Deployment stopped: {error}") from None
