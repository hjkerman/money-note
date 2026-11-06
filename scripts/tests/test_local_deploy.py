"""Exercise real file publication/rollback in tmp_path; Docker and health are fakes."""

import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

import pytest


spec = importlib.util.spec_from_file_location(
    "local_deploy", Path(__file__).resolve().parents[1] / "local_deploy.py"
)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def put(path, value, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    path.chmod(mode)


def arguments(**kwargs):
    return argparse.Namespace(apply=False, stage_only=False, force=False, rollback=None, **kwargs)


@pytest.fixture
def host(tmp_path, monkeypatch):
    root, production, web = (tmp_path / name for name in ("checkout", "production", "web"))
    for path in (root, production, web, production / "downloads"):
        path.mkdir()
    put(production / ".env", "PRIVATE_TEST_CONFIGURATION=preserve", 0o600)
    put(production / "data/money-note.sqlite3", "persistent DB sentinel", 0o600)
    put(production / "data/snapshot-backups/snapshot.json", "persistent backup sentinel")
    put(production / "downloads/money-note.apk", "old APK")
    put(production / "docker-compose.yml", "legacy compose")
    put(web / "index.html", '<script src="assets/old.js"></script>')
    put(web / "assets/old.js", "old JS")
    put(web / ".well-known/assetlinks.json", "old assetlinks")
    for key, value in (("ROOT", root), ("PRODUCTION", production), ("WEB", web)):
        monkeypatch.setattr(deploy, key, value)
    machine = {"image": "sha256:legacy", "activations": [], "removed": [], "fail_build": False,
               "fail_health": False, "calls": []}

    def config():
        return {"services": {"api": {
            "volumes": [
                {"type": "bind", "source": str(production / "data"), "target": "/app/data"},
                {"type": "bind", "source": str(production / "downloads"), "target": "/app/downloads",
                 "read_only": True},
            ],
            "environment": {"MONEY_NOTE_DB_PATH": "/app/data/money-note.sqlite3"},
            "ports": [{"host_ip": "127.0.0.1", "published": "18080", "target": 8000}],
            "read_only": True, "security_opt": ["no-new-privileges:true"],
        }}}

    def fake_run(args, **kwargs):
        machine["calls"].append(args)
        if args[:2] == ["docker", "inspect"]:
            if "Labels" in args[3]:
                return deploy.PROJECT
            if "Mounts" in args[3]:
                return json.dumps([
                    {"Source": str(production / "data"), "Destination": "/app/data", "RW": True},
                    {"Source": str(production / "downloads"), "Destination": "/app/downloads", "RW": False},
                ])
            return machine["image"]
        if args[:3] == ["docker", "image", "inspect"]:
            return "money-note" if "User" in args[4] else args[-1]
        if args[:3] == ["docker", "image", "rm"]:
            machine["removed"].append(args[-1])
            return ""
        if args[:2] == ["docker", "compose"]:
            if "config" in args:
                return json.dumps(machine.get("config", config()))
            directory = Path(args[args.index("-f") + 1]).parent
            machine["image"] = json.loads((directory / "image.json").read_text())["services"]["api"]["image"]
            machine["activations"].append(machine["image"])
            return ""
        if args[:2] == ["docker", "build"] and machine["fail_build"]:
            raise RuntimeError("injected build failure")
        if args[:2] in (["docker", "run"], ["docker", "build"]) or args[0] == "flutter":
            return ""
        raise AssertionError(f"Unexpected external command: {args}")

    def fake_health():
        if machine["fail_health"] and machine["image"].startswith("money-note-local:"):
            raise RuntimeError("injected health failure")

    monkeypatch.setattr(deploy, "run", fake_run)
    monkeypatch.setattr(deploy, "health", fake_health)
    machine.update(root=root, production=production, web=web, config_factory=config)
    return machine


def stage(host, number=1):
    name = f"{'a' * 12}-attempt{number}"
    path = host["root"] / "work/deploy" / name
    put(path / "docker-compose.yml", "candidate compose")
    put(path / "backend/Dockerfile", "FROM synthetic")
    put(path / "frontend/dist/index.html", f'<script src="assets/new{number}.js"></script>')
    put(path / f"frontend/dist/assets/new{number}.js", f"new JS {number}")
    put(path / "frontend/dist/.well-known/assetlinks.json", f"new assetlinks {number}")
    deploy.image_override(path, f"money-note-local:{name}")
    return path


def apply(host, prepared):
    current = host["production"] / ".local-deploy/current.json"
    previous = json.loads(current.read_text()) if current.exists() else None
    deploy.apply_server(prepared, "a" * 40, True, True, previous, host["image"])


def protected(host):
    production = host["production"]
    paths = [production / ".env", production / "data/money-note.sqlite3",
             production / "data/snapshot-backups/snapshot.json", production / "downloads/money-note.apk",
             production / "docker-compose.yml"]
    return {str(path): (path.read_bytes(), path.stat().st_mode) for path in paths}


def test_default_dry_run_never_builds_or_writes_production(host):
    before = protected(host)
    deploy.server(arguments(), "a" * 40)
    assert protected(host) == before
    assert not (host["production"] / ".local-deploy").exists()
    assert not host["activations"]
    assert all(call[:2] == ["docker", "inspect"] for call in host["calls"])


@pytest.mark.parametrize("name", ["data", ".local-deploy", "downloads"])
def test_production_paths_reject_symlinks(host, tmp_path, name):
    source = host["production"] / name
    if source.exists():
        source.rename(tmp_path / f"original-{name}")
    source.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(RuntimeError, match="Symlink"):
        deploy.production_paths()


def test_production_checkout_is_rejected_before_commands(host, monkeypatch):
    monkeypatch.setattr(deploy, "ROOT", host["production"])
    with pytest.raises(RuntimeError, match="separate Git working copy"):
        deploy.source_revision("main", clean=True)
    assert not host["calls"]


def test_compose_cannot_redirect_persistent_database(host):
    config = host["config_factory"]()
    config["services"]["api"]["volumes"][0]["source"] = str(host["root"] / "data")
    host["config"] = config
    with pytest.raises(RuntimeError, match="bind mounts changed"):
        deploy.validate_compose(stage(host))


@pytest.mark.parametrize("name,link", [("backend/data/private.db", False),
                                      ("frontend/.env.production", False), ("backend/app/link", True)])
def test_build_archive_rejects_data_secrets_and_links(host, monkeypatch, name, link):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        info = tarfile.TarInfo(name)
        if link:
            info.type, info.linkname = tarfile.SYMTYPE, str(host["production"])
        archive.addfile(info)
    monkeypatch.setattr(deploy.subprocess, "check_output", lambda *args, **kwargs: stream.getvalue())
    with pytest.raises(RuntimeError, match="Non-deployable|cannot contain links"):
        deploy.stage_source("a" * 40)


def test_committed_archive_closes_frontend_relative_imports(host, monkeypatch):
    """Use the real Git allowlist, not the surrounding checkout's files."""
    checkout = Path(__file__).resolve().parents[2]
    contents = subprocess.check_output(["git", "archive", "HEAD", *deploy.SOURCE_PATHS], cwd=checkout)
    monkeypatch.setattr(deploy.subprocess, "check_output", lambda *args, **kwargs: contents)
    prepared = deploy.stage_source("a" * 40)
    imports = re.compile(r'''(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s*)["'](\.{1,2}/[^"']+)["']''')
    missing = []
    checked = 0
    for source in (prepared / "frontend").rglob("*"):
        if source.suffix not in {".ts", ".tsx", ".mjs"}:
            continue
        for dependency in imports.findall(source.read_text()):
            target = (source.parent / dependency).resolve()
            assert target.is_relative_to(prepared), f"Import escapes archive: {source}: {dependency}"
            candidates = [target] + [Path(str(target) + suffix) for suffix in (".ts", ".tsx", ".js", ".json")]
            candidates += [target / ("index" + suffix) for suffix in (".ts", ".tsx", ".js")]
            if not any(candidate.is_file() for candidate in candidates):
                missing.append(f"{source.relative_to(prepared)} -> {dependency}")
            checked += 1
    assert checked > 0
    assert not missing, "Missing archive dependencies: " + "; ".join(missing)
    # Include configuration inputs for every declared stage validation command.
    for name in ("package.json", "package-lock.json", "tsconfig.json", "tsconfig.node.json",
                 "vite.config.ts", "eslint.config.mjs", "index.html"):
        assert (prepared / "frontend" / name).is_file(), f"Missing frontend configuration: {name}"
    for path in prepared.rglob("*"):
        assert not path.is_symlink()
        relative = path.relative_to(prepared)
        assert not set(relative.parts) & {"work", "data", "downloads", "secrets", ".git", ".local-deploy"}
        assert not any(part.startswith(".env") for part in relative.parts)
        assert path.suffix not in {".db", ".sqlite3", ".jks", ".keystore"}


def test_stage_only_preserves_archive_layout_and_validates_before_publication(host, monkeypatch):
    prepared = stage(host)
    monkeypatch.setattr(deploy, "stage_source", lambda revision: prepared)
    args = arguments()
    args.stage_only, args.force = True, True
    before = protected(host)
    deploy.server(args, "a" * 40)
    command = next(call for call in host["calls"] if call[:2] == ["docker", "run"])
    assert f"{prepared}:/source:ro" in command
    assert f"{prepared / 'frontend'}:/source/frontend" in command
    assert command[command.index("--workdir") + 1] == "/source/frontend"
    assert command[-1] == "npm ci --no-audit --no-fund && npm test && npm run lint && npm run build"
    assert protected(host) == before
    assert not host["activations"]
    assert not (host["production"] / ".local-deploy").exists()


def test_failed_frontend_validation_cannot_build_or_publish_backend(host, monkeypatch):
    prepared = stage(host)
    original_run = deploy.run

    def failed_validation(command, **kwargs):
        if command[:2] == ["docker", "run"]:
            raise RuntimeError("injected frontend validation failure")
        return original_run(command, **kwargs)

    monkeypatch.setattr(deploy, "run", failed_validation)
    monkeypatch.setattr(deploy, "stage_source", lambda revision: prepared)
    args = arguments()
    args.apply, args.force = True, True
    before = protected(host)
    with pytest.raises(RuntimeError, match="frontend validation failure"):
        deploy.server(args, "a" * 40)
    assert protected(host) == before
    assert not host["activations"]
    assert not any(call[:2] == ["docker", "build"] for call in host["calls"])
    assert not (host["production"] / ".local-deploy").exists()


@pytest.mark.parametrize("changed", ["backend/tests/fixtures/confirmed_recurring_actual.json",
                                    "scripts/local_deploy.py"])
def test_shared_input_and_packaging_changes_revalidate_frontend(host, monkeypatch, changed):
    prepared = stage(host)
    put(host["production"] / ".local-deploy/current.json", json.dumps({"commit": "b" * 40}))
    original_run = deploy.run

    def changed_run(command, **kwargs):
        if command[:3] == ["git", "diff", "--name-only"]:
            return changed
        return original_run(command, **kwargs)

    monkeypatch.setattr(deploy, "run", changed_run)
    monkeypatch.setattr(deploy, "stage_source", lambda revision: prepared)
    args = arguments()
    args.stage_only = True
    deploy.server(args, "a" * 40)
    assert any(call[:2] == ["docker", "run"] for call in host["calls"])
    assert not host["activations"]


def test_failed_build_aborts_before_production_writes(host, monkeypatch):
    prepared = stage(host)
    monkeypatch.setattr(deploy, "stage_source", lambda revision: prepared)
    host["fail_build"] = True
    args = arguments()
    args.apply = True
    before = protected(host)
    with pytest.raises(RuntimeError, match="build failure"):
        deploy.server(args, "a" * 40)
    assert protected(host) == before
    assert not (host["production"] / ".local-deploy").exists()
    assert not host["activations"]


def test_success_publishes_index_last_and_preserves_data(host, monkeypatch):
    before = protected(host)
    copied = []
    original_copy = deploy.atomic_copy

    def copy(source, target, *args):
        copied.append(target)
        original_copy(source, target, *args)

    monkeypatch.setattr(deploy, "atomic_copy", copy)
    apply(host, stage(host))
    assert copied[-1] == host["web"] / "index.html"
    assert protected(host) == before
    assert (host["web"] / "assets/old.js").exists()
    assert not list((host["production"] / ".local-deploy").rglob("*.sqlite3"))
    assert not list((host["production"] / ".local-deploy").rglob(".env"))


def test_failed_health_restores_old_image_and_keeps_old_web(host):
    before = protected(host)
    host["fail_health"] = True
    with pytest.raises(RuntimeError, match="health failure"):
        apply(host, stage(host))
    assert host["image"] == "sha256:legacy"
    assert (host["web"] / "index.html").read_text().find("old.js") >= 0
    assert protected(host) == before
    assert not (host["production"] / ".local-deploy/current.json").exists()
    assert not (host["production"] / ".local-deploy/pending.json").exists()


def test_failed_web_publication_restores_image_and_root_files(host, monkeypatch):
    original_copy = deploy.atomic_copy
    failed = False

    def copy(source, target, *args):
        nonlocal failed
        if target.name == "index.html" and not failed:
            failed = True
            raise OSError("injected publication failure")
        original_copy(source, target, *args)

    monkeypatch.setattr(deploy, "atomic_copy", copy)
    with pytest.raises(OSError, match="publication failure"):
        apply(host, stage(host))
    assert host["image"] == "sha256:legacy"
    assert (host["web"] / ".well-known/assetlinks.json").read_text() == "old assetlinks"
    assert "old.js" in (host["web"] / "index.html").read_text()


def test_three_successes_retain_only_current_and_previous_artifacts(host):
    before = protected(host)
    for number in (1, 2, 3):
        apply(host, stage(host, number))
    control = host["production"] / ".local-deploy"
    assert [path.name for path in (control / "backups").iterdir()] == ["a" * 12 + "-attempt3"]
    assert len(list((control / "releases").iterdir())) == 2
    assert len(list((host["root"] / "work/deploy").iterdir())) == 2
    assert {path.name for path in (host["web"] / "assets").iterdir()} == {"new2.js", "new3.js"}
    assert host["removed"] and all(tag.startswith("money-note-local:") for tag in host["removed"])
    assert "sha256:legacy" not in host["removed"]
    assert protected(host) == before


def test_manual_rollback_uses_one_retained_backup(host):
    for number in (1, 2, 3):
        apply(host, stage(host, number))
    args = arguments()
    args.rollback, args.apply = "a" * 12 + "-attempt3", True
    deploy.server(args, "a" * 40)
    assert "new2.js" in (host["web"] / "index.html").read_text()
    assert host["image"].endswith("attempt2")


def test_interrupted_attempt_blocks_another_publication(host):
    with deploy.deploy_lock() as control:
        deploy.save_json(control / "pending.json", {"attempt": "a" * 12 + "-attempt0"})
    with pytest.raises(RuntimeError, match="Unfinished deployment"):
        apply(host, stage(host))
    assert host["image"] == "sha256:legacy"


def test_apk_retains_one_previous_version_without_service_restart(host, monkeypatch):
    monkeypatch.setattr(deploy.shutil, "which", lambda name: "/fake/flutter")
    monkeypatch.setattr(deploy, "source_revision", lambda *args, **kwargs: "a" * 40)
    put(host["root"] / "mobile/android/key.properties", "synthetic signing config", 0o600)
    args = arguments()
    args.apply = True
    for number in (1, 2, 3):
        put(host["root"] / "mobile/build/app/outputs/flutter-apk/app-release.apk", f"APK {number}")
        deploy.mobile(args, "a" * 40, {"MONEY_NOTE_API_BASE_URL": "https://example.test", "MONEY_NOTE_DEPLOY_BRANCH": "main"})
    backup = host["production"] / ".local-deploy/apk-backups"
    assert [path.read_text() for path in backup.iterdir()] == ["APK 2"]
    assert (host["production"] / "downloads/money-note.apk").read_text() == "APK 3"
    assert not host["activations"]


def test_concurrent_build_cannot_race_retention(host):
    with deploy.build_lock():
        with pytest.raises(BlockingIOError):
            with deploy.build_lock():
                raise AssertionError('Second build must not enter')


def test_failed_deploy_does_not_prune_previous_success_backup(host):
    apply(host, stage(host, 1))
    control = host['production'] / '.local-deploy'
    first_backup = control / 'backups' / ('a' * 12 + '-attempt1')
    host['fail_health'] = True
    with pytest.raises(RuntimeError, match='Rollback incomplete'):
        apply(host, stage(host, 2))
    assert first_backup.is_dir()
    assert (control / 'pending.json').exists()
    assert (host['web'] / 'assets/old.js').exists()


def test_symlink_web_asset_cannot_redirect_publication(host, tmp_path):
    prepared = stage(host)
    outside = tmp_path / 'outside.js'
    outside.write_text('must remain unchanged')
    (host['web'] / 'assets/new1.js').symlink_to(outside)
    with pytest.raises(RuntimeError, match='Symlink'):
        deploy.web_files(prepared / 'frontend/dist')
    assert outside.read_text() == 'must remain unchanged'


def test_repeated_identical_image_builds_do_not_accumulate_old_tags(host, monkeypatch):
    original_run = deploy.run

    def same_image(args, **kwargs):
        value = original_run(args, **kwargs)
        if args[:2] == ["docker", "inspect"] and args[3] == "{{.Image}}":
            return "sha256:identical" if value.startswith("money-note-local:") else value
        if args[:3] == ["docker", "image", "inspect"] and "{{.Id}}" in args:
            return "sha256:identical" if args[-1].startswith("money-note-local:") else value
        return value

    monkeypatch.setattr(deploy, "run", same_image)
    for number in (1, 2, 3):
        current = host["production"] / ".local-deploy/current.json"
        previous = json.loads(current.read_text()) if current.exists() else None
        deploy.apply_server(stage(host, number), "a" * 40, True, True, previous, deploy.live_image())
    assert set(host["removed"]) == {"money-note-local:" + "a" * 12 + "-attempt1"}


def test_checkout_change_during_apk_build_aborts_before_publication(host, monkeypatch):
    monkeypatch.setattr(deploy.shutil, "which", lambda name: "/fake/flutter")
    monkeypatch.setattr(deploy, "source_revision", lambda *args, **kwargs: "b" * 40)
    put(host["root"] / "mobile/android/key.properties", "synthetic signing config", 0o600)
    put(host["root"] / "mobile/build/app/outputs/flutter-apk/app-release.apk", "new APK")
    args = arguments()
    args.apply = True
    before = protected(host)
    with pytest.raises(RuntimeError, match="Checkout changed"):
        deploy.mobile(args, "a" * 40, {"MONEY_NOTE_API_BASE_URL": "https://example.test",
                                        "MONEY_NOTE_DEPLOY_BRANCH": "main"})
    assert protected(host) == before
    assert not (host["production"] / ".local-deploy").exists()


PROMOTION_RELEASE = "a" * 40
PROMOTION_CONTROLLER = "b" * 40
PROMOTION_IMAGE = "sha256:" + "c" * 64


@pytest.fixture
def promotion(host, tmp_path, monkeypatch):
    artifacts = tmp_path / "approved-artifacts"
    artifacts.mkdir(mode=0o700)
    dist = artifacts / "web"
    put(dist / "index.html", '<script src="assets/promoted.js"></script>')
    put(dist / "assets/promoted.js", "approved JS")
    put(dist / ".well-known/assetlinks.json", "approved assetlinks")
    sources = {
        "docker-compose.yml": b"approved compose",
        "backend/Dockerfile": b"FROM synthetic",
        "backend/requirements.lock": b"locked synthetic dependencies",
    }

    def digest(raw):
        return deploy.hashlib.sha256(raw).hexdigest()

    web = deploy.promotion_inventory(dist)
    manifest = {
        "version": 1,
        "release": PROMOTION_RELEASE,
        "backend_image_id": PROMOTION_IMAGE,
        "compose_sha256": digest(sources["docker-compose.yml"]),
        "web_root": "web",
        "web_files": web,
        "web_manifest_sha256": deploy.promotion_digest(web),
        "provenance": {
            "dockerfile_sha256": digest(sources["backend/Dockerfile"]),
            "requirements_lock_sha256": digest(sources["backend/requirements.lock"]),
            "python_base_image": "sha256:" + "d" * 64,
            "node_image": "sha256:" + "e" * 64,
        },
    }
    path = artifacts / "promotion.json"
    fake_run = deploy.run

    def run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return PROMOTION_RELEASE
        return fake_run(args, **kwargs)

    def show(args, **kwargs):
        assert args[:2] == ["git", "show"]
        return sources[args[2].split(":", 1)[1]]

    monkeypatch.setattr(deploy, "run", run)
    monkeypatch.setattr(deploy.subprocess, "check_output", show)

    def write():
        put(path, json.dumps(manifest), 0o600)
        return arguments(
            promote_manifest=str(path),
            expected_manifest_sha256=deploy.sha(path),
            controller_revision=PROMOTION_CONTROLLER,
            release=PROMOTION_RELEASE,
        )

    return {
        "manifest": manifest,
        "path": path,
        "dist": dist,
        "write": write,
        "args": write(),
        "run": run,
    }


def no_builds(host):
    assert not any(
        call[:2] in (["docker", "build"], ["docker", "pull"], ["docker", "run"])
        or call[0] in {"npm", "flutter"}
        for call in host["calls"]
    )


def test_promotion_stage_only_is_exact_and_does_not_access_production(
    host, promotion, monkeypatch
):
    args = promotion["args"]
    args.stage_only = True
    monkeypatch.setattr(
        deploy, "production_paths", lambda: pytest.fail("Production access")
    )
    deploy.server(args, PROMOTION_RELEASE)
    prepared = next(p for p in (host["root"] / "work/deploy").iterdir() if p.is_dir())
    assert re.fullmatch(r"a{12}-[a-z0-9_]+", prepared.name)
    assert (
        json.loads((prepared / "image.json").read_text())["services"]["api"]["image"]
        == PROMOTION_IMAGE
    )
    assert (
        deploy.promotion_inventory(prepared / "frontend/dist")
        == promotion["manifest"]["web_files"]
    )
    assert not host["activations"]
    no_builds(host)


def test_promotion_uses_existing_publication_and_records_separate_identity(
    host, promotion
):
    before = protected(host)
    args = promotion["args"]
    args.apply = True
    deploy.server(args, PROMOTION_RELEASE)
    current = json.loads(
        (host["production"] / ".local-deploy/current.json").read_text()
    )
    assert current["commit"] == PROMOTION_RELEASE
    assert current["controller_commit"] == PROMOTION_CONTROLLER
    assert current["backend_image_id"] == PROMOTION_IMAGE
    assert current["promotion_manifest_sha256"] == args.expected_manifest_sha256
    assert (
        current["web_manifest_sha256"] == promotion["manifest"]["web_manifest_sha256"]
    )
    assert host["activations"] == [PROMOTION_IMAGE]
    assert (host["web"] / "index.html").read_bytes() == (
        promotion["dist"] / "index.html"
    ).read_bytes()
    assert protected(host) == before
    no_builds(host)


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "release",
        "image",
        "missing_image",
        "compose",
        "file",
        "add",
        "delete",
        "symlink",
        "traversal",
        "absolute",
        "version",
        "bool_version",
        "missing",
        "extra",
        "provenance",
        "duplicate",
        "case",
        "web_digest",
        "root_escape",
        "malformed",
        "unsafe_type",
    ],
)
def test_invalid_promotion_never_publishes(host, promotion, monkeypatch, change):
    m = promotion["manifest"]
    if change == "release":
        m["release"] = "f" * 40
    if change == "image":
        m["backend_image_id"] = "money-note-local:mutable"
    if change == "compose":
        m["compose_sha256"] = "0" * 64
    if change == "version":
        m["version"] = 2
    if change == "bool_version":
        m["version"] = True
    if change == "missing":
        del m["web_root"]
    if change == "extra":
        m["unchecked"] = "value"
    if change == "provenance":
        m["provenance"]["dockerfile_sha256"] = "0" * 64
    if change == "web_digest":
        m["web_manifest_sha256"] = "0" * 64
    if change == "root_escape":
        m["web_root"] = "../outside"
    if change in {"traversal", "absolute", "case"}:
        key = {
            "traversal": "../secret",
            "absolute": "/etc/passwd",
            "case": "INDEX.html",
        }[change]
        m["web_files"][key] = "0" * 64
    if change == "file":
        put(promotion["dist"] / "index.html", "changed")
    if change == "add":
        put(promotion["dist"] / "extra.js", "extra")
    if change == "delete":
        (promotion["dist"] / "index.html").unlink()
    if change == "symlink":
        (promotion["dist"] / "index.html").unlink()
        (promotion["dist"] / "index.html").symlink_to(host["production"] / ".env")
    if change == "unsafe_type":
        deploy.os.mkfifo(promotion["dist"] / "pipe")
    args = promotion["write"]()
    if change == "hash":
        args.expected_manifest_sha256 = "0" * 64
    if change in {"duplicate", "malformed"}:
        text = promotion["path"].read_text()
        put(
            promotion["path"],
            '{"version":1,' + text[1:] if change == "duplicate" else "{",
            0o600,
        )
        args.expected_manifest_sha256 = deploy.sha(promotion["path"])
    if change == "missing_image":

        def unavailable(*args, **kwargs):
            raise RuntimeError("image missing")

        monkeypatch.setattr(deploy, "verify_promotion_image", unavailable)
    args.apply = True
    before = protected(host)
    with pytest.raises(RuntimeError):
        deploy.server(args, PROMOTION_RELEASE)
    assert protected(host) == before and not host["activations"]
    assert not (host["production"] / ".local-deploy/pending.json").exists()
    no_builds(host)


