@Timeout(Duration(minutes: 10))
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
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

class AuditWorkspace extends E4Workspace {
  AuditWorkspace(super.root, {super.fault});
  Completer<void>? entered, release;
  void pause() {
    entered = Completer();
    release = Completer();
  }

  @override
  Future<List<OfflineJournalOperation>> loadJournal() async {
    if (entered != null && !entered!.isCompleted) {
      entered!.complete();
      await release!.future;
    }
    return super.loadJournal();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late Directory root;
  late SegmentedClientStore store;
  late AuditWorkspace workspace;
  late AppState state;
  late FrozenGeneration initial;
  void Function(String)? fileFault;
  final evidence = <Map<String, dynamic>>[];
  var serial = 0;
  File source() => File('${workspace.root.path}/e4-source.json');
  File baseline() => File('${workspace.root.path}/offline-mode/baseline.json');
  File pending() =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 6);
    wire = await e4WireOracle();
  });
  tearDownAll(() async {
    const output = String.fromEnvironment('REAUDIT_OUTPUT');
    if (output.isNotEmpty)
      File(output).writeAsStringSync(jsonEncode(evidence), flush: true);
    await bridge.dispose();
  });
  setUp(() async {
    await bridge.command({'command': 'advance', 'seconds': 901});
    FlutterSecureStorage.setMockInitialValues({});
    root = Directory.systemTemp.createTempSync('mn-independent-e4-a01-');
    store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
    );
    fileFault = null;
    workspace = AuditWorkspace(root, fault: (p) => fileFault?.call(p));
    final api = TargetedApi(bridge, wire);
    await api.saveSession(bridge.token);
    state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    initial = (await state.installSegmentedLegacyForIsolatedUse(store)).frozen;
    await workspace.beginOnlineWrite(1);
  });
  tearDown(() {
    if (workspace.release != null && !workspace.release!.isCompleted)
      workspace.release!.complete();
    state.dispose();
    store.close();
    root.deleteSync(recursive: true);
  });
  Map<String, dynamic> disk() {
    final db = sqlite3.open(store.path);
    try {
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      return {
        'source': base64Encode(source().readAsBytesSync()),
        'baseline': base64Encode(baseline().readAsBytesSync()),
        'pending': base64Encode(pending().readAsBytesSync()),
        for (final t in [
          'accepted',
          'installed',
          'frozen',
          'generation_roots',
          'refs',
        ])
          t: db
              .select('SELECT * FROM $t ORDER BY 1,2')
              .map(
                (r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v),
                ),
              )
              .toList(),
      };
    } finally {
      db.close();
    }
  }

  Future<(FrozenGeneration, OfflineBaseline)> prepare() async {
    final g = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(g);
    final bundle = store.withAcceptedRead(
      g,
      (r) => materializeLegacyRead(r, baselineFixture().user),
      materializationProof: proof,
    );
    final b = legacyBaseline(
      bundle,
      DateTime.utc(2026, 10, 15).add(Duration(seconds: ++serial)),
    );
    final f = store.prepareFrozenGeneration(
      g,
      proof,
      workspace.bindingFor(g, b, store.cache.key),
      frozenId: syncUuid(),
      finalAuthorityFence: () {},
    );
    workspace.prepareLegacySource(f, () {});
    return (f, b);
  }

  Future<void> check(String id, String frozenId, {bool process = false}) async {
    final current = disk();
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final fresh = E4Workspace(root);
    await fresh.recoverLegacyHandoff(store);
    final b = await fresh.readFrozenBaseline(store, frozenId, 1);
    expect(
      fresh.recoveryLineageFingerprint(b),
      store
          .frozenGenerations()
          .singleWhere((f) => f.id == frozenId)
          .binding['legacy_lineage'],
    );
    final repo = Directory.current.parent.path;
    if (process) {
      File('${root.path}/owned').writeAsStringSync('synthetic E4-A01');
      File('${root.path}/expected.json').writeAsStringSync(
        jsonEncode({
          'target': store.acceptedGeneration().manifest!.target.toJson(),
          'frozen': frozenId,
        }),
      );
      final child = await Process.run('/home/hjkerman/.flutter/bin/flutter', [
        'test',
        '--no-pub',
        '--machine',
        '--dart-define=A01_ROOT=${root.path}',
        '--dart-define=A01_MODE=recover',
        '$repo/docs/benchmarks/t66e4-a01/crash_child_test.dart',
      ], workingDirectory: '$repo/mobile');
      expect(
        child.exitCode,
        0,
        reason: (child.stdout as String)
            .split('\n')
            .where((l) => l.contains('"type":"error"'))
            .join('\n'),
      );
    }
    final oracle = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
      workspace.root.path,
    ]);
    expect(oracle.exitCode, 0, reason: oracle.stderr as String);
    evidence.add({
      'id': id,
      'before_reopen': current,
      'after_reopen': disk(),
      'fresh_process': process,
      'independent_graph': jsonDecode(oracle.stdout as String),
    });
  }

  Matcher code(String c) =>
      isA<SegmentedException>().having((e) => e.code, 'code', c);

  test('RA01 same operation becomes legitimately installed while its rollback recovery waits', () async {
    final (a, b) = await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    final outcome = expectLater(
      older,
      throwsA(code('FROZEN_RELEASE_REJECTED')),
    );
    await workspace.entered!.future;
    await E4Workspace(root).replaceBaseline(b);
    store.finishFrozenHandoff(a, finalAuthorityFence: () {});
    final winner = disk();
    workspace.release!.complete();
    await outcome;
    expect(disk(), winner);
    await check('RA01', a.id, process: true);
  });

  test(
    'RA02 exact stale source replay cannot resurrect a deleted SQL preparation',
    () async {
      await prepare();
      final stale = source().readAsBytesSync();
      await E4Workspace(root).recoverLegacyHandoff(store);
      final healthy = source().readAsBytesSync();
      source().writeAsBytesSync(stale, flush: true);
      final before = disk();
      await expectLater(
        workspace.recoverLegacyHandoff(store),
        throwsA(code('FROZEN_BINDING_INVALID')),
      );
      expect(disk(), before);
      // Controlled metadata-corruption fixture is restored by the auditor, not claimed as automatic repair.
      source().writeAsBytesSync(healthy, flush: true);
      await check('RA02', initial.id);
    },
  );

  test('RA03 four competing recoveries on two SQLite handles release only the abandoned owner', () async {
    final (a, _) = await prepare();
    final before = disk();
    final other = SegmentedClientStore.open(root, store.cache, adapters: true);
    try {
      await Future.wait([
        workspace.recoverLegacyHandoff(store),
        E4Workspace(root).recoverLegacyHandoff(other),
        E4Workspace(root).recoverLegacyHandoff(store),
        E4Workspace(root).recoverLegacyHandoff(other),
      ]);
    } finally {
      other.close();
    }
    expect(store.frozenGenerations().map((f) => f.id), [initial.id]);
    expect(store.frozenGenerations().any((f) => f.id == a.id), false);
    expect(base64Encode(baseline().readAsBytesSync()), before['baseline']);
    expect(base64Encode(pending().readAsBytesSync()), before['pending']);
    await check('RA03', initial.id);
  });

  test('RA04 competing SQLite writer excludes recovery file mutation before BEGIN IMMEDIATE', () async {
    await prepare();
    final before = disk();
    final writer = sqlite3.open(store.path);
    writer.execute('BEGIN IMMEDIATE');
    try {
      await expectLater(
        workspace.recoverLegacyHandoff(store),
        throwsA(code('STORE_BUSY')),
      );
      expect(disk(), before);
    } finally {
      writer.execute('ROLLBACK');
      writer.close();
    }
    await workspace.recoverLegacyHandoff(store);
    await check('RA04', initial.id);
  });

  test('RA05 missing mandatory trigger after async recovery checks fails before changing source', () async {
    await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    final outcome = expectLater(older, throwsA(code('STORE_SCHEMA_CORRUPT')));
    await workspace.entered!.future;
    final db = sqlite3.open(store.path);
    final sql =
        db
                .select(
                  "SELECT sql FROM sqlite_master WHERE name='frozen_release'",
                )
                .single['sql']
            as String;
    db.execute('DROP TRIGGER frozen_release');
    final before = disk();
    workspace.release!.complete();
    await outcome;
    expect(disk(), before);
    db.execute(sql);
    db.close();
    await workspace.recoverLegacyHandoff(store);
    await check('RA05', initial.id);
  });

  test('RA06 changed legacy B after async unchanged check cannot be restored or unpinned', () async {
    final (a, b) = await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    final outcome = expectLater(
      older,
      throwsA(code('LEGACY_LINEAGE_UNAVAILABLE')),
    );
    await workspace.entered!.future;
    await E4Workspace(root).replaceBaseline(b);
    final before = disk();
    workspace.release!.complete();
    await outcome;
    expect(disk(), before);
    await workspace.recoverLegacyHandoff(store);
    await check('RA06', a.id);
  });

  test('RA07 journal appearing during recovery preserves preparation and exact ordered bytes', () async {
    final b = await E4Workspace(root).readFrozenBaseline(store, initial.id, 1);
    await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    final journal = File('${workspace.root.path}/offline-mode/journal.ndjson');
    // Use a valid existing legacy journal operation rather than inventing input grammar.
    await workspace.saveMetadata(
      OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: workspace.recoveryLineageFingerprint(b),
      ),
    );
    await workspace.appendOperation(
      type: OfflineOperationType.createCashFlow,
      payload: {
        'occurred_on': '2026-10-15',
        'title': '미확인 입력 e\u0301',
        'amount_value': '+0002.00',
        'is_primary_income': 0,
      },
      baseline: b,
    );
    final bytes = journal.readAsBytesSync();
    final before = disk();
    workspace.release!.complete();
    await expectLater(older, throwsA(code('FROZEN_HANDOFF_RECOVERY_REQUIRED')));
    expect(disk(), before);
    expect(journal.readAsBytesSync(), bytes);
    evidence.add({
      'id': 'RA07',
      'state': before,
      'journal_sha256': localChecksum(bytes),
      'journal_operations': utf8
          .decode(bytes)
          .split('\n')
          .where((line) => line.isNotEmpty)
          .map(jsonDecode)
          .toList(),
      'recovery': 'blocked with active J',
    });
  });

  test('RA08 null expected installed owner cannot invoke restoration over a valid source', () async {
    final before = disk();
    var called = false;
    expect(
      () => store.restoreUncommittedSource(
        null,
        restoreSource: () {
          called = true;
        },
      ),
      throwsA(code('PUBLICATION_CONFLICT')),
    );
    expect(called, false);
    expect(disk(), before);
    await check('RA08', initial.id);
  });

  test('RA09 changed source at native restoration hook is preserved under SQL fence', () async {
    await bridge.command({'command': 'mutate'});
    await state.publishSegmentedForIsolatedUse(store);
    workspace.prepareSegmentedSource(store, store.acceptedGeneration(), () {});
    late List<int> winner;
    fileFault = (p) {
      if (p == 'before_source_rename') {
        fileFault = null;
        workspace.prepareLegacySource(initial, () {});
        winner = source().readAsBytesSync();
      }
    };
    await workspace.recoverLegacyHandoff(store);
    expect(source().readAsBytesSync(), winner);
    await check('RA09', initial.id);
  });

  test('RA10 same binding checksum different UUID and lineage-preserving bytes remains newer owner', () async {
    final (a, b) = await prepare();
    workspace.pause();
    final old = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    await E4Workspace(root).recoverLegacyHandoff(store);
    final g = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(g);
    final newer = store.prepareFrozenGeneration(
      g,
      proof,
      a.binding,
      frozenId: syncUuid(),
      finalAuthorityFence: () {},
    );
    expect(newer.checksum, a.checksum);
    expect(newer.id, isNot(a.id));
    workspace.prepareLegacySource(newer, () {});
    await workspace.replaceBaseline(b);
    store.finishFrozenHandoff(newer, finalAuthorityFence: () {});
    final winner = disk();
    workspace.release!.complete();
    await old;
    expect(disk(), winner);
    await check('RA10', newer.id, process: true);
  });

  test('RA11 same frozen source with changed durable operation metadata causes stale no-op', () async {
    await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    final changed =
        jsonDecode(source().readAsStringSync()) as Map<String, dynamic>;
    changed['audit_operation'] = 'different operation with same frozen ID';
    source().writeAsStringSync(jsonEncode(changed), flush: true);
    final before = disk();
    workspace.release!.complete();
    expect(await older, null);
    expect(disk(), before);
    await workspace.recoverLegacyHandoff(store);
    await check('RA11', initial.id);
  });

  test('RA12 legitimate source rollback and repeated reopen retain legacy lineage and unknown pending', () async {
    await prepare();
    final before = disk();
    await workspace.recoverLegacyHandoff(store);
    final after = disk();
    expect(after['baseline'], before['baseline']);
    expect(after['pending'], before['pending']);
    for (var n = 0; n < 3; n++) {
      await E4Workspace(root).recoverLegacyHandoff(store);
      expect(disk(), after);
    }
    await check('RA12', initial.id, process: true);
  });

  test('RA13 second connection cannot commit between SQL ownership check and source rename', () async {
    await prepare();
    final other = SegmentedClientStore.open(root, store.cache, adapters: true);
    var called = false, blocked = false;
    fileFault = (point) {
      if (point != 'before_source_rename') return;
      fileFault = null;
      try {
        other.restoreUncommittedSource(
          other.installedGeneration(),
          restoreSource: () {
            called = true;
          },
        );
      } on SegmentedException catch (e) {
        expect(e.code, 'STORE_BUSY');
        blocked = true;
      }
    };
    try {
      await workspace.recoverLegacyHandoff(store);
      expect(blocked, true);
      expect(called, false);
    } finally {
      other.close();
    }
    await check('RA13', initial.id);
  });

  test('RA14 COMMIT-busy compensation cannot overwrite a newly replaced valid source', () async {
    await prepare();
    final reader = sqlite3.open(store.path);
    var hooks = 0;
    List<int>? winner;
    fileFault = (point) {
      if (point != 'before_source_rename') return;
      hooks++;
      if (hooks == 1) {
        reader.execute('BEGIN DEFERRED');
        reader.select('SELECT * FROM frozen');
      } else {
        fileFault = null;
        workspace.prepareSegmentedSource(
          store,
          store.installedGeneration()!,
          () {},
        );
        winner = source().readAsBytesSync();
      }
    };
    try {
      await expectLater(
        workspace.recoverLegacyHandoff(store),
        throwsA(code('STORE_BUSY')),
      );
      expect(hooks, 2);
      expect(winner, isNotNull);
      expect(source().readAsBytesSync(), winner);
    } finally {
      reader.execute('ROLLBACK');
      reader.close();
    }
    await workspace.recoverLegacyHandoff(store);
    expect(source().readAsBytesSync(), winner);
    await check('RA14', initial.id);
  });

  test('RA15 newer AppState installation failure preserves the previous owner before old recovery resumes', () async {
    final before = disk();
    await prepare();
    workspace.pause();
    final older = workspace.recoverLegacyHandoff(store);
    await workspace.entered!.future;
    fileFault = (point) {
      if (point == 'before_legacy_rename') {
        fileFault = null;
        throw StateError('newer pre-install failure');
      }
    };
    await expectLater(
      state.installSegmentedLegacyForIsolatedUse(store),
      throwsA(
        isA<StateError>().having(
          (e) => e.message,
          'message',
          'newer pre-install failure',
        ),
      ),
    );
    final afterB = disk();
    expect(afterB['baseline'], before['baseline']);
    expect(afterB['pending'], before['pending']);
    expect(store.frozenGenerations().map((f) => f.id), [initial.id]);
    workspace.release!.complete();
    expect(await older, null);
    expect(disk(), afterB);
    await check('RA15', initial.id);
  });

  for (final native in [false, true]) {
    test(
      'RA${native ? 17 : 16} missing predecessor source with an existing installed SQL owner must fail closed native=$native',
      () async {
        if (native) {
          await bridge.command({'command': 'mutate'});
          await state.publishSegmentedForIsolatedUse(store);
          workspace.prepareSegmentedSource(
            store,
            store.acceptedGeneration(),
            () {},
          );
        } else {
          await prepare();
        }
        final value =
            jsonDecode(source().readAsStringSync()) as Map<String, dynamic>;
        expect(value['previous_source'], isNotNull);
        value['previous_source'] =
            null; // One-field corruption; no hash is recomputed.
        source().writeAsStringSync(jsonEncode(value), flush: true);
        final before = disk();
        Object? recoveryError;
        try {
          await workspace.recoverLegacyHandoff(store);
        } catch (error) {
          recoveryError = error;
        }
        final db = sqlite3.open(store.path);
        final afterSql = {
          for (final t in [
            'accepted',
            'installed',
            'frozen',
            'generation_roots',
          ])
            t: db
                .select('SELECT * FROM $t ORDER BY 1,2')
                .map(
                  (r) => r.map(
                    (k, v) =>
                        MapEntry(k, v is List<int> ? localChecksum(v) : v),
                  ),
                )
                .toList(),
        };
        db.close();
        final cache = store.cache;
        store.close();
        store = SegmentedClientStore.open(root, cache, adapters: true);
        Object? freshError;
        try {
          await E4Workspace(root).recoverLegacyHandoff(store);
        } catch (error) {
          freshError = error;
        }
        evidence.add({
          'id': native ? 'RA17' : 'RA16',
          'native': native,
          'before_recovery': before,
          'after_source_exists': source().existsSync(),
          'after_sql': afterSql,
          'baseline_unchanged':
              base64Encode(baseline().readAsBytesSync()) == before['baseline'],
          'pending_unchanged':
              base64Encode(pending().readAsBytesSync()) == before['pending'],
          'recovery_error': recoveryError is SegmentedException
              ? recoveryError.code
              : recoveryError?.toString(),
          'fresh_error': freshError is SegmentedException
              ? freshError.code
              : freshError?.toString(),
        });
        if (recoveryError != null) {
          expect(source().existsSync(), true);
          expect(base64Encode(source().readAsBytesSync()), before['source']);
          expect(afterSql['frozen'], before['frozen']);
        } else {
          expect(
            source().existsSync(),
            true,
            reason: 'A recovery that returns normally must preserve a verified source for the existing installed owner.',
          );
          expect(freshError, null);
          await E4Workspace(root).readFrozenBaseline(store, initial.id, 1);
        }
      },
    );
  }

  test('RA18 AppState must not report native installation success while losing its existing Frozen-B lineage association', () async {
    await prepare();
    final corrupt =
        jsonDecode(source().readAsStringSync()) as Map<String, dynamic>;
    corrupt['previous_source'] = null;
    source().writeAsStringSync(jsonEncode(corrupt), flush: true);
    final before = disk();
    Object? installError, readError, freshReadError;
    var installedSuccessfully = false;
    try {
      await state.refreshSegmentedForIsolatedUse(store);
      installedSuccessfully = true;
    } catch (error) {
      installError = error;
    }
    final after = disk();
    try {
      await workspace.readFrozenBaseline(store, initial.id, 1);
    } catch (error) {
      readError = error;
    }
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final fresh = E4Workspace(root);
    Object? freshRecoveryError;
    try {
      await fresh.recoverLegacyHandoff(store);
    } catch (error) {
      freshRecoveryError = error;
    }
    try {
      await fresh.readFrozenBaseline(store, initial.id, 1);
    } catch (error) {
      freshReadError = error;
    }
    final repo = Directory.current.parent.path;
    final oracle = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
    ]);
    expect(oracle.exitCode, 0, reason: oracle.stderr as String);
    File('${root.path}/owned').writeAsStringSync('synthetic E4-A01');
    File('${root.path}/expected.json').writeAsStringSync(
      jsonEncode({
        'target': store.acceptedGeneration().manifest!.target.toJson(),
        'frozen': initial.id,
      }),
    );
    final child = await Process.run('/home/hjkerman/.flutter/bin/flutter', [
      'test',
      '--no-pub',
      '--machine',
      '--dart-define=A01_ROOT=${root.path}',
      '--dart-define=A01_MODE=recover',
      '$repo/docs/benchmarks/t66e4-a01/crash_child_test.dart',
    ], workingDirectory: '$repo/mobile');
    final childErrors = (child.stdout as String)
        .split('\n')
        .where((line) => line.contains('"type":"error"'))
        .toList();
    String? errorCode(Object? error) =>
        error is SegmentedException ? error.code : error?.toString();
    evidence.add({
      'id': 'RA18',
      'initial_frozen': initial.id,
      'before_recovery': before,
      'after_native_install': after,
      'installed_successfully': installedSuccessfully,
      'install_error': errorCode(installError),
      'read_error': errorCode(readError),
      'fresh_recovery_error': errorCode(freshRecoveryError),
      'fresh_read_error': errorCode(freshReadError),
      'fresh_process_exit': child.exitCode,
      'fresh_process_errors': childErrors,
      'baseline_unchanged': after['baseline'] == before['baseline'],
      'pending_unchanged': after['pending'] == before['pending'],
      'independent_graph': jsonDecode(oracle.stdout as String),
    });
    if (installedSuccessfully) {
      final committedSource = jsonDecode(
        utf8.decode(base64Decode(after['source'] as String)),
      ) as Map;
      expect(
        committedSource['legacy_frozen'] ?? committedSource['frozen'],
        initial.id,
        reason: 'A reported successful native installation must preserve the already installed Frozen-B association.',
      );
      expect(readError, null);
      expect(freshReadError, null);
      expect(child.exitCode, 0);
    } else {
      expect(after['source'], before['source']);
    }
  });
}
