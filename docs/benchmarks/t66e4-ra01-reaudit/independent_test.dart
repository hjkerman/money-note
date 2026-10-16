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
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

// 제품의 검증 결과와 별도로 source/B/J bytes와 실제 SQL rows를 대조한다.
class ReauditWorkspace extends E4Workspace {
  ReauditWorkspace(super.root, {super.fault});
  Completer<void>? entered, release;
  bool pauseBase = false;
  @override
  Future<void> verifySegmentedInstallationBase(
    SegmentedClientStore store,
  ) async {
    await super.verifySegmentedInstallationBase(store);
    if (pauseBase) {
      pauseBase = false;
      entered!.complete();
      await release!.future;
    }
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late Directory root;
  late SegmentedClientStore store;
  late ReauditWorkspace workspace;
  late TargetedApi api;
  late AppState state;
  void Function(String)? fileFault, sqlFault;
  final evidence = <Map<String, dynamic>>[];
  var serial = 0;
  File source() => File('${workspace.root.path}/e4-source.json');
  File bFile() => File('${workspace.root.path}/offline-mode/baseline.json');
  File jFile() => File('${workspace.root.path}/offline-mode/journal.ndjson');
  File pending() =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  Map<String, dynamic> src() => jsonDecode(source().readAsStringSync());
  void save(Map<String, dynamic> value) =>
      source().writeAsStringSync(jsonEncode(value), flush: true);
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 9);
    wire = await e4WireOracle();
  });
  tearDownAll(() async {
    const out = String.fromEnvironment('RA01_AUDIT_OUTPUT');
    if (out.isNotEmpty) File(out).writeAsStringSync(jsonEncode(evidence));
    await bridge.dispose();
  });
  setUp(() async {
    await bridge.command({'command': 'advance', 'seconds': 901});
    FlutterSecureStorage.setMockInitialValues({});
    root = Directory.systemTemp.createTempSync('mn-independent-ra01-');
    fileFault = sqlFault = null;
    store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
      fault: (p) => sqlFault?.call(p),
    );
    workspace = ReauditWorkspace(root, fault: (p) => fileFault?.call(p));
    api = TargetedApi(bridge, wire);
    await api.saveSession(bridge.token);
    state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    await workspace.beginOnlineWrite(1);
  });
  tearDown(() {
    if (workspace.release != null && !workspace.release!.isCompleted) {
      workspace.release!.complete();
    }
    fileFault = sqlFault = null;
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
        'B': bFile().existsSync()
            ? base64Encode(bFile().readAsBytesSync())
            : null,
        'J': jFile().existsSync()
            ? base64Encode(jFile().readAsBytesSync())
            : null,
        'pending': pending().existsSync()
            ? base64Encode(pending().readAsBytesSync())
            : null,
        for (final t in [
          'accepted',
          'installed',
          'frozen',
          'generation_roots',
          'objects',
        ])
          t: d
              .select('SELECT * FROM $t ORDER BY 1,2')
              .map(
                (r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v),
                ),
              )
              .toList(),
      };
    } finally {
      d.close();
    }
  }

  void retain(Map<String, dynamic> before, {String? frozenOwner}) {
    final after = disk();
    for (final k in ['B', 'J', 'pending', 'frozen']) {
      expect(after[k], before[k], reason: k);
    }
    for (final t in ['objects', 'generation_roots']) {
      for (final row in before[t] as List) {
        // A later authorized publication may retire unrelated older owners.
        // Its required Frozen-B owner must retain every actual root relation.
        if (t == 'generation_roots' &&
            frozenOwner != null &&
            row['generation_id'] != frozenOwner)
          continue;
        expect(
          (after[t] as List).any((r) => jsonEncode(r) == jsonEncode(row)),
          true,
          reason: '$t $row',
        );
      }
    }
  }

  Future<FrozenGeneration> legacy() async =>
      (await state.installSegmentedLegacyForIsolatedUse(store)).frozen;

  Future<FrozenGeneration> preparation() async {
    final g = store.acceptedGeneration();
    final proof = await store.verifyAcceptedForMaterialization(g);
    final bundle = store.withAcceptedRead(
      g,
      (r) => materializeLegacyRead(r, baselineFixture().user),
      materializationProof: proof,
    );
    final b = legacyBaseline(
      bundle,
      DateTime.utc(2026, 10, 20).add(Duration(seconds: ++serial)),
    );
    final f = store.prepareFrozenGeneration(
      g,
      proof,
      workspace.bindingFor(g, b, store.cache.key),
      frozenId: syncUuid(),
      finalAuthorityFence: () {},
    );
    workspace.prepareLegacySource(f, () {});
    return f;
  }

  Future<void> fresh(String id, {bool child = false}) async {
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final w = E4Workspace(root);
    await w.recoverLegacyHandoff(store);
    final b = await w.readFrozenBaseline(store, id, 1);
    final frozen = store.frozenGenerations().singleWhere((f) => f.id == id);
    expect(w.recoveryLineageFingerprint(b), frozen.binding['legacy_lineage']);
    final repo = Directory.current.parent.path;
    final oracle = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
      w.root.path,
    ]);
    expect(oracle.exitCode, 0, reason: '${oracle.stderr}');
    if (child) {
      File('${root.path}/owned').writeAsStringSync('synthetic E4-A01');
      File('${root.path}/expected.json').writeAsStringSync(
        jsonEncode({
          'target': store.acceptedGeneration().manifest!.target.toJson(),
          'frozen': id,
        }),
      );
      final p = await Process.run('/home/hjkerman/.flutter/bin/flutter', [
        'test',
        '--no-pub',
        '--machine',
        '--dart-define=A01_ROOT=${root.path}',
        '--dart-define=A01_MODE=recover',
        '$repo/docs/benchmarks/t66e4-a01/crash_child_test.dart',
      ], workingDirectory: '$repo/mobile');
      expect(p.exitCode, 0, reason: '${p.stdout}\n${p.stderr}');
    }
  }

  void note(String id, Map<String, dynamic> before, [Object? detail]) =>
      evidence.add({
        'id': id,
        'before': before,
        'after': disk(),
        'detail': detail,
      });

  test('NR01 first-source transaction fails after rename then valid retry installs', () async {
    var prepared = false;
    fileFault = (p) {
      if (p == 'before_source_rename') prepared = true;
    };
    sqlFault = (p) {
      if (p == 'after_segmented_install_pointer')
        throw StateError('owned synthetic precommit');
    };
    await expectLater(
      state.refreshSegmentedForIsolatedUse(store),
      throwsA(isA<StateError>()),
    );
    expect(prepared, true);
    expect(store.installedGeneration(), null);
    expect(src()['previous_source'], null);
    final before = disk();
    fileFault = sqlFault = null;
    await workspace.recoverLegacyHandoff(store);
    expect(source().existsSync(), false);
    await state.refreshSegmentedForIsolatedUse(store);
    expect(src()['previous_source'], null);
    expect(store.installedGeneration()!.id, src()['generation']);
    expect(disk()['pending'], before['pending']);
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    await E4Workspace(root).recoverLegacyHandoff(store);
    expect((await store.recoverInstalledGeneration())!.id, src()['generation']);
    note('NR01', before);
  });

  test(
    'NR02 alternating legacy/native transitions retain latest distinct lineage',
    () async {
      final first = await legacy();
      await bridge.command({'command': 'mutate'});
      await state.refreshSegmentedForIsolatedUse(store);
      await bridge.command({'command': 'mutate'});
      final second = await legacy();
      expect(second.id, isNot(first.id));
      expect(
        second.binding['legacy_lineage'],
        isNot(first.binding['legacy_lineage']),
      );
      final before = disk();
      await bridge.command({'command': 'mutate'});
      await state.refreshSegmentedForIsolatedUse(store);
      expect(src()['legacy_frozen'], second.id);
      note('NR02-before-retention-assertion', before, {
        'required_frozen_owner': second.generationId,
      });
      retain(before, frozenOwner: second.generationId);
      await fresh(second.id, child: true);
      note('NR02', before);
    },
  );

  for (final value in [<Object?>[], 'invalid', 1, true]) {
    test(
      'NR03 malformed predecessor type ${value.runtimeType} is not absence',
      () async {
        final f = await legacy();
        final valid = src();
        await preparation();
        save(src()..['previous_source'] = value);
        final before = disk();
        await expectLater(
          state.refreshSegmentedForIsolatedUse(store),
          throwsA(isA<SegmentedException>()),
        );
        expect(disk(), before);
        note('NR03-${value.runtimeType}', before);
        save(
          valid,
        ); // explicit test repair only; product must not fabricate it.
        await workspace.recoverLegacyHandoff(store);
        await fresh(f.id);
      },
    );
  }

  test(
    'NR04 null source cannot erase installed native-only owner on reopen',
    () async {
      await state.refreshSegmentedForIsolatedUse(store);
      await bridge.command({'command': 'mutate'});
      await state.publishSegmentedForIsolatedUse(store);
      workspace.prepareSegmentedSource(
        store,
        store.acceptedGeneration(),
        () {},
      );
      save(src()..['previous_source'] = null);
      final before = disk();
      await expectLater(
        workspace.recoverLegacyHandoff(store),
        throwsA(isA<SegmentedException>()),
      );
      expect(disk(), before);
      final cache = store.cache;
      store.close();
      store = SegmentedClientStore.open(root, cache, adapters: true);
      await expectLater(
        E4Workspace(root).recoverLegacyHandoff(store),
        throwsA(isA<SegmentedException>()),
      );
      expect(disk(), before);
      note('NR04', before);
    },
  );

  test('NR05 original request invalidated while verified base waits', () async {
    final f = await legacy();
    final before = disk();
    workspace.pauseBase = true;
    workspace.entered = Completer();
    workspace.release = Completer();
    final older = state.refreshSegmentedForIsolatedUse(store);
    final rejected = expectLater(older, throwsA(isA<Exception>()));
    await workspace.entered!.future;
    await state.refreshSegmentedForIsolatedUse(store);
    final winner = disk();
    workspace.release!.complete();
    await rejected;
    expect(disk(), winner);
    retain(before);
    await fresh(f.id);
    note('NR05', before);
  });

  test(
    'NR06 schema changed after verified base cannot rename current source',
    () async {
      final f = await legacy(), before = disk();
      final d = sqlite3.open(store.path);
      final sql =
          d
                  .select(
                    "SELECT sql FROM sqlite_master WHERE name='frozen_release'",
                  )
                  .single['sql']
              as String;
      fileFault = (p) {
        if (p == 'after_e3_acceptance') {
          fileFault = null;
          d.execute('DROP TRIGGER frozen_release');
        }
      };
      try {
        await expectLater(
          state.refreshSegmentedForIsolatedUse(store),
          throwsA(isA<SegmentedException>()),
        );
        expect(disk()['source'], before['source']);
        expect(disk()['installed'], before['installed']);
        retain(before);
        note('NR06', before);
      } finally {
        d.execute(sql);
        d.close();
      }
      await fresh(f.id);
    },
  );

  test(
    'NR07 different metadata owner at native rename is never overwritten',
    () async {
      final f = await legacy(), before = disk();
      List<int>? winner;
      fileFault = (p) {
        if (p == 'before_source_rename') {
          fileFault = null;
          save(src()..['audit_operation'] = 'new-owner-with-same-frozen-id');
          winner = source().readAsBytesSync();
        }
      };
      await expectLater(
        state.refreshSegmentedForIsolatedUse(store),
        throwsA(anything),
      );
      expect(source().readAsBytesSync(), winner);
      expect(disk()['installed'], before['installed']);
      retain(before);
      await fresh(f.id, child: true);
      note('NR07', before);
    },
  );

  for (final damaged in ['previous_sequence', 'previous_installation']) {
    test(
      'NR08 native rollback rejects wrong $damaged even with exact Frozen binding',
      () async {
        final f = await legacy();
        await state.refreshSegmentedForIsolatedUse(store);
        final valid = src();
        await bridge.command({'command': 'mutate'});
        await state.publishSegmentedForIsolatedUse(store);
        workspace.prepareSegmentedSource(
          store,
          store.acceptedGeneration(),
          () {},
        );
        final s = src();
        s[damaged] = damaged == 'previous_sequence'
            ? (s[damaged] as int) + 1
            : syncUuid();
        save(s);
        final before = disk();
        await expectLater(
          workspace.recoverLegacyHandoff(store),
          throwsA(isA<SegmentedException>()),
        );
        expect(disk(), before);
        note('NR08-$damaged', before);
        save(valid);
        await fresh(f.id);
      },
    );
  }

  test('NR09 same generation with stale predecessor operation sequence is rejected', () async {
    final f = await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    final valid = src();
    await preparation();
    final s = src(), p = Map<String, dynamic>.from(src()['previous_source']);
    p['sequence'] = (p['sequence'] as int) + 7;
    s['previous_source'] = p;
    save(s);
    final before = disk();
    await expectLater(
      workspace.recoverLegacyHandoff(store),
      throwsA(isA<SegmentedException>()),
    );
    expect(disk(), before);
    note('NR09', before);
    save(valid);
    await fresh(f.id);
  });

  test(
    'NR10 legitimate rollback repeated after two independent handle reopenings',
    () async {
      final f = await legacy();
      await state.refreshSegmentedForIsolatedUse(store);
      final before = disk();
      await preparation();
      await fresh(f.id, child: true);
      final after = disk();
      await fresh(f.id, child: true);
      expect(disk(), after);
      retain(before);
      note('NR10', before);
    },
  );

  test('NR11 failed conditional native commit and retry cannot retire unknown marker', () async {
    final f = await legacy(), before = disk();
    await bridge.command({'command': 'mutate'});
    sqlFault = (p) {
      if (p == 'after_segmented_install_pointer') {
        sqlFault = null;
        throw StateError('conditional native rollback');
      }
    };
    await expectLater(
      state.refreshSegmentedForIsolatedUse(store),
      throwsA(isA<StateError>()),
    );
    expect(disk()['installed'], before['installed']);
    retain(before);
    await fresh(f.id, child: true);
    await state.refreshSegmentedForIsolatedUse(store);
    retain(before);
    expect(src()['legacy_frozen'], f.id);
    await fresh(f.id);
    note('NR11', before);
  });

  test('NR12 prepared legacy source without an owner recovers then first native installs', () async {
    await state.publishSegmentedForIsolatedUse(store);
    await preparation();
    final before = disk();
    expect(src()['previous_source'], null);
    await state.refreshSegmentedForIsolatedUse(store);
    expect(src()['previous_source'], null);
    expect(src()['legacy_frozen'], null);
    expect(store.frozenGenerations(), isEmpty);
    expect(store.installedGeneration()!.id, src()['generation']);
    expect(disk()['pending'], before['pending']);
    note('NR12', before);
  });

  test('NR13 native predecessor Frozen association preserved when damaged hint rejects recovery', () async {
    final f = await legacy();
    await state.refreshSegmentedForIsolatedUse(store);
    await bridge.command({'command': 'mutate'});
    await state.publishSegmentedForIsolatedUse(store);
    workspace.prepareSegmentedSource(store, store.acceptedGeneration(), () {});
    save(src()..['previous_source'] = null);
    final before = disk();
    await expectLater(
      state.refreshSegmentedForIsolatedUse(store),
      throwsA(isA<SegmentedException>()),
    );
    expect(disk(), before);
    // RecoveryBlocked is distinct from read-only integrity of retained Frozen B.
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    final b = await E4Workspace(root).readFrozenBaseline(store, f.id, 1);
    expect(b.serverStateFingerprint, f.binding['legacy_fingerprint']);
    expect(disk(), before);
    note('NR13', before);
  });

  test('NR14 source binding change before final SQL fence cannot report installed success', () async {
    final f = await legacy(), before = disk();
    await bridge.command({'command': 'mutate'});
    sqlFault = (p) {
      if (p == 'after_segmented_install_pointer') {
        sqlFault = null;
        save(src()..['legacy_binding'] = '0' * 64);
      }
    };
    await expectLater(
      state.refreshSegmentedForIsolatedUse(store),
      throwsA(anything),
    );
    expect(disk()['installed'], before['installed']);
    retain(before);
    note('NR14', before);
    source().writeAsBytesSync(base64Decode(before['source']), flush: true);
    await fresh(f.id);
  });
}