def test_promotion_rejects_backend_identity_mismatch(host, promotion, monkeypatch):
    original = deploy.run
    monkeypatch.setattr(
        deploy,
        "run",
        lambda args, **kw: (
            "sha256:" + "0" * 64
            if args[:3] == ["docker", "image", "inspect"]
            else original(args, **kw)
        ),
    )
    with pytest.raises(RuntimeError, match="image mismatch"):
        deploy.server(promotion["args"], PROMOTION_RELEASE)
    assert not host["activations"]


@pytest.mark.parametrize(
    "file",
    ["frontend/dist/index.html", "docker-compose.yml", "image.json", "promotion.json"],
)
def test_changed_staging_is_rejected_under_deploy_lock(host, promotion, file):
    info = deploy.load_promotion(promotion["args"], PROMOTION_RELEASE)
    prepared = deploy.prepare_promotion(info)
    put(prepared / file, "tampered")
    before = protected(host)
    with pytest.raises(RuntimeError):
        deploy.apply_server(
            prepared, PROMOTION_RELEASE, True, True, None, host["image"], promotion=info
        )
    assert protected(host) == before and not host["activations"]


def test_last_validation_failure_does_not_publish_or_set_pending(
    host, promotion, monkeypatch
):
    info = deploy.load_promotion(promotion["args"], PROMOTION_RELEASE)
    prepared = deploy.prepare_promotion(info)
    original = deploy.verify_promotion_stage
    calls = 0

    def check(stage, proof):
        nonlocal calls
        calls += 1
        if calls == 2:
            put(stage / "frontend/dist/index.html", "changed during backup preparation")
        original(stage, proof)

    monkeypatch.setattr(deploy, "verify_promotion_stage", check)
    with pytest.raises(RuntimeError):
        deploy.apply_server(
            prepared, PROMOTION_RELEASE, True, True, None, host["image"], promotion=info
        )
    assert calls == 2 and not host["activations"]
    assert not (host["production"] / ".local-deploy/pending.json").exists()


