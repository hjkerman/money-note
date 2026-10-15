// Actual D3a/D3b synthetic seed/transfer is CPU-heavy when the full regression
// runs concurrently. This finite harness ceiling does not alter transport timeouts
// or any work-count/correctness assertion.
@Timeout(Duration(minutes: 20))
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/e4_targeted_fixture.dart';
import 'support/segmented_e2_fixture.dart';

// Independent legacy IO/hash oracle: delegates to the unchanged P0 algorithms.
class CountedLegacy extends OfflineStore {
  CountedLegacy(this.root) : super(directoryProvider: () => Future.value(root));
  final Directory root;
  int parses = 0, parseBytes = 0, hashes = 0, hashBytes = 0;
  @override
  Future<OfflineBaseline?> loadBaseline() async {
    parses++;
    parseBytes += File('${root.path}/offline-mode/baseline.json').lengthSync();
    return super.loadBaseline();
  }

  @override
  String recoveryLineageFingerprint(OfflineBaseline b) {
    hashes++;
    hashBytes += utf8
        .encode(jsonEncode({
          'schema_version': 1,
          'origin': 'mobile-baseline-lineage',
          'baseline': b.toJson()
        }))
        .length;
    return super.recoveryLineageFingerprint(b);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, dynamic> wire;
  setUpAll(() async {
    wire = await e4WireOracle();
  });
  final costs = <Map<String, dynamic>>[];
  final nativeFixtures = <Map<String, dynamic>>[];
  for (final history in [4, 400]) {
    test(
        'T03 independent before/full vs optimized repeated frozen read history=$history',
        () async {
      final bridge = await BackendBridge.start(history: history),
          h = await E4Harness.create(bridge, wire);
      try {
        final installed = await h.install(), f = installed.frozen;
        expect(f.target.syncRoot,
            GenerationFixture(bridge.fixture).target.syncRoot);
        final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
        await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
            baselineLineageFingerprint: f.binding['legacy_lineage']));
        for (var n = 0; n < 3; n++) {
          await h.workspace.appendOperation(
              type: OfflineOperationType.createCashFlow,
              payload: {
                'occurred_on': '2026-10-14',
                'title': '원문 $n 😀',
                'amount_value': '+0007.00',
                'is_primary_income': 0
              },
              baseline: b);
        }
        final before = CountedLegacy(h.workspace.root);
        final fullWatch = Stopwatch()..start();
        final full = await readPendingLegacyView(before, 1);
        await readPendingLegacyView(before, 1);
        fullWatch.stop();
        expect(before.parses, 2);
        expect(before.hashes, 2);
        final fresh = E4Workspace(h.root);
        final coldWatch = Stopwatch()..start();
        final cold = await fresh.readFrozenPending(h.store, f.id, 1);
        coldWatch.stop();
        expect(fresh.fullBaselineReads, 1);
        expect(fresh.lineageVerifications, 1);
        final work = h.store.work.snapshot(),
            parses = fresh.fullBaselineReads,
            hashes = fresh.lineageVerifications;
        final watch = Stopwatch();
        for (var n = 0; n < 3; n++) {
          watch.start();
          final optimized = await fresh.readFrozenPending(h.store, f.id, 1);
          watch.stop();
          expect(optimized.bundle.baseline.toJson(),
              full!.bundle.baseline.toJson());
          expect(optimized.bundle.operations.map((o) => o.toJson()).toList(),
              full.bundle.operations.map((o) => o.toJson()).toList());
          expect(optimized.projection!.summary.cashFlowBalance,
              full.projection!.summary.cashFlowBalance);
        }
        watch.stop();
        expect(fresh.fullBaselineReads - parses, 0);
        expect(fresh.lineageVerifications - hashes, 0);
        expect(h.store.work.since(work)['frozen_full_recoveries'] ?? 0, 0);
        final warmWork = h.store.work.since(work);
        for (final key in [
          'full_raw_rows',
          'full_fact_rows',
          'full_verifications',
          'graph_nodes_examined'
        ]) {
          expect(warmWork[key] ?? 0, 0, reason: key);
        }
        final beforeAccept = fresh.fullBaselineReads;
        await bridge.command({'command': 'mutate'});
        await h.publish();
        final changedFixture = await bridge.command({'command': 'oracle'});
        nativeFixtures.add({
          'history': history,
          'initial': bridge.fixture,
          'changed': changedFixture,
          'binding': f.binding
        });
        await fresh.readFrozenPending(h.store, f.id, 1);
        expect(fresh.fullBaselineReads, beforeAccept);
        h.reopen();
        final restarted = E4Workspace(h.root);
        await restarted.readFrozenPending(h.store, f.id, 1);
        expect(restarted.fullBaselineReads, 1);
        expect(h.store.work.snapshot()['frozen_full_recoveries'], 1);
        expect(cold.bundle.baseline.toJson(), full!.bundle.baseline.toJson());
        final d = sqlite3.open(h.store.path);
        costs.add({
          'history': history,
          'objects': d.select('SELECT count(*) AS n FROM objects').single['n'],
          'baseline_bytes':
              File('${h.workspace.root.path}/offline-mode/baseline.json')
                  .lengthSync(),
          'before': {
            'reads': 2,
            'full_baseline_parses': before.parses,
            'baseline_bytes_read': before.parseBytes,
            'full_lineage_hashes': before.hashes,
            'lineage_bytes_hashed': before.hashBytes,
            'elapsed_us': fullWatch.elapsedMicroseconds
          },
          'cold': {
            'full_baseline_parses': 1,
            'lineage_verifications': 1,
            'elapsed_us': coldWatch.elapsedMicroseconds
          },
          'warm': {
            'reads': 3,
            'full_baseline_parses': fresh.fullBaselineReads - parses,
            'lineage_verifications': fresh.lineageVerifications - hashes,
            'full_frozen_recoveries': warmWork['frozen_full_recoveries'] ?? 0,
            'verification_work': warmWork,
            'elapsed_us': watch.elapsedMicroseconds
          },
          'rss_bytes': ProcessInfo.currentRss,
          'pin_rows':
              d.select('SELECT count(*) AS n FROM generation_roots').single['n']
        });
        d.close();
      } finally {
        h.dispose();
        await bridge.dispose();
      }
    });
  }
  tearDownAll(() {
    const out = String.fromEnvironment('E4_COST_OUT');
    if (out.isNotEmpty) {
      File(out).writeAsStringSync(
          '${const JsonEncoder.withIndent('  ').convert(costs)}\n',
          flush: true);
    }
    const fixtureOut = String.fromEnvironment('E4_FIXTURE_OUT');
    if (fixtureOut.isNotEmpty) {
      File(fixtureOut)
          .writeAsStringSync(jsonEncode(nativeFixtures), flush: true);
    }
  });

  late BackendBridge bridge;
  late E4Harness h;
  late FrozenGeneration f;
  group('T03 invalidation', () {
    setUpAll(() async {
      bridge = await BackendBridge.start(history: 4);
    });
    tearDownAll(() => bridge.dispose());
    setUp(() async {
      h = await E4Harness.create(bridge, wire);
      f = (await h.install()).frozen;
    });
    tearDown(() => h.dispose());
    test(
        'cached B is deeply immutable and preserves original value representation',
        () async {
      final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      expect(() => b.authoritativeSnapshot!['data']['ledger_entries'].clear(),
          throwsUnsupportedError);
      expect(() => b.entries.clear(), throwsUnsupportedError);
      expect(() => b.settings.values['cash_flow_balance'] = 'changed',
          throwsUnsupportedError);
      expect((await h.workspace.readFrozenBaseline(h.store, f.id, 1)).toJson(),
          b.toJson());
    });
    test('benign external connection COMMIT forces exactly one full fallback',
        () async {
      final other =
          SegmentedClientStore.open(h.root, h.store.cache, adapters: true);
      other.createStaging(
          syncUuid(),
          ObservationManifest.fromBytes(
              encodeC1(GenerationFixture(bridge.fixture).manifest)),
          DateTime.now().toUtc());
      other.close();
      final before = h.workspace.fullBaselineReads;
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      expect(h.workspace.fullBaselineReads, before + 1);
      final again = h.workspace.fullBaselineReads;
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      expect(h.workspace.fullBaselineReads, again);
    });
    for (final missing in [false, true]) {
      test(
          'external corrupt/missing frozen object missing=$missing invalidates proof and preserves B',
          () async {
        final before = h.baselineFile.readAsBytesSync(),
            d = sqlite3.open(h.store.path);
        final triggers = d.select(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name IN ('immutable_body','retained_object_delete','retained_graph_object_delete')");
        for (final t in triggers) {
          d.execute('DROP TRIGGER ${t['name']}');
        }
        final hash = f.target.roots['raw']!.hash;
        if (missing) {
          d.execute('DELETE FROM objects WHERE hash=?', [hash]);
        } else {
          final bytes = List<int>.from(d.select(
              'SELECT body FROM objects WHERE hash=?',
              [hash]).single['body'] as List<int>);
          bytes[0] = 32;
          d.execute('UPDATE objects SET body=? WHERE hash=?', [bytes, hash]);
        }
        for (final t in triggers) {
          d.execute(t['sql'] as String);
        }
        d.close();
        await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 1),
            throwsA(isA<SegmentedException>()));
        expect(h.baselineFile.readAsBytesSync(), before);
      });
    }
    test('frozen pin association removal is not hidden by cached data',
        () async {
      final d = sqlite3.open(h.store.path);
      d.execute('DELETE FROM frozen WHERE id=?', [f.id]);
      d.close();
      await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 1),
          throwsA(isA<SegmentedException>()));
      expect(h.baselineFile.existsSync(), true);
    });
    test('legacy source discriminator mismatch is rejected', () async {
      final file = File('${h.workspace.root.path}/e4-source.json');
      final value = jsonDecode(file.readAsStringSync());
      value['namespace'] = 'wrong';
      file.writeAsStringSync(jsonEncode(value));
      await expectLater(h.workspace.readFrozenBaseline(h.store, f.id, 1),
          throwsA(isA<SegmentedException>()));
    });
    test('wrong stored metadata lineage cannot project J on another B',
        () async {
      await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint: '0' * 64));
      await expectLater(h.workspace.readFrozenPending(h.store, f.id, 1),
          throwsA(isA<SegmentedException>()));
    });
    test(
        'new pending append changes J view, never frozen B identity or raw verification',
        () async {
      final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint: f.binding['legacy_lineage']));
      final reads = h.workspace.fullBaselineReads;
      for (var n = 0; n < 2; n++) {
        await h.workspace.appendOperation(
            type: OfflineOperationType.createCashFlow,
            payload: {
              'occurred_on': '2026-10-14',
              'title': 'pending$n',
              'amount_value': '+0007.00',
              'is_primary_income': 0
            },
            baseline: b);
        final view = await h.workspace.readFrozenPending(h.store, f.id, 1);
        expect(view.bundle.operations.length, n + 1);
        expect(view.lineage, f.binding['legacy_lineage']);
      }
      expect(h.workspace.fullBaselineReads, reads);
    });
    test('AppState pending read uses frozen provenance with current authority',
        () async {
      await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint: f.binding['legacy_lineage']));
      h.state.connectivityMode = ConnectivityMode.offline;
      final before = h.workspace.fullBaselineReads;
      final result = await h.state
          .readSegmentedForIsolatedUse(h.store, includePending: true);
      expect(result.pendingLegacy!.lineage, f.binding['legacy_lineage']);
      await h.state.readSegmentedForIsolatedUse(h.store, includePending: true);
      expect(h.workspace.fullBaselineReads, before);
    });
  });
}
