@Timeout(Duration(minutes: 8))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/e4_targeted_fixture.dart';
import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

class RecoveryWorkspace extends E4Workspace {
  RecoveryWorkspace(super.root, {super.fault});
  Completer<void>? entered, release;
  bool onJournal = false;
  void pause({bool journal = false}) {
    entered = Completer();
    release = Completer();
    onJournal = journal;
  }

  Future<void> barrier(bool journal) async {
    if (entered != null && !entered!.isCompleted && onJournal == journal) {
      entered!.complete();
      await release!.future;
    }
  }

  @override
  Future<OfflineWorkspaceMetadata> loadMetadata() async {
    await barrier(false);
    return super.loadMetadata();
  }

  @override
  Future<List<OfflineJournalOperation>> loadJournal() async {
    await barrier(true);
    return super.loadJournal();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late Directory root;
  late SegmentedClientStore store;
  late RecoveryWorkspace workspace;
  late AppState state;
  late E4LegacyInstallation initial;
  void Function(String)? fileFault, sqlFault;
  var serial = 0;
  File getSource() => File('${workspace.root.path}/e4-source.json');
  File getB() => File('${workspace.root.path}/offline-mode/baseline.json');
  File getPending() =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 5);
    wire = await e4WireOracle();
  });
  tearDownAll(() => bridge.dispose());
  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    fileFault = sqlFault = null;
    root = Directory.systemTemp.createTempSync('mn-e4-a01-');
    store = SegmentedClientStore.open(
        root, GenerationFixture(bridge.fixture).cache,
        adapters: true, fault: (p) => sqlFault?.call(p));
    workspace = RecoveryWorkspace(root, fault: (p) => fileFault?.call(p));
    final api = TargetedApi(bridge, wire);
    await api.saveSession(bridge.token);
    state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    initial = await state.installSegmentedLegacyForIsolatedUse(store);
    await workspace.beginOnlineWrite(1);
  });
  tearDown(() {
    if (workspace.release != null && !workspace.release!.isCompleted) {
      workspace.release!.complete();
    }
    state.dispose();
    store.close();
    root.deleteSync(recursive: true);
  });

  // Independent connection: compare durable rows/bytes, not the recovery
  // return value. Byte BLOBs are checksummed only for this test observation.
  Map<String, dynamic> disk() {
    final db = sqlite3.open(store.path);
    try {
      final result = <String, dynamic>{
        'source': base64Encode(getSource().readAsBytesSync()),
        'B': base64Encode(getB().readAsBytesSync()),
        'pending': base64Encode(getPending().readAsBytesSync()),
      };
      for (final table in [
        'accepted',
        'installed',
        'frozen',
        'generation_roots',
        'objects'
      ]) {
        result[table] = db
            .select('SELECT * FROM $table ORDER BY 1,2')
            .map((r) => r.map(
                (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v)))
            .toList();
      }
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      return result;
    } finally {
      db.close();
    }
  }

  Future<(FrozenGeneration, OfflineBaseline)> prepare() async {
    final accepted = store.acceptedGeneration();
    final full = await store.verifyAcceptedForMaterialization(accepted);
    final bundle = store.withAcceptedRead(
        accepted, (r) => materializeLegacyRead(r, baselineFixture().user),
        materializationProof: full);
    final b = legacyBaseline(
        bundle, DateTime.utc(2026, 10, 15).add(Duration(seconds: ++serial)));
    final frozen = store.prepareFrozenGeneration(
        accepted, full, workspace.bindingFor(accepted, b, store.cache.key),
        frozenId: syncUuid(), finalAuthorityFence: () {});
    workspace.prepareLegacySource(frozen, () {});
    return (frozen, b);
  }

  Future<void> reopenAndRead(String id) async {
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final fresh = E4Workspace(root);
    await fresh.recoverLegacyHandoff(store);
    final b = await fresh.readFrozenBaseline(store, id, 1);
    final frozen = store.frozenGenerations().singleWhere((f) => f.id == id);
    expect(
        fresh.recoveryLineageFingerprint(b), frozen.binding['legacy_lineage']);
    expect(b.serverStateFingerprint, frozen.binding['legacy_fingerprint']);
    final oracle =
        await Process.run('${Directory.current.parent.path}/.venv/bin/python', [
      '${Directory.current.parent.path}/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
      workspace.root.path
    ]);
    expect(oracle.exitCode, 0, reason: oracle.stderr as String);
  }

  for (final journal in [false, true]) {
    for (final native in [false, true]) {
      test(
          'A01 delayed ${journal ? 'journal' : 'metadata'} recovery preserves newer ${native ? 'native' : 'legacy'} source',
          () async {
        await prepare();
        workspace.pause(journal: journal);
        final oldRecovery = workspace.recoverLegacyHandoff(store);
        await workspace.entered!.future;
        // A second recovery completes before the newer original AppState
        // request installs. No sleeps, new coordinator, or copied permit.
        await E4Workspace(root).recoverLegacyHandoff(store);
        await bridge.command({'command': 'mutate'});
        final String frozenId;
        if (native) {
          await state.refreshSegmentedForIsolatedUse(store);
          frozenId = initial.frozen.id;
        } else {
          frozenId = (await state.installSegmentedLegacyForIsolatedUse(store))
              .frozen
              .id;
        }
        final winner = disk();
        workspace.release!.complete();
        expect(await oldRecovery, null);
        expect(disk(), winner);
        await workspace.recoverLegacyHandoff(store);
        expect(disk(), winner);
        await reopenAndRead(frozenId);
        expect(disk(), winner);
      });
    }
  }

  test(
      'A01 same binding and generation but different frozen operation UUID is not the old owner',
      () async {
    final (a, b) = await prepare();
    workspace.pause();
    final oldRecovery = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    await E4Workspace(root).recoverLegacyHandoff(store);
    final accepted = store.acceptedGeneration();
    final full = await store.verifyAcceptedForMaterialization(accepted);
    final newer = store.prepareFrozenGeneration(accepted, full, a.binding,
        frozenId: syncUuid(), finalAuthorityFence: () {});
    expect(newer.checksum, a.checksum);
    expect(newer.id, isNot(a.id));
    workspace.prepareLegacySource(newer, () {});
    await workspace.replaceBaseline(b);
    await workspace.readFrozenBaseline(store, newer.id, 1);
    store.finishFrozenHandoff(newer, finalAuthorityFence: () {});
    final winner = disk();
    workspace.release!.complete();
    await oldRecovery;
    expect(disk(), winner);
    await reopenAndRead(newer.id);
    expect(disk(), winner);
  });

  test('A01 concurrent recoveries of a current unfinished owner are idempotent',
      () async {
    final (a, _) = await prepare();
    final b = getB().readAsBytesSync(),
        pending = getPending().readAsBytesSync();
    await Future.wait([
      workspace.recoverLegacyHandoff(store),
      E4Workspace(root).recoverLegacyHandoff(store)
    ]);
    expect(store.frozenGenerations().map((f) => f.id), [initial.frozen.id]);
    expect(store.frozenGenerations().any((f) => f.id == a.id), false);
    final after = disk();
    await workspace.recoverLegacyHandoff(store);
    expect(disk(), after);
    expect(getB().readAsBytesSync(), b);
    expect(getPending().readAsBytesSync(), pending);
    await reopenAndRead(initial.frozen.id);
  });

  test(
      'A01 current published preparation can still finalize after logout and recover twice',
      () async {
    final (a, b) = await prepare();
    await workspace.replaceBaseline(b);
    await state.logout();
    final pending = getPending().readAsBytesSync();
    expect((await workspace.recoverLegacyHandoff(store))!.id, a.id);
    final after = disk();
    await workspace.recoverLegacyHandoff(store);
    expect(disk(), after);
    expect(getPending().readAsBytesSync(), pending);
    await reopenAndRead(a.id);
  });

  test(
      'A01 source replacement in synchronous rename hook is rechecked before mutation',
      () async {
    final (a, _) = await prepare();
    late List<int> winner;
    fileFault = (point) {
      if (point == 'before_source_rename') {
        fileFault = null;
        // Another existing source owner wins at the last reentrant boundary.
        workspace.prepareLegacySource(initial.frozen, () {});
        winner = getSource().readAsBytesSync();
      }
    };
    expect(await workspace.recoverLegacyHandoff(store), null);
    expect(getSource().readAsBytesSync(), winner);
    expect(store.frozenGenerations().any((f) => f.id == a.id), true);
    expect(
        store
            .frozenGenerations()
            .any((f) => f.id == initial.frozen.id && f.installed),
        true);
  });

  for (final point in ['before_commit', 'after_commit']) {
    test('A01 storage failure $point preserves recoverable source and pending',
        () async {
      final (a, _) = await prepare();
      final old = disk();
      sqlFault = (p) {
        if (p == point) {
          sqlFault = null;
          throw StateError('A01 injected $point');
        }
      };
      await expectLater(
          workspace.recoverLegacyHandoff(store),
          throwsA(isA<StateError>()
              .having((e) => e.message, 'message', 'A01 injected $point')));
      expect(getPending().readAsBytesSync(), base64Decode(old['pending']));
      expect(getB().readAsBytesSync(), base64Decode(old['B']));
      if (point == 'before_commit') {
        expect(disk(), old);
        expect(store.frozenGenerations().any((f) => f.id == a.id), true);
      } else {
        expect(store.frozenGenerations().any((f) => f.id == a.id), false);
      }
      await workspace.recoverLegacyHandoff(store);
      await reopenAndRead(initial.frozen.id);
    });
  }

  test(
      'A01 actual SQLITE_BUSY at COMMIT restores the still-owned prepared source',
      () async {
    await prepare();
    final before = disk();
    final reader = sqlite3.open(store.path);
    fileFault = (p) {
      if (p == 'before_source_rename') {
        fileFault = null;
        reader.execute('BEGIN DEFERRED');
        reader.select('SELECT * FROM frozen'); // real SHARED lock
      }
    };
    try {
      await expectLater(
          workspace.recoverLegacyHandoff(store),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'STORE_BUSY')));
      expect(disk(), before);
    } finally {
      reader.execute('ROLLBACK');
      reader.close();
    }
    await workspace.recoverLegacyHandoff(store);
    await reopenAndRead(initial.frozen.id);
  });

  for (final field in ['namespace', 'binding']) {
    test(
        'A01 wrong source $field fails closed without modifying source/pins/B/pending',
        () async {
      final source =
          jsonDecode(getSource().readAsStringSync()) as Map<String, dynamic>;
      source[field] = 'f' * 64;
      getSource().writeAsStringSync(jsonEncode(source), flush: true);
      final before = disk();
      await expectLater(
          workspace.recoverLegacyHandoff(store),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'FROZEN_BINDING_INVALID')));
      expect(disk(), before);
    });
  }

  test('A01 failed source rename cannot discard the current preparation',
      () async {
    await prepare();
    final before = disk();
    fileFault = (p) {
      if (p == 'before_source_rename') throw StateError('A01 rename');
    };
    await expectLater(
        workspace.recoverLegacyHandoff(store), throwsA(isA<StateError>()));
    expect(disk(), before);
    fileFault = null;
    await workspace.recoverLegacyHandoff(store);
    await reopenAndRead(initial.frozen.id);
  });

  test(
      'A01 interrupted source restore releases only the abandoned preparation on reopen',
      () async {
    final (a, _) = await prepare();
    final prepared = jsonDecode(getSource().readAsStringSync());
    // Exact durable state of process death after restore but before SQL COMMIT:
    // old installed source/B, plus the rolled-back prepared SQL owner.
    getSource().writeAsStringSync(jsonEncode(prepared['previous_source']),
        flush: true);
    final b = getB().readAsBytesSync(),
        pending = getPending().readAsBytesSync();
    await reopenAndRead(initial.frozen.id);
    expect(store.frozenGenerations().any((f) => f.id == a.id), false);
    expect(getB().readAsBytesSync(), b);
    expect(getPending().readAsBytesSync(), pending);
    expect(
        (await state.installSegmentedLegacyForIsolatedUse(store))
            .frozen
            .installed,
        true);
  });

  test(
      'A01 delayed finalization cannot release the newer installed frozen owner',
      () async {
    final (_, b) = await prepare();
    await workspace.replaceBaseline(b);
    workspace.pause();
    final oldRecovery = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    await E4Workspace(root).recoverLegacyHandoff(store);
    await bridge.command({'command': 'mutate'});
    final newer = await state.installSegmentedLegacyForIsolatedUse(store);
    final winner = disk();
    workspace.release!.complete();
    expect(await oldRecovery, null);
    expect(disk(), winner);
    await reopenAndRead(newer.frozen.id);
  });

  test(
      'A01 current uncommitted native source restores its predecessor idempotently',
      () async {
    await bridge.command({'command': 'mutate'});
    await state.publishSegmentedForIsolatedUse(store);
    workspace.prepareSegmentedSource(store, store.acceptedGeneration(), () {});
    final b = getB().readAsBytesSync(),
        pending = getPending().readAsBytesSync();
    await workspace.recoverLegacyHandoff(store);
    expect(jsonDecode(getSource().readAsStringSync())['frozen'],
        initial.frozen.id);
    final restored = disk();
    await workspace.recoverLegacyHandoff(store);
    expect(disk(), restored);
    expect(getB().readAsBytesSync(), b);
    expect(getPending().readAsBytesSync(), pending);
    await reopenAndRead(initial.frozen.id);
  });

  test('A01 native SQL ownership fence rejects a stale installed sequence',
      () async {
    final previous = store.installedGeneration();
    await bridge.command({'command': 'mutate'});
    await state.refreshSegmentedForIsolatedUse(store);
    final winner = disk();
    var called = false;
    expect(
        () => store.restoreUncommittedSource(previous, restoreSource: () {
              called = true;
            }),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'PUBLICATION_CONFLICT')));
    expect(called, false);
    expect(disk(), winner);
    await reopenAndRead(initial.frozen.id);
  });

  test('A01 native ownership transaction rejects asynchronous file callbacks',
      () async {
    final before = disk();
    expect(
        () => store.restoreUncommittedSource(store.installedGeneration(),
            restoreSource: () async {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'ASYNC_PUBLICATION_FENCE')));
    expect(disk(), before);
  });

  test(
      'A01 restored native source retains legacy B and releases only its abandoned preparation',
      () async {
    await state.refreshSegmentedForIsolatedUse(store);
    final (a, _) = await prepare();
    final source = jsonDecode(getSource().readAsStringSync());
    getSource()
        .writeAsStringSync(jsonEncode(source['previous_source']), flush: true);
    final b = getB().readAsBytesSync(),
        pending = getPending().readAsBytesSync();
    await reopenAndRead(initial.frozen.id);
    expect(store.frozenGenerations().any((f) => f.id == a.id), false);
    expect(getB().readAsBytesSync(), b);
    expect(getPending().readAsBytesSync(), pending);
  });

  test(
      'A01 first legacy preparation with a native-only predecessor is recoverable without inventing B',
      () async {
    final nativeRoot = Directory.systemTemp.createTempSync('mn-e4-a01-native-');
    final nativeStore =
        SegmentedClientStore.open(nativeRoot, store.cache, adapters: true);
    final nativeWorkspace = E4Workspace(nativeRoot);
    final nativeState = AppState(state.api, offlineStore: nativeWorkspace)
      ..user = baselineFixture().user;
    try {
      await nativeState.refreshSegmentedForIsolatedUse(nativeStore);
      final accepted = nativeStore.acceptedGeneration();
      final proof =
          await nativeStore.verifyAcceptedForMaterialization(accepted);
      final bundle = nativeStore.withAcceptedRead(
          accepted, (r) => materializeLegacyRead(r, baselineFixture().user),
          materializationProof: proof);
      final baseline = legacyBaseline(bundle, DateTime.utc(2026, 10, 16));
      final a = nativeStore.prepareFrozenGeneration(accepted, proof,
          nativeWorkspace.bindingFor(accepted, baseline, nativeStore.cache.key),
          frozenId: syncUuid(), finalAuthorityFence: () {});
      final sourceFile = File('${nativeWorkspace.root.path}/e4-source.json');
      final previous = sourceFile.readAsBytesSync();
      nativeWorkspace.prepareLegacySource(a, () {});
      sourceFile.writeAsBytesSync(previous,
          flush: true); // crashed restore/SQL rollback
      await nativeWorkspace.beginOnlineWrite(1);
      final pending =
          File('${nativeWorkspace.root.path}/offline-mode/online-write-1.json');
      final bytes = pending.readAsBytesSync();
      await nativeWorkspace.recoverLegacyHandoff(nativeStore);
      expect(nativeStore.frozenGenerations(), isEmpty);
      expect(sourceFile.readAsBytesSync(), previous);
      expect(
          File('${nativeWorkspace.root.path}/offline-mode/baseline.json')
              .existsSync(),
          false);
      expect(pending.readAsBytesSync(), bytes);
      await nativeWorkspace.recoverLegacyHandoff(nativeStore);
      expect(sourceFile.readAsBytesSync(), previous);
    } finally {
      nativeState.dispose();
      nativeStore.close();
      nativeRoot.deleteSync(recursive: true);
    }
  });
}