def test_interrupted_promotion_copy_never_publishes(host, promotion, monkeypatch):
    monkeypatch.setattr(
        deploy.shutil,
        "copyfile",
        lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    args = promotion["args"]
    args.apply = True
    with pytest.raises(KeyboardInterrupt):
        deploy.server(args, PROMOTION_RELEASE)
    assert not host["activations"]
    assert not (host["production"] / ".local-deploy/pending.json").exists()


@pytest.mark.parametrize("failure", ["health", "web", "interrupt"])
def test_promotion_failure_restores_previous_artifacts(
    host, promotion, monkeypatch, failure
):
    before = protected(host)
    old_index = (host["web"] / "index.html").read_bytes()
    if failure == "health":

        def health():
            if host["image"] == PROMOTION_IMAGE:
                raise RuntimeError("new health failed")

        monkeypatch.setattr(deploy, "health", health)
    else:
        original = deploy.atomic_copy

        def copy(source, target, *args):
            if (
                source.is_relative_to(host["root"] / "work")
                and target.name == "index.html"
            ):
                if failure == "interrupt":
                    raise KeyboardInterrupt()
                raise OSError("Web publication failed")
            return original(source, target, *args)

        monkeypatch.setattr(deploy, "atomic_copy", copy)
    args = promotion["args"]
    args.apply = True
    with pytest.raises((RuntimeError, OSError, KeyboardInterrupt)):
        deploy.server(args, PROMOTION_RELEASE)
    assert host["image"] == "sha256:legacy" and protected(host) == before
    assert (host["web"] / "index.html").read_bytes() == old_index
    assert not (host["production"] / ".local-deploy/pending.json").exists()
    no_builds(host)


def test_promotion_failed_rollback_leaves_pending_then_uses_existing_recovery(
    host, promotion, monkeypatch
):
    monkeypatch.setattr(
        deploy, "health", lambda: (_ for _ in ()).throw(RuntimeError("health failed"))
    )
    args = promotion["args"]
    args.apply = True
    with pytest.raises(RuntimeError, match="Rollback incomplete"):
        deploy.server(args, PROMOTION_RELEASE)
    pending = host["production"] / ".local-deploy/pending.json"
    attempt = json.loads(pending.read_text())["attempt"]
    monkeypatch.setattr(deploy, "health", lambda: None)
    deploy.server(
        argparse.Namespace(rollback=attempt, apply=True, stage_only=False, force=False),
        PROMOTION_RELEASE,
    )
    assert not pending.exists() and host["image"] == "sha256:legacy"
    no_builds(host)


@pytest.mark.parametrize(
    "change",
    [
        "root_symlink",
        "empty_index",
        "no_index",
        "private_root",
        "duplicate_nested",
        "unknown_nested",
        "null_files",
        "bad_hash",
        "backslash",
        "empty_component",
        "unicode",
    ],
)
def test_strict_manifest_and_root_boundaries(host, promotion, change, tmp_path):
    m = promotion["manifest"]
    if change == "root_symlink":
        (promotion["path"].parent / "link").symlink_to(
            promotion["dist"], target_is_directory=True
        )
        m["web_root"] = "link"
    if change == "empty_index":
        put(promotion["dist"] / "index.html", "")
    if change == "no_index":
        (promotion["dist"] / "index.html").unlink()
    if change in {"empty_index", "no_index"}:
        m["web_files"] = deploy.promotion_inventory(promotion["dist"])
        m["web_manifest_sha256"] = deploy.promotion_digest(m["web_files"])
    if change == "private_root":
        promotion["path"].parent.chmod(0o755)
    if change == "unknown_nested":
        m["provenance"]["unchecked"] = "x"
    if change == "null_files":
        m["web_files"] = None
    if change == "bad_hash":
        m["web_files"]["index.html"] = "not-a-digest"
    if change in {"backslash", "empty_component", "unicode"}:
        m["web_root"] = {
            "backslash": r"web\outside",
            "empty_component": "web//x",
            "unicode": "웹",
        }[change]
    args = promotion["write"]()
    if change == "duplicate_nested":
        text = (
            promotion["path"]
            .read_text()
            .replace(
                '"provenance": {',
                '"provenance": {"node_image":"sha256:' + "0" * 64 + '",',
            )
        )
        put(promotion["path"], text, 0o600)
        args.expected_manifest_sha256 = deploy.sha(promotion["path"])
    with pytest.raises(RuntimeError):
        deploy.server(args, PROMOTION_RELEASE)
    assert not host["activations"]


def test_staged_metadata_symlink_is_not_followed(host, promotion):
    info = deploy.load_promotion(promotion["args"], PROMOTION_RELEASE)
    prepared = deploy.prepare_promotion(info)
    (prepared / "promotion.json").unlink()
    (prepared / "promotion.json").symlink_to(host["production"] / ".env")
    with pytest.raises(RuntimeError, match="Symlink"):
        deploy.apply_server(
            prepared, PROMOTION_RELEASE, True, True, None, host["image"], promotion=info
        )
    assert not host["activations"]


def test_copy_race_is_revalidated_without_publication(host, promotion, monkeypatch):
    original = deploy.shutil.copyfile

    def corrupt(source, target):
        original(source, target)
        if target.name == "index.html":
            target.write_text("modified after original validation")

    monkeypatch.setattr(deploy.shutil, "copyfile", corrupt)
    args = promotion["args"]
    args.apply = True
    with pytest.raises(RuntimeError, match="Staged Web"):
        deploy.server(args, PROMOTION_RELEASE)
    assert not host["activations"]
    no_builds(host)


def test_promotion_cli_stage_only_and_wrapper_forwarding(host, promotion, monkeypatch):
    args = promotion["args"]
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            "local_deploy.py",
            "server",
            "--promote-manifest",
            args.promote_manifest,
            "--expected-manifest-sha256",
            args.expected_manifest_sha256,
            "--release",
            PROMOTION_RELEASE,
            "--stage-only",
        ],
    )
    monkeypatch.setattr(
        deploy, "settings", lambda: {"MONEY_NOTE_DEPLOY_BRANCH": "approved-controller"}
    )
    seen = []

    def revision(branch, *, clean):
        seen.append((branch, clean))
        return PROMOTION_CONTROLLER

    monkeypatch.setattr(deploy, "source_revision", revision)
    deploy.main()
    assert seen == [("approved-controller", True)]
    assert not host["activations"]
    assert (host["root"] / "work/deploy/.build.lock").is_file()
    wrapper = Path(__file__).resolve().parents[1] / "deploy-server.sh"
    assert 'server "$@"' in wrapper.read_text()
    no_builds(host)


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--release", PROMOTION_RELEASE],
        [
            "--release",
            PROMOTION_RELEASE,
            "--expected-manifest-sha256",
            "0" * 64,
            "--force",
        ],
        [
            "--release",
            PROMOTION_RELEASE,
            "--expected-manifest-sha256",
            "0" * 64,
            "--rollback",
            "x",
        ],
    ],
)
def test_incomplete_or_conflicting_promotion_cli_rejects_before_access(
    host, promotion, monkeypatch, extra
):
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        [
            "local_deploy.py",
            "server",
            "--promote-manifest",
            promotion["args"].promote_manifest,
            *extra,
        ],
    )
    monkeypatch.setattr(
        deploy,
        "settings",
        lambda: pytest.fail("settings accessed before CLI rejection"),
    )
    with pytest.raises(RuntimeError, match="Promotion requires"):
        deploy.main()
    assert not host["activations"]


