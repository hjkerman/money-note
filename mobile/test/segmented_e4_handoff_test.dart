@Timeout(Duration(minutes: 5))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/e4_targeted_fixture.dart';
import 'support/segmented_e2_fixture.dart';
import 'support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late Map<String, dynamic> wire;
  late E4Harness h;
  void Function(String)? fault;
  void Function(String)? sqlFault;
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 4);
    wire = await e4WireOracle();
  });
  tearDownAll(() => bridge.dispose());
  setUp(() async {
    fault = null;
    sqlFault = null;
    // Authentication-race cases intentionally make old-session release
    // impossible. Expire their bounded server leases between independent cases;
    // do not let LEASE_LIMIT substitute for the context rejection being tested.
    await bridge.command({'command': 'advance', 'seconds': 901});
    h = await E4Harness.create(bridge, wire,
        fault: (p) => fault?.call(p), sqlFault: (p) => sqlFault?.call(p));
  });
  tearDown(() {
    bridge.before = null;
    h.dispose();
  });
  void checkDisk({required bool pending}) {
    expect(h.pendingFile.existsSync(), pending);
    final direct = sqlite3.open(h.store.path);
    expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
    expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
    direct.close();
  }

  test(
      'T01 original-ticket fresh backend acquisition installs complete legacy B, no substitute fingerprint',
      () async {
    final result = await h.install();
    final disk =
        jsonDecode(h.baselineFile.readAsStringSync()) as Map<String, dynamic>;
    expect(disk['authoritative_snapshot']['snapshot_id'],
        result.frozen.binding['snapshot_id']);
    expect(disk['server_state_fingerprint'],
        result.frozen.binding['legacy_fingerprint']);
    expect(disk['server_state_fingerprint'],
        isNot(result.publication.target.syncRoot));
    expect(h.state.summary!.toString(), isNotEmpty);
    expect(h.state.lastSuccessfulSyncAt!.toUtc().toIso8601String(),
        disk['synced_at']);
    expect(result.frozen.installed, true);
    expect(result.pendingRemains, false);
    final d = sqlite3.open(h.store.path);
    final receipt = jsonDecode(utf8.decode(d.select(
        'SELECT receipt FROM generations WHERE id=?',
        [result.publication.generationId]).single['receipt'] as List<int>));
    expect(receipt['authority_history']['request'], 1);
    expect(d.select('SELECT state FROM frozen').single['state'], 'installed');
    d.close();
    checkDisk(pending: false);
  });
  for (final confirmed in [false, true]) {
    test(
        'T01 pending confirmed=$confirmed uses durable token/status, never content matching',
        () async {
      final p = await h.workspace.beginOnlineWrite(1);
      if (confirmed) await h.workspace.savePendingOnlineWrite(p.committed());
      final before = h.pendingFile.readAsBytesSync();
      final result = await h.install();
      expect(result.pendingRemains, !confirmed);
      checkDisk(pending: !confirmed);
      if (!confirmed) expect(h.pendingFile.readAsBytesSync(), before);
      expect(h.state.authoritativeRebuildPending, !confirmed);
    });
  }
  Future<void> networkRace(Future<void> Function() change) async {
    final p = await h.workspace.beginOnlineWrite(1);
    final bytes = h.pendingFile.readAsBytesSync();
    final entered = Completer<void>(), release = Completer<void>();
    var once = false;
    bridge.before = (path) async {
      if (!once && path.endsWith('/observations')) {
        once = true;
        entered.complete();
        await release.future;
      }
    };
    final result = h.install();
    await entered.future;
    await change();
    final b = h.baselineFile.readAsBytesSync();
    release.complete();
    await expectLater(result, throwsA(isA<Exception>()));
    expect(h.baselineFile.readAsBytesSync(), b);
    expect(h.pendingFile.readAsBytesSync(), bytes);
    expect((await h.workspace.loadPendingOnlineWrite(1))!.token, p.token);
    checkDisk(pending: true);
  }

  test('T01 logout after acquisition begins preserves original marker and B',
      () => networkRace(() => h.state.logout()));
  test(
      'T01 same-user reauthentication invalidates original ticket',
      () => networkRace(
          () => h.state.login('synthetic', 'synthetic-only-password')));
  test('T01 credential changes before AppState auth-generation update',
      () => networkRace(() => h.api.saveSession('synthetic-replaced')));
  test(
      'T01 wrong current user invalidates original ticket',
      () => networkRace(() async {
            h.state.user = baselineFixture().user;
            h.state.user = null;
          }));
  test(
      'T01 mode change invalidates original ticket',
      () => networkRace(() async {
            h.state.connectivityMode = ConnectivityMode.offline;
          }));
  test('T01 newer legacy refresh invalidates original segmented operation',
      () => networkRace(() => h.state.refresh(notify: false)));
  test(
      'T01 newer segmented request cannot authorize old acquired result',
      () => networkRace(() async {
            try {
              await h.state.readSegmentedForIsolatedUse(h.store);
            } on Object {/* ticket issued, empty cache is not authority */}
          }));
  for (final point in [
    'after_e3_acceptance',
    'after_legacy_materialization',
    'before_legacy_rename',
    'before_installation',
    'before_pending_retire'
  ]) {
    test('T01 authority rechecked after hook $point', () async {
      final p = await h.workspace.beginOnlineWrite(1);
      await h.workspace.savePendingOnlineWrite(p.committed());
      final before = h.pendingFile.readAsBytesSync();
      fault = (actual) {
        if (actual == point) {
          h.state.connectivityMode = ConnectivityMode.offline;
        }
      };
      await expectLater(h.install(), throwsA(isA<Exception>()));
      expect(h.pendingFile.readAsBytesSync(), before);
      expect(h.state.summary, null);
      checkDisk(pending: true);
    });
  }
  test(
      'T01 actual mutation invalidates request, preserves resulting confirmed pending',
      () async {
    final entered = Completer<void>(), release = Completer<void>();
    var once = false;
    bridge.before = (p) async {
      if (!once && p.endsWith('/observations')) {
        once = true;
        entered.complete();
        await release.future;
      }
    };
    final op = h.install();
    await entered.future;
    await h.state.updateSetting('owner_card_last4', '1234');
    final b = h.baselineFile.readAsBytesSync();
    release.complete();
    await expectLater(op, throwsA(isA<Exception>()));
    expect(h.baselineFile.readAsBytesSync(), b);
    expect(h.state.settings.values['owner_card_last4'], isNot('stale'));
  });
  test('T01 active legacy J/frozen epoch cannot be migrated or rebased',
      () async {
    final b = baselineFixture();
    await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint: h.workspace.recoveryLineageFingerprint(b)));
    await h.workspace.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: {
          'occurred_on': '2026-10-14',
          'title': 'pending',
          'amount_value': '+0007.00',
          'is_primary_income': 0
        },
        baseline: b);
    final j = File('${h.workspace.root.path}/offline-mode/journal.ndjson')
        .readAsBytesSync();
    await expectLater(h.install(), throwsA(isA<SegmentedException>()));
    expect(
        File('${h.workspace.root.path}/offline-mode/journal.ndjson')
            .readAsBytesSync(),
        j);
    expect(h.store.frozenGenerations(), isEmpty);
  });
  test('T01 confirmed marker replacement in final hook cannot delete new input',
      () async {
    final p = await h.workspace.beginOnlineWrite(1);
    await h.workspace.savePendingOnlineWrite(p.committed());
    fault = (point) {
      if (point == 'before_pending_retire') {
        h.pendingFile.writeAsStringSync(
            jsonEncode(const PendingOnlineWrite(
                    1, 'new-input', OnlineWriteStatus.outcomeUnknown)
                .toJson()),
            flush: true);
      }
    };
    await expectLater(h.install(), throwsA(isA<SegmentedException>()));
    expect((await h.workspace.loadPendingOnlineWrite(1))!.token, 'new-input');
    expect(h.state.summary, null);
    checkDisk(pending: true);
  });
  test(
      'T01 baseline write failure preserves previous valid B and confirmed marker',
      () async {
    final p = await h.workspace.beginOnlineWrite(1);
    await h.workspace.savePendingOnlineWrite(p.committed());
    final before = h.baselineFile.readAsBytesSync();
    fault = (point) {
      if (point == 'before_legacy_rename') {
        throw StateError('synthetic disk failure');
      }
    };
    await expectLater(h.install(), throwsA(isA<StateError>()));
    expect(h.baselineFile.readAsBytesSync(), before);
    checkDisk(pending: true);
    expect(h.store.frozenGenerations(), isEmpty);
  });
  test('T01 R1 gate remains closed after valid adapter installation', () async {
    await h.install();
    expect(await h.state.enterOfflineMode(), false);
    expect(h.state.isOnline, true);
    await expectLater(h.workspace.loadBaseline(),
        throwsA(isA<OfflinePersistenceException>()));
    final again = E4Workspace(h.root);
    await expectLater(
        again.loadBaseline(), throwsA(isA<OfflinePersistenceException>()));
  });

  test(
      'T01 account switch to another principal rejects original installation',
      () => networkRace(() async {
            h.state.user = AuthUser(
                id: 2,
                username: 'synthetic-other',
                displayName: '합성 다른 사용자',
                sharePinNeedsChange: false);
          }));
  for (final field in ['dataset_id', 'epoch']) {
    test('T01 wrong expected $field fails before persistence or installation',
        () async {
      final target = GenerationFixture(bridge.fixture).target.toJson();
      target['ns'][field] = syncUuid();
      target.remove('sync_root');
      target['sync_root'] = objectHash('view', encodeC1(target));
      final cache =
          CacheNamespace.forTarget(syntheticOrigin, SyncTarget.parse(target));
      final wrong = SegmentedClientStore.open(h.root, cache, adapters: true),
          before = h.baselineFile.readAsBytesSync();
      try {
        await expectLater(
            h.state.refreshSegmentedForIsolatedUse(wrong),
            throwsA(isA<AcquisitionFailure>().having((e) => e.code,
                'E2 context rejection', 'CACHE_CONTEXT_MISMATCH')));
        expect(wrong.acceptedGeneration().id, null);
        expect(wrong.installedGeneration(), null);
        expect(h.baselineFile.readAsBytesSync(), before);
      } finally {
        wrong.close();
      }
    });
  }
  test(
      'T01 original ticket becomes stale while queued behind actual legacy lineage lock',
      () async {
    h.workspace.pauseRename();
    final legacy = h.state.refreshInputArea(notify: false);
    final legacyRejected = expectLater(legacy, throwsA(isA<Exception>()));
    await h.workspace.entered!.future;
    final queued = Completer<void>();
    sqlFault = (point) {
      if (point == 'after_generation_pins' && !queued.isCompleted) {
        queued.complete();
      }
    };
    final segmented = h.state.refreshSegmentedForIsolatedUse(h.store);
    final rejected = expectLater(segmented, throwsA(isA<Exception>()));
    await queued.future;
    try {
      await h.state.readSegmentedForIsolatedUse(h.store);
    } on Object {/* new actual coordinator ticket */}
    h.workspace.release!.complete();
    await legacyRejected;
    await rejected;
    expect(h.store.installedGeneration(), null);
    expect(h.state.summary, null);
  });

  group('segmented-native T01', () {
    for (final confirmed in [null, false, true]) {
      test(
          'native complete-store handoff pending=$confirmed has no legacy baseline rewrite',
          () async {
        if (confirmed != null) {
          final p = await h.workspace.beginOnlineWrite(1);
          if (confirmed) {
            await h.workspace.savePendingOnlineWrite(p.committed());
          }
        }
        final before = h.baselineFile.readAsBytesSync();
        final result = await h.state.refreshSegmentedForIsolatedUse(h.store);
        expect(h.baselineFile.readAsBytesSync(), before);
        expect(h.workspace.fullBaselineReads, 0);
        expect(h.workspace.lineageVerifications, 0);
        expect(
            h.store.installedGeneration()!.id, result.publication.generationId);
        expect(result.authority.completeStoreHandle.generation.id,
            result.publication.generationId);
        expect(h.state.summary!.cashFlowBalance,
            result.authority.candidate.summary.cashFlowBalance);
        expect(result.pendingRemains, confirmed == false);
        checkDisk(pending: confirmed == false);
      });
    }
    test(
        'native unchanged and one-change refresh do not repeat raw/full recovery or legacy hashes',
        () async {
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      final work = h.store.work.snapshot(), downloaded = bridge.objectRequests;
      final same = await h.state.refreshSegmentedForIsolatedUse(h.store);
      expect(bridge.objectRequests - downloaded, 0);
      expect(h.store.work.since(work)['full_verifications'] ?? 0, 0);
      expect(h.workspace.fullBaselineReads, 0);
      expect(h.workspace.lineageVerifications, 0);
      await bridge.command({'command': 'mutate'});
      final before = h.store.work.snapshot();
      final next = await h.state.refreshSegmentedForIsolatedUse(h.store);
      expect(next.publication.target.syncRoot,
          isNot(same.publication.target.syncRoot));
      expect(h.store.work.since(before)['full_verifications'] ?? 0, 0);
      expect(h.workspace.fullBaselineReads, 0);
    });
    test('native stale ticket after E3 acceptance cannot install or retire',
        () async {
      final p = await h.workspace.beginOnlineWrite(1);
      await h.workspace.savePendingOnlineWrite(p.committed());
      final before = h.baselineFile.readAsBytesSync(),
          marker = h.pendingFile.readAsBytesSync();
      fault = (point) {
        if (point == 'after_e3_acceptance') {
          h.state.connectivityMode = ConnectivityMode.offline;
        }
      };
      await expectLater(h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<Exception>()));
      expect(h.baselineFile.readAsBytesSync(), before);
      expect(h.pendingFile.readAsBytesSync(), marker);
      expect(h.store.installedGeneration(), null);
      expect(h.state.summary, null);
    });
    test('native session change before installation preserves confirmed input',
        () async {
      final p = await h.workspace.beginOnlineWrite(1);
      await h.workspace.savePendingOnlineWrite(p.committed());
      final marker = h.pendingFile.readAsBytesSync();
      fault = (point) {
        if (point == 'before_installation') {
          unawaited(h.api.saveSession('synthetic-new-credential'));
        }
      };
      await expectLater(h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<Exception>()));
      expect(h.pendingFile.readAsBytesSync(), marker);
      expect(h.state.summary, null);
    });
    test(
        'native data COMMIT followed by failure is not falsely reported as rollback',
        () async {
      final p = await h.workspace.beginOnlineWrite(1);
      await h.workspace.savePendingOnlineWrite(p.committed());
      fault = (point) {
        if (point == 'after_e4_installation') {
          throw StateError('post-install failure');
        }
      };
      await expectLater(h.state.refreshSegmentedForIsolatedUse(h.store),
          throwsA(isA<E4InstallationCommittedException>()));
      expect(h.store.installedGeneration(), isNotNull);
      expect(h.pendingFile.existsSync(), false);
      expect(h.state.summary, isNotNull);
    });
    test(
        'native installed handle retains G1 across later G2/G3 cache publications',
        () async {
      final g1 = await h.state.refreshSegmentedForIsolatedUse(h.store);
      final requiredId = g1.publication.generationId;
      for (var n = 0; n < 2; n++) {
        await bridge.command({'command': 'mutate'});
        await h.publish();
      }
      expect(h.store.acceptedGeneration().previousId, isNot(requiredId));
      final result = await g1.authority.completeStoreHandle.read(
          (r) => {'id': r.generation.id, 'rows': r.rows('ledger_entries')});
      expect(result['id'], requiredId);
      expect((result['rows'] as List).isNotEmpty, true);
      expect(h.store.discardUnacceptedGeneration(requiredId), false);
    });
    test('native G2 keeps original frozen G1 legacy identity and B/J separate',
        () async {
      final g1 = (await h.install()).frozen,
          before = h.baselineFile.readAsBytesSync();
      await bridge.command({'command': 'mutate'});
      final g2 = await h.state.refreshSegmentedForIsolatedUse(h.store);
      expect(g2.publication.generationId, isNot(g1.generationId));
      expect(h.baselineFile.readAsBytesSync(), before);
      final b = await h.workspace.readFrozenBaseline(h.store, g1.id, 1);
      expect(h.workspace.recoveryLineageFingerprint(b),
          g1.binding['legacy_lineage']);
      await h.workspace.saveMetadata(OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint: g1.binding['legacy_lineage']));
      h.state.connectivityMode = ConnectivityMode.offline;
      final read = await h.state
          .readSegmentedForIsolatedUse(h.store, includePending: true);
      expect(read.segmented.generationId, g2.publication.generationId);
      expect(read.pendingLegacy!.lineage, g1.binding['legacy_lineage']);
    });
    test(
        'native general-user Offline remains R1-gated with legacy fallback bytes intact',
        () async {
      final before = h.baselineFile.readAsBytesSync();
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      expect(await h.state.enterOfflineMode(), false);
      expect(h.state.isOnline, true);
      expect(h.baselineFile.readAsBytesSync(), before);
    });
    test(
        'native original ticket is allocated once before E2 and no persisted permit is consumed',
        () {
      final source = File('lib/src/app_state.dart').readAsStringSync();
      final begin = source.indexOf(
          '  Future<E4SegmentedInstallation> refreshSegmentedForIsolatedUse(');
      final end = source.indexOf('  // Explicit isolated E4 read only.', begin),
          seam = source.substring(begin, end);
      expect(RegExp('_refreshCoordinator.begin').allMatches(seam).length, 1);
      expect(seam.indexOf('_refreshCoordinator.begin'),
          lessThan(seam.indexOf('.acquire(')));
      for (final forbidden in [
        'materializeLegacyRead(',
        'AuthoritativeBaselineEnvelope(',
        'recoveryLineageFingerprint(',
        'replaceBaseline('
      ]) {
        expect(seam.contains(forbidden), false, reason: forbidden);
      }
      expect(File('lib/src/segmented/store.dart').readAsStringSync(),
          contains("finalFence?.call();\n      _db.execute('COMMIT');"));
      expect(File('lib/src/segmented/workspace.dart').readAsStringSync(),
          contains('guard();\n    file.deleteSync();'));
    });
  });
}
