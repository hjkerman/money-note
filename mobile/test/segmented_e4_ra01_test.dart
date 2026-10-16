@Timeout(Duration(minutes: 8))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'segmented_e4_a01_test.dart' show RecoveryWorkspace;
import 'support/e4_targeted_fixture.dart';
import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

class Ra01Api extends TargetedApi {
  Ra01Api(super.bridge, super.wire);
  void Function()? credentialRead;
  @override
  T withIsolatedTransport<T>(
          T Function(http.Client, String, String? Function()) create) =>
      super.withIsolatedTransport(
          (client, origin, credential) => create(client, origin, () {
                credentialRead?.call();
                return credential();
              }));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late Directory root;
  late SegmentedClientStore store;
  late RecoveryWorkspace workspace;
  late Ra01Api api;
  late AppState state;
  void Function(String)? fileFault, sqlFault;
  var serial = 0;
  File source() => File('${workspace.root.path}/e4-source.json');
  File baseline() => File('${workspace.root.path}/offline-mode/baseline.json');
  File pending() =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  Map<String, dynamic> sourceJson() => jsonDecode(source().readAsStringSync());
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 6);
    wire = await e4WireOracle();
  });
  tearDownAll(() => bridge.dispose());
  setUp(() async {
    await bridge.command({'command': 'advance', 'seconds': 901});
    FlutterSecureStorage.setMockInitialValues({});
    root = Directory.systemTemp.createTempSync('mn-e4-ra01-unit-');
    fileFault = sqlFault = null;
    store = SegmentedClientStore.open(
        root, GenerationFixture(bridge.fixture).cache,
        adapters: true, fault: (p) => sqlFault?.call(p));
    workspace = RecoveryWorkspace(root, fault: (p) => fileFault?.call(p));
    api = Ra01Api(bridge, wire);
    await api.saveSession(bridge.token);
    state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    await workspace
        .beginOnlineWrite(1); // outcomeUnknown is never retirement proof.
  });
  tearDown(() {
    bridge.before = null;
    api.credentialRead = null;
    if (workspace.release != null && !workspace.release!.isCompleted) {
      workspace.release!.complete();
    }
    state.dispose();
    store.close();
    root.deleteSync(recursive: true);
  });

  Map<String, dynamic> disk() {
    final d = sqlite3.open(store.path);
    try {
      expect(d.select('PRAGMA foreign_key_check'), isEmpty);
      return {
        'source': source().existsSync()
            ? base64Encode(source().readAsBytesSync())
            : null,
        'baseline': baseline().existsSync()
            ? base64Encode(baseline().readAsBytesSync())
            : null,
        'pending': base64Encode(pending().readAsBytesSync()),
        for (final table in [
          'accepted',
          'installed',
          'frozen',
          'generation_roots',
          'objects'
        ])
          table: d
              .select('SELECT * FROM $table ORDER BY 1,2')
              .map((r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v)))
              .toList()
      };
    } finally {
      d.close();
    }
  }

  Future<FrozenGeneration> legacy() async =>
      (await state.installSegmentedLegacyForIsolatedUse(store)).frozen;

  Future<FrozenGeneration> prepareLegacy() async {
    final g = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(g);
    final bundle = store.withAcceptedRead(
        g, (r) => materializeLegacyRead(r, baselineFixture().user),
        materializationProof: proof);
    final b = legacyBaseline(
        bundle, DateTime.utc(2026, 10, 17).add(Duration(seconds: ++serial)));
    final f = store.prepareFrozenGeneration(
        g, proof, workspace.bindingFor(g, b, store.cache.key),
        frozenId: syncUuid(), finalAuthorityFence: () {});
    workspace.prepareLegacySource(f, () {});
    return f;
  }

  Future<void> frozenRead(FrozenGeneration f, {bool process = false}) async {
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final fresh = E4Workspace(root);
    await fresh.recoverLegacyHandoff(store);
    final b = await fresh.readFrozenBaseline(store, f.id, 1);
    expect(fresh.recoveryLineageFingerprint(b), f.binding['legacy_lineage']);
    expect(b.serverStateFingerprint, f.binding['legacy_fingerprint']);
    expect(b.authoritativeSnapshot!['snapshot_id'], f.binding['snapshot_id']);
    final repo = Directory.current.parent.path;
    final oracle = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
      workspace.root.path
    ]);
    expect(oracle.exitCode, 0, reason: oracle.stderr as String);
    if (process) {
      File('${root.path}/owned').writeAsStringSync('synthetic E4-A01');
      File('${root.path}/expected.json').writeAsStringSync(jsonEncode({
        'target': store.acceptedGeneration().manifest!.target.toJson(),
        'frozen': f.id
      }));
      final child = await Process.run(
          '/home/hjkerman/.flutter/bin/flutter',
          [
            'test',
            '--no-pub',
            '--machine',
            '--dart-define=A01_ROOT=${root.path}',
            '--dart-define=A01_MODE=recover',
            '$repo/docs/benchmarks/t66e4-a01/crash_child_test.dart'
          ],
          workingDirectory: '$repo/mobile');
      expect(child.exitCode, 0,
          reason: (child.stdout as String)
              .split('\n')
              .where((l) => l.contains('"type":"error"'))
              .join('\n'));
    }
  }

  void preserved(Map<String, dynamic> before) {
    final after = disk();
    for (final key in ['baseline', 'pending', 'frozen']) {
      expect(after[key], before[key], reason: key);
    }
    final rows = after['objects'] as List;
    for (final object in before['objects'] as List) {
      expect(rows.singleWhere((r) => r['hash'] == object['hash']), object);
    }
    for (final pin in before['generation_roots'] as List) {
      expect(
          (after['generation_roots'] as List).singleWhere((r) =>
              r['generation_id'] == pin['generation_id'] &&
              r['hash'] == pin['hash']),
          pin);
    }
  }

  test(
      'RA01C genuine first native installation has no invented Frozen-B predecessor',
      () async {
    final marker = pending().readAsBytesSync();
    final r = await state.refreshSegmentedForIsolatedUse(store);
    expect(sourceJson()['previous_source'], null);
    expect(sourceJson()['previous_installation'], null);
    expect(sourceJson()['legacy_frozen'], null);
    expect(store.installedGeneration()!.id, r.authority.generationId);
    expect(store.frozenGenerations(), isEmpty);
    expect(baseline().existsSync(), false);
    expect(pending().readAsBytesSync(), marker);
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    await E4Workspace(root).recoverLegacyHandoff(store);
    expect((await store.recoverInstalledGeneration())!.id,
        r.authority.generationId);
    expect(() => requireSegmentedOfflineRecovery(),
        throwsA(isA<SegmentedException>()));
  });

  test(
      'RA01C initial native source preserves an ordinary unsourced legacy v4 file',
      () async {
    await workspace.replaceBaseline(baselineFixture());
    final before = disk();
    await state.refreshSegmentedForIsolatedUse(store);
    expect(sourceJson()['previous_source'], null);
    expect(sourceJson()['legacy_frozen'], null);
    expect(disk()['baseline'], before['baseline']);
    expect(disk()['pending'], before['pending']);
    expect(store.frozenGenerations(), isEmpty);
  });

  test(
      'RA01C valid legacy-to-native handoff preserves exact source lineage and fresh-process read',
      () async {
    final f = await legacy(), before = disk();
    final old = sourceJson();
    await bridge.command({'command': 'mutate'});
    final r = await state.refreshSegmentedForIsolatedUse(store);
    final s = sourceJson();
    expect(s['previous_source']['frozen'], old['frozen']);
    expect(s['legacy_frozen'], f.id);
    expect(s['legacy_binding'], f.checksum);
    expect(s['generation'], r.authority.generationId);
    expect(
        f.binding['legacy_fingerprint'], isNot(r.publication.target.syncRoot));
    preserved(before);
    await frozenRead(f, process: true);
    preserved(before);
  });

  test(
      'RA01C repeated native installation keeps shared descendants and immutable canonical B',
      () async {
    final f = await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    final before = disk(), installed = store.installedGeneration()!;
    for (var n = 0; n < 3; n++) {
      await state.refreshSegmentedForIsolatedUse(store);
      expect(store.installedGeneration()!.id, installed.id);
      expect(store.installedGeneration()!.sequence, installed.sequence);
      expect(sourceJson()['legacy_frozen'], f.id);
    }
    preserved(before);
    await frozenRead(f);
  });

  test(
      'RA01C confirmed retirement succeeds only after valid native source handoff',
      () async {
    final f = await legacy();
    final marker = (await workspace.loadPendingOnlineWrite(1))!;
    await workspace.savePendingOnlineWrite(marker.committed());
    final b = baseline().readAsBytesSync();
    final result = await state.refreshSegmentedForIsolatedUse(store);
    expect(result.pendingRemains, false);
    expect(pending().existsSync(), false);
    expect(sourceJson()['legacy_frozen'], f.id);
    expect(store.installedGeneration()!.id, result.authority.generationId);
    expect(baseline().readAsBytesSync(), b);
    await frozenRead(f);
  });

  test(
      'RA01C missing predecessor cannot retire even a confirmed pending marker',
      () async {
    await legacy();
    final marker = (await workspace.loadPendingOnlineWrite(1))!;
    await workspace.savePendingOnlineWrite(marker.committed());
    await prepareLegacy();
    final invalid = sourceJson()..['previous_source'] = null;
    source().writeAsStringSync(jsonEncode(invalid), flush: true);
    final before = disk();
    await expectLater(
        state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'SOURCE_PROVENANCE_REQUIRED')));
    expect(disk(), before);
    expect(pending().readAsBytesSync(), base64Decode(before['pending']));
  });

  test(
      'RA01C committed native current ownership does not require its obsolete historical hint',
      () async {
    final f = await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    final s = sourceJson()..['previous_source'] = null;
    source().writeAsStringSync(jsonEncode(s), flush: true);
    final before = disk();
    await state.refreshSegmentedForIsolatedUse(store);
    expect(sourceJson()['previous_source']['generation'], s['generation']);
    expect(sourceJson()['legacy_frozen'], f.id);
    preserved(before);
    await frozenRead(f);
  });

  test(
      'RA01C committed legacy B before native pointer finalization is a valid handoff base',
      () async {
    fileFault = (p) {
      if (p == 'after_legacy_commit') {
        fileFault = null;
        throw StateError('RA01 legacy already committed');
      }
    };
    await expectLater(state.installSegmentedLegacyForIsolatedUse(store),
        throwsA(isA<StateError>()));
    final f = store.frozenGenerations().single;
    expect(f.installed, true);
    expect(store.installedGeneration(), null);
    final before = disk();
    await state.refreshSegmentedForIsolatedUse(store);
    expect(sourceJson()['legacy_frozen'], f.id);
    expect(sourceJson()['previous_installation'], null);
    expect(sourceJson()['previous_source']['frozen'], f.id);
    preserved(before);
    await frozenRead(f, process: true);
  });

  test(
      'RA01C native current owner cannot forget a separately installed Frozen-B obligation',
      () async {
    await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    final s = sourceJson()
      ..['legacy_frozen'] = null
      ..['legacy_binding'] = null;
    source().writeAsStringSync(jsonEncode(s), flush: true);
    final before = disk();
    await expectLater(workspace.recoverLegacyHandoff(store),
        throwsA(isA<SegmentedException>()));
    await expectLater(state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<SegmentedException>()));
    expect(disk(), before);
  });

  test(
      'RA01C absent current sidecar with durable owners cannot silently become first installation',
      () async {
    await legacy();
    source()
        .deleteSync(); // Explicit pre-existing metadata damage, not a valid source.
    final before = disk();
    await expectLater(state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<SegmentedException>()));
    expect(disk(), before);
    expect(source().existsSync(), false); // No fabricated reconnection.
  });

  for (final native in [false, true]) {
    for (final variant in [
      'missing',
      'foreign_principal',
      'foreign_dataset',
      'foreign_epoch',
      'wrong_uuid',
      native ? 'wrong_sequence' : 'wrong_binding',
      'wrong_lineage',
      'cross_kind_alias'
    ]) {
      test(
          'RA01C invalid predecessor $variant native=$native preserves all recovery evidence',
          () async {
        await legacy();
        if (native) await state.refreshSegmentedForIsolatedUse(store);
        final preparation = await prepareLegacy();
        final s = sourceJson();
        final p = Map<String, dynamic>.from(s['previous_source']);
        if (variant == 'missing') {
          s['previous_source'] = null;
        } else {
          if (variant.startsWith('foreign_')) {
            final t = store.acceptedGeneration().manifest!.target.toJson()
              ..remove('sync_root');
            if (variant == 'foreign_principal') {
              t['principal_id'] = 2;
            } else {
              t['ns'][variant == 'foreign_epoch' ? 'epoch' : 'dataset_id'] =
                  syncUuid();
            }
            t['sync_root'] = objectHash('view', encodeC1(t));
            p['namespace'] =
                CacheNamespace.forTarget(syntheticOrigin, SyncTarget.parse(t))
                    .key;
          } else if (variant == 'wrong_uuid') {
            p[native ? 'generation' : 'frozen'] = syncUuid();
          } else if (variant == 'wrong_sequence') {
            p['sequence'] = (p['sequence'] as int) + 1;
          } else if (variant == 'wrong_binding') {
            p['binding'] = 'f' * 64;
          } else if (variant == 'cross_kind_alias') {
            if (native) {
              p['frozen'] = p['legacy_frozen'];
              p['binding'] = p['legacy_binding'];
            } else {
              p['legacy_frozen'] = p['frozen'];
              p['legacy_binding'] = p['binding'];
              p['frozen'] = preparation.id;
              p['binding'] = preparation.checksum;
            }
          } else if (native) {
            p['legacy_binding'] = preparation.checksum;
          } else {
            p['frozen'] = preparation.id;
            p['binding'] = preparation
                .checksum; // Prepared, not the installed lineage owner.
          }
          s['previous_source'] = p;
        }
        source().writeAsStringSync(jsonEncode(s), flush: true);
        final before = disk();
        await expectLater(workspace.recoverLegacyHandoff(store),
            throwsA(isA<SegmentedException>()));
        expect(disk(), before);
        final cache = store.cache;
        store.close();
        store = SegmentedClientStore.open(root, cache, adapters: true);
        await expectLater(E4Workspace(root).recoverLegacyHandoff(store),
            throwsA(isA<SegmentedException>()));
        expect(disk(), before);
      });
    }
  }

  test(
      'RA01C a changed predecessor after an async wait cannot be repaired from the old cached map',
      () async {
    await legacy();
    await prepareLegacy();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    final s = sourceJson()..['previous_source'] = null;
    source().writeAsStringSync(jsonEncode(s), flush: true);
    final before = disk();
    workspace.release!.complete();
    expect(await older,
        null); // Superseded data-only recovery, NOT installation success.
    expect(disk(), before);
    await expectLater(workspace.recoverLegacyHandoff(store),
        throwsA(isA<SegmentedException>()));
    expect(disk(), before);
  });

  for (final phase in ['prepare', 'commit']) {
    test(
        'RA01C source replacement in the $phase session getter is rechecked synchronously',
        () async {
      final f = await legacy(), before = disk();
      await bridge.command({'command': 'mutate'});
      List<int>? winner;
      void replace() {
        api.credentialRead = null;
        fileFault = sqlFault = null;
        workspace.prepareLegacySource(f, () {});
        winner = source().readAsBytesSync();
      }

      if (phase == 'prepare') {
        fileFault = (p) {
          if (p == 'before_source_rename') {
            fileFault = null;
            api.credentialRead = replace;
          }
        };
      } else {
        sqlFault = (p) {
          if (p == 'after_segmented_install_pointer') {
            sqlFault = null;
            api.credentialRead = replace;
          }
        };
      }
      await expectLater(
          state.refreshSegmentedForIsolatedUse(store), throwsA(anything));
      expect(winner, isNotNull);
      expect(source().readAsBytesSync(), winner);
      expect(disk()['installed'], before['installed']);
      preserved(before);
      await frozenRead(f);
    });
  }

  test(
      'RA01C native source preparation and final owner check exclude a competing SQLite writer',
      () async {
    final f = await legacy(), before = disk();
    final other = SegmentedClientStore.open(root, store.cache, adapters: true);
    var excluded = false;
    fileFault = (p) {
      if (p != 'before_source_rename') return;
      fileFault = null;
      expect(
          () => other.restoreUncommittedSource(other.installedGeneration(),
                  restoreSource: () {
                fail('competing writer must not reach its callback');
              }),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'STORE_BUSY')));
      excluded = true;
    };
    try {
      await state.refreshSegmentedForIsolatedUse(store);
      expect(excluded, true);
      preserved(before);
    } finally {
      other.close();
    }
    await frozenRead(f);
  });

  test(
      'RA01C real native COMMIT BUSY preserves Frozen-B and recovers its verified predecessor',
      () async {
    final f = await legacy(), before = disk();
    await bridge.command({'command': 'mutate'});
    final reader = sqlite3.open(store.path);
    sqlFault = (p) {
      if (p == 'after_segmented_install_pointer') {
        sqlFault = null;
        reader.execute('BEGIN DEFERRED');
        reader.select('SELECT * FROM installed');
      }
    };
    try {
      await expectLater(
          state.refreshSegmentedForIsolatedUse(store),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'STORE_BUSY')));
      expect(disk()['installed'], before['installed']);
      preserved(before);
    } finally {
      reader.execute('ROLLBACK');
      reader.close();
    }
    await frozenRead(f, process: true);
    preserved(before);
  });

  test(
      'RA01C asynchronous source preparation cannot enter the native publication callback',
      () async {
    await legacy();
    final before = disk();
    expect(
        () => store.commitInstalledGeneration(store.acceptedGeneration(),
            prepareSource: () async {}, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'ASYNC_PUBLICATION_FENCE')));
    expect(disk(), before);
  });

  test(
      'RA01C an oversized predecessor cannot replace a readable bounded source',
      () async {
    final f = await legacy();
    final s = sourceJson();
    s['audit_padding'] = 'x' * (16384 - utf8.encode(jsonEncode(s)).length - 64);
    source().writeAsStringSync(jsonEncode(s), flush: true);
    expect(source().lengthSync(), lessThanOrEqualTo(16384));
    final before = disk();
    await expectLater(
        state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'LOCAL_METADATA_BUDGET')));
    expect(disk()['source'], before['source']);
    expect(disk()['installed'], before['installed']);
    preserved(before);
    await frozenRead(f);
  });

  test(
      'RA01C source rename failure before mutation keeps a valid prior source readable',
      () async {
    final f = await legacy(), before = disk();
    fileFault = (p) {
      if (p == 'before_source_rename') throw StateError('RA01 source failure');
    };
    await expectLater(state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<StateError>()));
    expect(disk()['source'], before['source']);
    expect(disk()['installed'], before['installed']);
    preserved(before);
    fileFault = null;
    await frozenRead(f, process: true);
  });

  test(
      'RA01C post-COMMIT readback error is committed failure, never a claimed rollback',
      () async {
    final f = await legacy(), before = disk();
    await bridge.command({'command': 'mutate'});
    sqlFault = (p) {
      if (p == 'during_installation_readback') {
        sqlFault = null;
        throw StateError('RA01 committed readback');
      }
    };
    await expectLater(state.refreshSegmentedForIsolatedUse(store),
        throwsA(isA<PublicationCommittedException>()));
    expect(disk()['installed'], isNot(before['installed']));
    expect(sourceJson()['legacy_frozen'], f.id);
    preserved(before);
    await frozenRead(f, process: true);
  });

  test(
      'RA01C valid native predecessor rollback stays idempotent and independently readable',
      () async {
    final f = await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    final before = disk();
    await prepareLegacy();
    await workspace.recoverLegacyHandoff(store);
    final after = disk();
    for (var n = 0; n < 3; n++) {
      await workspace.recoverLegacyHandoff(store);
      expect(disk(), after);
    }
    preserved(before);
    await frozenRead(f, process: true);
  });

  test(
      'RA01C first uncommitted native source may be removed when no durable owner existed',
      () async {
    await state.publishSegmentedForIsolatedUse(store);
    workspace.prepareSegmentedSource(store, store.acceptedGeneration(), () {});
    expect(sourceJson()['previous_source'], null);
    await workspace.recoverLegacyHandoff(store);
    expect(source().existsSync(), false);
    expect(store.installedGeneration(), null);
    expect(store.frozenGenerations(), isEmpty);
    expect(baseline().existsSync(), false);
  });

  test(
      'RA01C first unpublished legacy preparation may release its null predecessor',
      () async {
    await state.publishSegmentedForIsolatedUse(store);
    await prepareLegacy();
    expect(sourceJson()['previous_source'], null);
    await workspace.recoverLegacyHandoff(store);
    expect(source().existsSync(), false);
    expect(store.frozenGenerations(), isEmpty);
    expect(baseline().existsSync(), false);
  });

  test(
      'RA01C missing frozen root pin blocks native installation before changing its source',
      () async {
    final f = await legacy(), before = disk();
    final d = sqlite3.open(store.path);
    final trigger = d
        .select(
            "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'")
        .single['sql'] as String;
    final pin = Map<String, dynamic>.from(d.select(
        'SELECT * FROM generation_roots WHERE generation_id=? LIMIT 1',
        [f.generationId]).single);
    d.execute('DROP TRIGGER retained_root_delete');
    d.execute('DELETE FROM generation_roots WHERE generation_id=? AND hash=?',
        [f.generationId, pin['hash']]);
    d.execute(
        trigger); // Restore exact mandatory trigger: isolate missing pin from schema damage.
    try {
      await expectLater(state.refreshSegmentedForIsolatedUse(store),
          throwsA(isA<SegmentedException>()));
      expect(disk()['source'], before['source']);
      expect(disk()['installed'], before['installed']);
      expect(disk()['baseline'], before['baseline']);
      expect(disk()['pending'], before['pending']);
    } finally {
      d.execute('INSERT INTO generation_roots(generation_id,hash) VALUES(?,?)',
          [f.generationId, pin['hash']]);
      d.close();
    }
    await frozenRead(f);
  });

  test(
      'RA01C competing original tickets cannot let the older native installation replace the winner',
      () async {
    final f = await legacy();
    // E2 deliberately rejects simultaneous acquisitions in one isolate. Pause
    // A in DATA recovery before acquisition, not inside that acquisition lock.
    await prepareLegacy();
    workspace.pause();
    final older = state.refreshSegmentedForIsolatedUse(store);
    final rejected = expectLater(older, throwsA(isA<Exception>()));
    await workspace.entered!.future;
    await state.refreshSegmentedForIsolatedUse(store);
    final winner = disk();
    workspace.release!.complete();
    await rejected;
    expect(disk(), winner);
    await frozenRead(f, process: true);
  });

  for (final change in ['credential', 'mode']) {
    test(
        'RA01C final $change change cannot install native state or retire unknown input',
        () async {
      final f = await legacy(), before = disk();
      // An unchanged installed generation correctly takes the idempotent
      // branch, which has no pointer-write hook. Exercise the actual mutation.
      await bridge.command({'command': 'mutate'});
      if (change == 'credential') {
        fileFault = (p) {
          if (p == 'after_e3_acceptance') {
            fileFault = null;
            unawaited(api.saveSession('synthetic-RA01-replaced'));
          }
        };
      } else {
        sqlFault = (p) {
          if (p == 'after_segmented_install_pointer') {
            sqlFault = null;
            state.connectivityMode = ConnectivityMode.offline;
          }
        };
      }
      await expectLater(state.refreshSegmentedForIsolatedUse(store),
          throwsA(isA<Exception>()));
      expect(disk()['installed'], before['installed']);
      preserved(before);
      await frozenRead(f);
    });
  }
}