def test_promotion_publication_keeps_index_last(host, promotion, monkeypatch):
    original = deploy.atomic_copy
    order = []

    def record(source, target, *args):
        order.append(target.relative_to(host["web"]).as_posix())
        return original(source, target, *args)

    monkeypatch.setattr(deploy, "atomic_copy", record)
    args = promotion["args"]
    args.apply = True
    deploy.server(args, PROMOTION_RELEASE)
    assert order[-1] == "index.html"


def test_manifest_cannot_authorize_production_as_artifact_root(host, promotion, monkeypatch):
    monkeypatch.setattr(deploy, "PRODUCTION", promotion["path"].parent)
    with pytest.raises(RuntimeError, match="artifact root"):
        deploy.load_promotion(promotion["args"], PROMOTION_RELEASE)
    assert not host["activations"]


def test_promotions_retain_current_and_previous_without_touching_apk(host, promotion):
    before = protected(host)
    for number in range(3):
        put(promotion["dist"] / "index.html", f"approved index {number}")
        web = deploy.promotion_inventory(promotion["dist"])
        promotion["manifest"]["web_files"] = web
        promotion["manifest"]["web_manifest_sha256"] = deploy.promotion_digest(web)
        args = promotion["write"]()
        args.apply = True
        deploy.server(args, PROMOTION_RELEASE)
    control = host["production"] / ".local-deploy"
    assert len(list((control / "backups").iterdir())) == 1
    assert len(list((control / "releases").iterdir())) == 2
    assert protected(host) == before
    no_builds(host)


def test_promotion_is_not_available_to_mobile_mode(host, promotion, monkeypatch):
    args = promotion["args"]
    monkeypatch.setattr(__import__("sys"), "argv", [
        "local_deploy.py", "mobile", "--promote-manifest", args.promote_manifest,
        "--expected-manifest-sha256", args.expected_manifest_sha256,
        "--release", PROMOTION_RELEASE,
    ])
    monkeypatch.setattr(deploy, "settings", lambda: pytest.fail("unexpected config read"))
    with pytest.raises(RuntimeError, match="Promotion requires"):
        deploy.main()
