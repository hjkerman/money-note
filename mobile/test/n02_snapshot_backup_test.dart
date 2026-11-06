import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';
import 'package:money_note_mobile/src/snapshot_file_codec.dart';

import 'authoritative_acquisition_test.dart'
    show BundleTransport, InterruptedStore, card;
import 'authoritative_bundle_test.dart' show owner, specimen, reseal;
import 'local_snapshot_repository_test.dart' show PausedSnapshotFile;

class LaunchTransport extends BundleTransport {
  bool mutateAfterBundle = false;
  Completer<void>? snapshotRequested;
  Completer<void>? snapshotRelease;
  Object? afterBundleFailure;
  @override
  Future<http.Response> request(http.Request r) async {
    if (r.url.path == '/api/auth/me') {
      calls.add('${r.method} ${r.url.path}');
      return http.Response(
          jsonEncode({
            'id': 1,
            'username': 'owner',
            'display_name': 'Owner',
            'share_pin_needs_change': false
          }),
          200);
    }
    if (r.url.path == '/api/admin/snapshot') {
      calls.add('${r.method} ${r.url.path}');
      final bytes = utf8.encode(jsonEncode(wire['snapshot']));
      snapshotRequested?.complete();
      if (snapshotRelease != null) await snapshotRelease!.future;
      return http.Response.bytes(bytes, 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    }
    final response = await super.request(r);
    if (r.url.path == '/api/authoritative-state') {
      if (mutateAfterBundle) {
        // Represent an independent client's T2 edit. Never returned as T1.
        wire['snapshot']['exported_at'] = '2026-09-18T01:02:03Z';
        reseal(wire);
      }
      if (afterBundleFailure != null) throw afterBundleFailure!;
    }
    return response;
  }
}

class ReadbackPausedFile extends PausedSnapshotFile {
  ReadbackPausedFile(super.delegate, super.written, super.resume);
  @override
  Future<File> writeAsBytes(List<int> bytes,
          {FileMode mode = FileMode.write, bool flush = false}) =>
      delegate.writeAsBytes(bytes, mode: mode, flush: flush);
  @override
  Stream<List<int>> openRead([int? start, int? end]) async* {
    yield* delegate.openRead(start, end);
    written.complete(path);
    await resume.future;
  }
}

class FailedBackupRepository extends LocalSnapshotRepository {
  FailedBackupRepository(Directory dir)
      : super(directoryProvider: () async => dir);
  @override
  Future<List<LocalSnapshotInfo>> save(Uint8List bytes,
      {void Function()? beforePublish}) async {
    beforePublish?.call();
    throw const FileSystemException('injected archive failure');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory root;
  late LaunchTransport t;
  late OfflineStore store;
  late LocalSnapshotRepository repo;
  late AppState s;
  late File baselineFile;
  late List<MethodCall> shares;
  const secure = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  const share = MethodChannel('dev.fluttercommunity.plus/share');

  AppState makeState({LocalSnapshotRepository? repository}) => AppState(t.api,
      offlineStore: store,
      snapshotRepository: repository ?? repo,
      connectivityRetryDelay: (_) async {})
    ..user = owner
    ..isBootstrapping = false;

  setUp(() async {
    root = await Directory.systemTemp.createTemp('mn-n02-test-');
    t = LaunchTransport();
    store = OfflineStore(directoryProvider: () async => root);
    repo = LocalSnapshotRepository(directoryProvider: () async => root);
    s = makeState();
    baselineFile = File('${root.path}/offline-mode/baseline.json');
    shares = [];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(secure, (call) async => 'synthetic-token');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(share, (call) async {
      shares.add(call);
      return 'success';
    });
  });
  tearDown(() async {
    // dispose is idempotent neither here nor in ChangeNotifier: tests which
    // dispose mid-save replace s with a fresh object for teardown.
    s.dispose();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(secure, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(share, null);
    await root.delete(recursive: true);
  });

  int calls(String path) => t.calls.where((c) => c == 'GET $path').length;

  Future<Map<String, dynamic>> savedSnapshot() async {
    final items = await repo.list();
    expect(items, hasLength(1));
    expect(items.single.filename, endsWith('.money-note-snapshot.json.gz'));
    final text = await repo.readText(items.single.filename);
    // The existing request preparation preserves JSON verbatim and size limits.
    SnapshotRestoreRequest.prepare('synthetic-password', text);
    return jsonDecode(text) as Map<String, dynamic>;
  }

  for (final event in ['startup', 'login', 'resume']) {
    test('$event archives exactly its published Bundle without Snapshot GET',
        () async {
      final expected = jsonDecode(jsonEncode(t.wire['snapshot']));
      if (event == 'startup') {
        s.user = null;
        s.isBootstrapping = true;
        await s.bootstrap();
      } else if (event == 'login') {
        s.user = null;
        await s.login('owner', 'synthetic-password');
      } else {
        await s.resumeFromBackground();
      }
      expect(calls('/api/authoritative-state'), 1);
      expect(calls('/api/admin/snapshot'), 0);
      expect(await savedSnapshot(), expected);
      expect((await store.loadBaseline())!.authoritativeSnapshot, expected);
      expect(s.summary, isNotNull);
      expect(s.localSnapshots, hasLength(1));
      expect(s.statusMessage, isNot(contains('실패')));
      // Restore-server validation is also run on this task-owned output.
      final output = Platform.environment['N02_EVIDENCE'];
      if (output != null) {
        await File('$output/$event-snapshot.json').writeAsString(
            await repo.readText(s.localSnapshots.single.filename));
      }
    });
  }

  test('ordinary and post-mutation refresh add no automatic backup', () async {
    await s.refresh(notify: false);
    expect(await repo.list(), isEmpty);
    expect(await card(s), isTrue);
    expect(calls('/api/authoritative-state'), 2);
    expect(calls('/api/admin/snapshot'), 0);
    expect(await repo.list(), isEmpty);
  });

  test('T2 external change does not replace approved T1 recovery point',
      () async {
    final t1 = jsonDecode(jsonEncode(t.wire['snapshot']));
    t.mutateAfterBundle = true;
    await s.resumeFromBackground();
    expect(t.wire['snapshot'], isNot(t1));
    expect(await savedSnapshot(), t1);
    expect(calls('/api/admin/snapshot'), 0);
  });

  test('archive failure preserves successful baseline, UI and old backups',
      () async {
    final old = await repo.save(encodeSnapshotJson(t.wire['snapshot']));
    final oldText = await repo.readText(old.single.filename);
    s.dispose();
    s = makeState(repository: FailedBackupRepository(root));
    const pending = PendingOnlineWrite(
        1, 'synthetic-unknown', OnlineWriteStatus.outcomeUnknown,
        retryIdentity: 'synthetic-retry');
    await store.savePendingOnlineWrite(pending);
    await s.resumeFromBackground();
    expect(s.summary, isNotNull);
    expect(s.lastSuccessfulSyncAt, isNotNull);
    expect(await store.loadBaseline(), isNotNull);
    expect(await repo.readText(old.single.filename), oldText);
    expect(await repo.list(), hasLength(1));
    expect(calls('/api/admin/snapshot'), 0);
    expect(s.statusMessage, '앱 복귀 동기화 완료');
    expect((await store.loadPendingOnlineWrite(owner.id))!.toJson(),
        pending.toJson());
    expect(s.onlineWriteStatus, OnlineWriteStatus.outcomeUnknown);
  });

  test('failed durable publication cannot create a backup', () async {
    s.dispose();
    store = InterruptedStore(root)..failPublication = true;
    s = makeState();
    await s.resumeFromBackground();
    expect(s.summary, isNull);
    expect(await store.loadBaseline(), isNull);
    expect(await repo.list(), isEmpty);
    expect(calls('/api/admin/snapshot'), 0);
  });

  test('failed strict admission cannot create a backup', () async {
    t.getBody = '{}';
    await s.resumeFromBackground();
    expect(s.summary, isNull);
    expect(await repo.list(), isEmpty);
    expect(await store.loadBaseline(), isNull);
  });

  test('superseded refresh response cannot back up or replace newer baseline',
      () async {
    final requested = Completer<void>(), release = Completer<void>();
    t.requested = requested;
    t.release = release;
    final older = s.resumeFromBackground();
    await requested.future;
    await s.refresh(notify: false);
    final durable = await baselineFile.readAsBytes();
    release.complete();
    await older;
    expect(await baselineFile.readAsBytes(), durable);
    expect(await repo.list(), isEmpty);
    expect(calls('/api/admin/snapshot'), 0);
  });

  test('logout during acquisition prevents stale backup', () async {
    final requested = Completer<void>(), release = Completer<void>();
    t.requested = requested;
    t.release = release;
    final operation = s.resumeFromBackground();
    await requested.future;
    await s.logout();
    release.complete();
    await operation;
    expect(s.user, isNull);
    expect(await repo.list(), isEmpty);
    expect(await store.loadBaseline(), isNull);
  });

  // Actual file IO pauses inside the repository, after successful baseline/UI
  // publication. Revocation must prevent rename AND retention of the old 30.
  for (final revocation in [
    'logout',
    'same-principal login',
    'dispose',
    'new refresh',
    'offline',
    'finalizing'
  ]) {
    test('$revocation during gzip write prevents publication and retention',
        () async {
      final directory = await Directory('${root.path}/snapshots').create();
      final old = encodeSnapshotJson(t.wire['snapshot']);
      for (var i = 0; i < 30; i++) {
        await File('${directory.path}/old-$i.money-note-snapshot.json')
            .writeAsBytes(old);
      }
      final written = Completer<String>(), release = Completer<void>();
      final parent = Zone.current;
      final operation = IOOverrides.runZoned(() => s.resumeFromBackground(),
          createFile: (path) {
        final file = parent.run(() => File(path));
        return path.endsWith('.pending')
            ? PausedSnapshotFile(file, written, release)
            : file;
      });
      await written.future;
      final durable = await baselineFile.readAsBytes();
      switch (revocation) {
        case 'logout':
          await s.logout();
        case 'same-principal login':
          await s.login('owner', 'synthetic-password');
        case 'dispose':
          s.dispose();
        case 'new refresh':
          await s.refresh(notify: false);
        case 'offline':
          s.connectivityMode = ConnectivityMode.offline;
        case 'finalizing':
          s.connectivityMode = ConnectivityMode.reconciliationFinalizing;
      }
      release.complete();
      if (revocation == 'dispose') {
        // Existing resume finally notifies even after dispose; its lifecycle
        // exception is unrelated to saving, and cannot publish any backup.
        await expectLater(operation, throwsA(isA<FlutterError>()));
        s = makeState();
      } else {
        await operation;
      }
      final listed = await repo.list();
      // A second authorized login may create its own new backup and prune one.
      if (revocation == 'same-principal login') {
        expect(listed, hasLength(30));
        expect(listed.where((x) => x.filename.endsWith('.gz')), hasLength(1));
      } else {
        expect(listed, hasLength(30));
        expect(listed.every((x) => x.filename.endsWith('.json')), isTrue);
      }
      if (revocation == 'offline' || revocation == 'finalizing') {
        expect(await baselineFile.readAsBytes(), durable);
      }
      expect(directory.listSync().where((x) => x.path.endsWith('.pending')),
          isEmpty);
      expect(calls('/api/admin/snapshot'), 0);
    });
  }

  test('authority lost during gzip readback prevents final publication',
      () async {
    final written = Completer<String>(), release = Completer<void>();
    final parent = Zone.current;
    final operation = IOOverrides.runZoned(() => s.resumeFromBackground(),
        createFile: (path) {
      final file = parent.run(() => File(path));
      return path.endsWith('.pending')
          ? ReadbackPausedFile(file, written, release)
          : file;
    });
    await written.future;
    await s.logout();
    release.complete();
    await operation;
    expect(await repo.list(), isEmpty);
    expect(calls('/api/admin/snapshot'), 0);
  });

  test('retention rechecks authority after asynchronous listing', () async {
    final directory = await Directory('${root.path}/snapshots').create();
    for (var i = 0; i < 30; i++) {
      await File('${directory.path}/old-$i.money-note-snapshot.json')
          .writeAsBytes(encodeSnapshotJson(t.wire['snapshot']));
    }
    var checks = 0;
    await expectLater(
        repo.save(encodeSnapshotJson(t.wire['snapshot']), beforePublish: () {
          checks++;
          if (checks == 3) throw StateError('revoked before pruning');
        }),
        throwsStateError);
    // The T1 backup was valid when atomically published; no old backup may
    // subsequently be deleted under a revoked ticket. A later save prunes.
    expect(await repo.list(), hasLength(31));
    expect(directory.listSync().where((x) => x.path.endsWith('.json')),
        hasLength(30));
  });

  test('final synchronous authority check rejects before atomic rename',
      () async {
    var checks = 0;
    await expectLater(
        repo.save(encodeSnapshotJson(t.wire['snapshot']), beforePublish: () {
          checks++;
          if (checks == 2) throw StateError('revoked at publication');
        }),
        throwsStateError);
    expect(checks, 2);
    expect(await repo.list(), isEmpty);
  });

  test('final guard and rename have no asynchronous revocation gap', () async {
    var checks = 0;
    bool? publishedBeforeNextMicrotask;
    await repo.save(encodeSnapshotJson(t.wire['snapshot']), beforePublish: () {
      checks++;
      if (checks == 2) {
        scheduleMicrotask(() {
          publishedBeforeNextMicrotask = Directory('${root.path}/snapshots')
              .listSync()
              .any((x) => x.path.endsWith('.json.gz'));
        });
      }
    });
    expect(publishedBeforeNextMicrotask, isTrue);
  });

  test('guarded successful save keeps mixed retention at 30', () async {
    for (var i = 0; i < 30; i++) {
      final dir = await Directory('${root.path}/snapshots').create();
      final f = File('${dir.path}/old-$i.money-note-snapshot.json');
      await f.writeAsBytes(encodeSnapshotJson(t.wire['snapshot']));
      await f.setLastModified(DateTime.utc(2020, 1, 1, 0, 0, i));
    }
    await s.resumeFromBackground();
    final items = await repo.list();
    expect(items, hasLength(30));
    expect(items.where((x) => x.filename.endsWith('.gz')), hasLength(1));
    expect(items.any((x) => x.filename == 'old-0.money-note-snapshot.json'),
        isFalse);
  });

  test('recovery swallowing an API error keeps independent GET fallback',
      () async {
    s.networkUnavailable = true;
    t.afterBundleFailure =
        MoneyNoteApiException('synthetic recovery rejection');
    await s.resumeFromBackground();
    expect(await store.loadBaseline(), isNull);
    expect(s.summary, isNull);
    expect(calls('/api/authoritative-state'), 1);
    expect(calls('/api/admin/snapshot'), 1);
    expect(await savedSnapshot(), t.wire['snapshot']);
  });

  test('recovery fallback rejects authentication change during Snapshot GET',
      () async {
    s.networkUnavailable = true;
    t.snapshotRequested = Completer<void>();
    t.snapshotRelease = Completer<void>();
    final operation = s.resumeFromBackground();
    await t.snapshotRequested!.future;
    await s.logout();
    t.snapshotRelease!.complete();
    await operation;
    expect(calls('/api/admin/snapshot'), 1);
    expect(await repo.list(), isEmpty);
    expect(s.user, isNull);
  });

  test('recovery fallback rechecks authentication after gzip IO', () async {
    s.networkUnavailable = true;
    final written = Completer<String>(), release = Completer<void>();
    final parent = Zone.current;
    final operation = IOOverrides.runZoned(() => s.resumeFromBackground(),
        createFile: (path) {
      final file = parent.run(() => File(path));
      return path.endsWith('.pending')
          ? PausedSnapshotFile(file, written, release)
          : file;
    });
    await written.future;
    await s.logout();
    release.complete();
    await operation;
    expect(calls('/api/admin/snapshot'), 1);
    expect(await repo.list(), isEmpty);
  });

  test('recovery identifying a restored session keeps independent fallback',
      () async {
    s.user = null;
    s.networkUnavailable = true;
    await s.resumeFromBackground();
    expect(calls('/api/auth/me'), 1);
    expect(calls('/api/authoritative-state'), 1);
    expect(calls('/api/admin/snapshot'), 1);
    expect(await store.loadBaseline(), isNotNull);
    expect(await repo.list(), hasLength(1));
  });

  test('successful recovery preserves its independent Snapshot GET', () async {
    s.networkUnavailable = true;
    await s.resumeFromBackground();
    expect(calls('/api/authoritative-state'), 1);
    expect(calls('/api/admin/snapshot'), 1);
    expect(await store.loadBaseline(), isNotNull);
    expect(await repo.list(), hasLength(1));
  });

  test('Offline return adds no automatic backup or finalizing trigger',
      () async {
    await s.refresh(notify: false);
    expect(await s.enterOfflineMode(), isTrue);
    t.calls.clear();
    await s.resumeFromBackground();
    expect(s.isReconciliationRequired, isTrue);
    expect(calls('/api/authoritative-state'), 0);
    expect(calls('/api/admin/snapshot'), 0);
    expect(await repo.list(), isEmpty);
  });

  test('empty manual share still downloads independent Snapshot', () async {
    await s.shareCurrentSnapshot();
    expect(calls('/api/authoritative-state'), 0);
    expect(calls('/api/admin/snapshot'), 1);
    expect(shares, hasLength(1));
    expect(await repo.list(), hasLength(1));
  });

  test('outcomeUnknown remains unresolved and cannot be settled by backup',
      () async {
    t.losePost = true;
    expect(await card(s), isFalse);
    final pending = await store.loadPendingOnlineWrite(owner.id);
    expect(pending!.status, OnlineWriteStatus.outcomeUnknown);
    await s.resumeFromBackground();
    expect((await store.loadPendingOnlineWrite(owner.id))!.toJson(),
        pending.toJson());
    expect(s.onlineWriteStatus, OnlineWriteStatus.outcomeUnknown);
    // Lost mutation response entered the existing connectivity-recovery branch.
    // Its independent backup fallback is preserved, and cannot settle pending.
    expect(calls('/api/admin/snapshot'), 1);
  });

  for (final delta in [-1, 0, 1]) {
    test('snapshot-only UTF8 serialization size boundary $delta', () {
      final value = {'x': 'a' * (snapshotJsonLimit - 8 + delta)};
      if (delta > 0) {
        expect(() => encodeSnapshotJson(value), throwsFormatException);
      } else {
        expect(encodeSnapshotJson(value).length, snapshotJsonLimit + delta);
      }
    });
  }

  test('existing synthetic 10K Bundle snapshot remains restorable', () async {
    final fixtures = Platform.environment['P2_N01_FIXTURES'];
    if (fixtures == null) fail('task-owned synthetic fixture copy required');
    final wire =
        jsonDecode(await File('$fixtures/10000-bundle.raw').readAsString())
            as Map<String, dynamic>;
    // Use the actual strict admission before passing Snapshot to the encoder.
    final admitted = AuthoritativeBundle.decode(utf8.encode(jsonEncode(wire)));
    final bytes = encodeSnapshotJson(admitted.wire['snapshot']);
    final items = await repo.save(bytes, beforePublish: () {});
    expect(await repo.readText(items.single.filename), utf8.decode(bytes));
    final output = Platform.environment['N02_EVIDENCE'];
    if (output != null) {
      await File('$output/10k-snapshot.json').writeAsBytes(bytes);
    }
  });

  test('snapshot-only serialization is bounded and preserves immutable shape',
      () {
    final admitted =
        AuthoritativeBundle.decode(utf8.encode(jsonEncode(specimen())));
    final encoded = encodeSnapshotJson(admitted.wire['snapshot']);
    expect(jsonDecode(utf8.decode(encoded)), t.wire['snapshot']);
    expect(() => admitted.wire['snapshot']['revision'] = 1,
        throwsUnsupportedError);
    expect(encoded.length, lessThan(snapshotJsonLimit));
  });
}
