"""Exercise real file publication/rollback in tmp_path; Docker and health are fakes."""

import argparse
import importlib.util
import io
import json
from pathlib import Path
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
