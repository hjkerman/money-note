@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late E4Harness h;
  late Map<String, dynamic> wire;
  void Function(String)? fault, sqlFault;
  final evidence = <Map<String, dynamic>>[];
  var ordinal = 0;
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 7);
    wire = await e4WireOracle();
  });
  tearDownAll(() async {
    const out = String.fromEnvironment('AUDIT_E4_OUT');
    if (out.isNotEmpty) {
      File(out).writeAsStringSync(jsonEncode(evidence));
    }
    await bridge.dispose();
  });
  setUp(() async {
    fault = null;
    sqlFault = null;
    await bridge.command({'command': 'advance', 'seconds': 901});
    h = await E4Harness.create(
      bridge,
      wire,
      fault: (p) => fault?.call(p),
      sqlFault: (p) => sqlFault?.call(p),
    );
    // Phase A focuses on E4. These real server bytes still pass E1 validation;
    // E2 must obtain a fresh authenticated observation and verify membership.
    final cached = await bridge.command({'command': 'oracle'});
    for (final o in cached['objects']) {
      h.store.putVerifiedObject(
        ObjectRef.parse(o['ref']),
        base64Decode(o['data_base64']),
      );
    }
    ordinal++;
  });
  tearDown(() {
    bridge.before = null;
    h.dispose();
  });

  Map<String, dynamic> rows() {
    final d = sqlite3.open(h.store.path);
    try {
      return {
        for (final t in ['accepted', 'installed', 'frozen', 'generation_roots'])
          t: d
              .select('SELECT * FROM $t')
              .map(
                (r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? base64Encode(v) : v),
                ),
              )
              .toList(),
      };
    } finally {
      d.close();
    }
  }

  Future<Map<String, dynamic>> inspect({bool legacy = true}) async {
    final repo = Directory.current.parent.path;
    final p = await Process.run('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
      h.store.path,
      if (legacy) h.workspace.root.path,
    ]);
    expect(p.exitCode, 0, reason: p.stderr as String);
    final result = jsonDecode(p.stdout as String) as Map<String, dynamic>;
    evidence.add({'case': ordinal, 'persisted': result});
    return result;
  }

  Future<void> install(bool native, {SyncCancellation? cancellation}) async {
    if (native) {
      await h.state.refreshSegmentedForIsolatedUse(
        h.store,
        cancellation: cancellation,
      );
    } else {
      await h.state.installSegmentedLegacyForIsolatedUse(
        h.store,
        cancellation: cancellation,
      );
    }
  }

  for (final native in [false, true]) {
    test(
      'FA01 positive native=$native, independent persisted graph and identity',
      () async {
        final before = h.baselineFile.readAsBytesSync();
        await install(native);
        final actual = await inspect(legacy: !native);
        final g = (actual['generations'] as Map).values.single as Map;
        final oracle = await bridge.command({'command': 'oracle'});
        expect(
          (g['closure'] as List).toSet(),
          (oracle['objects'] as List).map((o) => o['ref']['hash']).toSet(),
        );
        for (final table in (oracle['source'] as Map).keys) {
          final expectedRows =
              (oracle['source'][table] as List)
                  .map(encodeC1)
                  .map(base64Encode)
                  .toList()
                ..sort();
          final actualRows =
              (g['source'][table] as List)
                  .map(encodeC1)
                  .map(base64Encode)
                  .toList()
                ..sort();
          expect(actualRows, expectedRows, reason: table as String);
        }
        expect(h.state.summary, isNotNull);
        final hotRef = oracle['manifest']['target']['hot_ref']['hash'];
        final hotObject = (oracle['objects'] as List).singleWhere(
          (o) => o['ref']['hash'] == hotRef,
        );
        final hot =
            jsonDecode(
                  utf8.decode(base64Decode(hotObject['data_base64'])),
                )['state']
                as Map;
        final summary = h.state.summary!;
        final values = {
          'scheduled_income': summary.scheduledIncome,
          'card_total': summary.cardTotal,
          'current_spending_total': summary.currentSpendingTotal,
          'current_discount_total': summary.currentDiscountTotal,
          'planned_recurring_total': summary.plannedRecurringTotal,
          'fixed_cash_total': summary.fixedCashTotal,
          'fixed_cash_processed_total': summary.fixedCashProcessedTotal,
          'frozen_asset_total': summary.frozenAssetTotal,
          'cash_flow_balance': summary.cashFlowBalance,
          'remaining_liquidity': summary.remainingLiquidity,
          'current_month_spendable': summary.currentMonthSpendable,
          'claim_original_total': summary.claimOriginalTotal,
          'claim_net_total': summary.claimNetTotal,
          'family_card_original_total': summary.familyCardOriginalTotal,
          'family_card_net_total': summary.familyCardNetTotal,
          'visible_cash_flow_total': summary.visibleCashFlowTotal,
        };
        for (final key in values.keys) {
          expect(values[key], hot['summary'][key], reason: key);
        }
        expect(h.state.settings.values, hot['settings']);
        expect(
          h.state.cardPaymentStatus!.effectiveRemainingTotal,
          hot['card_payment_status']['effective_remaining_total'],
        );
        expect(
          h.state.monthCloseStatus!.calendarDate,
          hot['month_close_status']['calendar_date'],
        );
        for (final pair in [
          [h.state.entries, hot['entries']],
          [h.state.confirmedPlannedEntries, hot['confirmed_planned_entries']],
        ]) {
          final typed = pair[0] as List<LedgerEntry>, raw = pair[1] as List;
          expect(typed.length, raw.length);
          for (var i = 0; i < typed.length; i++) {
            expect(
              [
                typed[i].id,
                typed[i].title,
                typed[i].amountValue,
                typed[i].effectiveAmountValue,
                typed[i].effectiveDiscountAmount,
              ],
              [
                raw[i]['id'],
                raw[i]['title'],
                raw[i]['amount_value'],
                raw[i]['effective_amount_value'],
                raw[i]['effective_discount_amount'],
              ],
            );
          }
        }
        if (native) expect(h.baselineFile.readAsBytesSync(), before);
      },
    );
    test(
      'FA02 unknown pending native=$native survives matching downloaded source and restart',
      () async {
        await h.workspace.beginOnlineWrite(1);
        final original = h.pendingFile.readAsBytesSync();
        await install(native);
        expect(h.pendingFile.readAsBytesSync(), original);
        h.reopen();
        await E4Workspace(h.root).recoverLegacyHandoff(h.store);
        expect(h.pendingFile.readAsBytesSync(), original);
        await inspect(legacy: !native);
      },
    );
    for (final point in [
      'after_e3_acceptance',
      'before_source_rename',
      'before_installation',
      'before_pending_retire',
    ]) {
      test(
        'FA03 stale mode native=$native at $point cannot retire or install UI',
        () async {
          final pending = await h.workspace.beginOnlineWrite(1);
          await h.workspace.savePendingOnlineWrite(pending.committed());
          final marker = h.pendingFile.readAsBytesSync();
          final before = h.baselineFile.readAsBytesSync();
          fault = (p) {
            if (p == point) h.state.connectivityMode = ConnectivityMode.offline;
          };
          await expectLater(install(native), throwsA(isA<Exception>()));
          expect(h.pendingFile.readAsBytesSync(), marker);
          expect(h.state.summary, null);
          if (point == 'after_e3_acceptance' ||
              point == 'before_source_rename') {
            expect(h.baselineFile.readAsBytesSync(), before);
            expect(rows()['installed'], isEmpty);
          }
          await inspect(legacy: !native);
        },
      );
    }
    test(
      'FA04 credential replacement after accepted COMMIT native=$native',
      () async {
        await h.workspace.beginOnlineWrite(1);
        final marker = h.pendingFile.readAsBytesSync(),
            before = h.baselineFile.readAsBytesSync();
        Future<void>? changed;
        fault = (p) {
          if (p == 'after_e3_acceptance')
            changed = h.api.saveSession('audit-only-new-session');
        };
        await expectLater(install(native), throwsA(isA<Exception>()));
        await changed;
        expect(h.pendingFile.readAsBytesSync(), marker);
        expect(h.baselineFile.readAsBytesSync(), before);
        expect(rows()['installed'], isEmpty);
        expect(h.state.summary, null);
        await inspect(legacy: !native);
      },
    );
    test(
      'FA05 cancellation at final retirement native=$native is persistent no-op',
      () async {
        final pending = await h.workspace.beginOnlineWrite(1);
        await h.workspace.savePendingOnlineWrite(pending.committed());
        final marker = h.pendingFile.readAsBytesSync(),
            cancel = SyncCancellation();
        fault = (p) {
          if (p == 'before_pending_retire') cancel.cancel();
        };
        await expectLater(
          install(native, cancellation: cancel),
          throwsA(isA<Exception>()),
        );
        expect(h.pendingFile.readAsBytesSync(), marker);
        expect(h.state.summary, null);
        await inspect(legacy: !native);
      },
    );
    test(
      'FA06 different current principal after acceptance native=$native',
      () async {
        final before = h.baselineFile.readAsBytesSync();
        fault = (p) {
          if (p == 'after_e3_acceptance')
            h.state.user = AuthUser(
              id: 77,
              username: 'audit',
              displayName: '합성',
              sharePinNeedsChange: false,
            );
        };
        await expectLater(install(native), throwsA(isA<Exception>()));
        expect(h.baselineFile.readAsBytesSync(), before);
        expect(rows()['installed'], isEmpty);
        await inspect(legacy: !native);
      },
    );
  }

  test('FA07 new legacy request while original waits cannot authorize old prepared B', () async {
    h.workspace.pauseRename();
    final operation = h.install();
    await h.workspace.entered!.future;
    // begin() is synchronous before acquire; this really advances the existing coordinator.
    final newer = h.state.refresh(notify: false);
    h.workspace.release!.complete();
    await expectLater(operation, throwsA(isA<Exception>()));
    await newer;
    expect(rows()['installed'], isEmpty);
    expect(h.store.frozenGenerations(), isEmpty);
  });

  test('FA08 frozen G1 remains separate from accepted/installed G2-G3 across reopen', () async {
    final f = (await h.install()).frozen;
    final old = await inspect();
    final wanted = old['generations'][f.generationId]['closure'];
    for (var i = 0; i < 3; i++) {
      await bridge.command({'command': 'mutate'});
      await h.state.refreshSegmentedForIsolatedUse(h.store);
    }
    final current = h.store.acceptedGeneration();
    expect([current.id, current.previousId], isNot(contains(f.generationId)));
    expect(h.store.discardUnacceptedGeneration(f.generationId), false);
    h.reopen();
    final workspace = E4Workspace(h.root);
    final b = await workspace.readFrozenBaseline(h.store, f.id, 1);
    final check = await inspect();
    expect(check['generations'][f.generationId]['closure'], wanted);
    expect(
      workspace.recoveryLineageFingerprint(b),
      f.binding['legacy_lineage'],
    );
    await expectLater(
      workspace.loadBaseline(),
      throwsA(isA<OfflinePersistenceException>()),
    );
  });
  test(
    'FA09 installed frozen ownership cannot be discarded, with unchanged rows',
    () async {
      final f = (await h.install()).frozen, before = rows();
      expect(
        () => h.store.discardFrozenPreparation(f, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()),
      );
      expect(rows(), before);
      await inspect();
    },
  );
  test('FA10 reader lifetime differs from durable frozen lifetime, detached view closes', () async {
    final f = (await h.install()).frozen;
    AcceptedReadView? escaped;
    final before = rows();
    await h.store.recoverFrozenGeneration(f.id);
    h.store.withFrozenRead(f, (r) {
      escaped = r;
      expect(r.rows('ledger_entries'), isNotEmpty);
    });
    expect(
      () => escaped!.rows('ledger_entries'),
      throwsA(isA<SegmentedException>()),
    );
    expect(rows(), before);
    await inspect();
  });

  for (final corruption in [
    'trigger',
    'receipt',
    'root_pin',
    'raw_bytes',
    'missing_raw',
    'lineage',
    'source',
    'schema',
  ]) {
    test(
      'FA11 warm Frozen-B invalidation $corruption, previous B and marker untouched',
      () async {
        final f = (await h.install()).frozen;
        await h.workspace.readFrozenBaseline(h.store, f.id, 1);
        await h.workspace.beginOnlineWrite(1);
        final before = h.baselineFile.readAsBytesSync(),
            pending = h.pendingFile.readAsBytesSync();
        final d = sqlite3.open(h.store.path);
        if (corruption == 'trigger') d.execute('DROP TRIGGER frozen_limit');
        if (corruption == 'schema') d.execute('PRAGMA user_version=88');
        if (corruption == 'receipt') {
          final sql =
              d
                      .select(
                        "SELECT sql FROM sqlite_master WHERE name='immutable_generation'",
                      )
                      .single['sql']
                  as String;
          d.execute('DROP TRIGGER immutable_generation');
          d.execute("UPDATE generations SET receipt=x'7b7d' WHERE id=?", [
            f.generationId,
          ]);
          d.execute(sql);
        }
        if (corruption == 'root_pin') {
          final sql =
              d
                      .select(
                        "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'",
                      )
                      .single['sql']
                  as String;
          d.execute('DROP TRIGGER retained_root_delete');
          d.execute(
            'DELETE FROM generation_roots WHERE generation_id=? AND hash=?',
            [f.generationId, f.target.roots['hot']!.hash],
          );
          d.execute(sql);
        }
        if (corruption == 'raw_bytes' || corruption == 'missing_raw') {
          final hash = d
              .select(
                "SELECT hash FROM objects WHERE kind='snapshot-leaf' ORDER BY hash LIMIT 1",
              )
              .single['hash'];
          final triggers = d.select(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='objects'",
          );
          for (final row in triggers) {
            d.execute('DROP TRIGGER ${row['name']}');
          }
          if (corruption == 'raw_bytes') {
            d.execute("UPDATE objects SET body=x'7b7d' WHERE hash=?", [hash]);
          } else {
            d.execute('DELETE FROM objects WHERE hash=?', [hash]);
          }
          // Restore exact schema: exercise hash/closure invalidation, not just missing triggers.
          for (final row in triggers) {
            d.execute(row['sql'] as String);
          }
        }
        d.close();
        if (corruption == 'lineage') {
          final p = jsonDecode(
            h.baselineFile.readAsStringSync(),
          ) as Map<String, dynamic>;
          p['synced_at'] = '2020-01-01T00:00:00.000Z';
          h.baselineFile.writeAsStringSync(jsonEncode(p), flush: true);
        }
        if (corruption == 'source') {
          final file = File('${h.workspace.root.path}/e4-source.json');
          final s = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
          s['binding'] = '0' * 64;
          file.writeAsStringSync(jsonEncode(s), flush: true);
        }
        final preAttempt = h.baselineFile.readAsBytesSync();
        await expectLater(
          h.workspace.readFrozenBaseline(h.store, f.id, 1),
          throwsA(isA<Exception>()),
        );
        expect(h.baselineFile.readAsBytesSync(), preAttempt);
        expect(h.pendingFile.readAsBytesSync(), pending);
        if (corruption != 'lineage') expect(preAttempt, before);
        evidence.add({
          'case': ordinal,
          'injected': corruption,
          'legacy_write': false,
          'marker_write': false,
        });
      },
    );
  }
  test('FA12 failed frozen install transaction retains old installed owner and prepared pin', () async {
    final old = (await h.install()).frozen;
    await bridge.command({'command': 'mutate'});
    sqlFault = (p) {
      if (p == 'after_frozen_install') throw StateError('audit rollback');
    };
    await expectLater(
      h.install(),
      throwsA(
        isA<StateError>().having((e) => e.message, 'message', 'audit rollback'),
      ),
    );
    final d = sqlite3.open(h.store.path);
    final owners = d
        .select('SELECT id,state FROM frozen')
        .map((r) => Map<String, dynamic>.from(r))
        .toList();
    d.close();
    expect(
      owners.any((r) => r['id'] == old.id && r['state'] == 'installed'),
      true,
    );
    expect(owners.where((r) => r['state'] == 'prepared').length, 1);
    expect(
      h.state.summary,
      isNotNull,
    ); // previous complete UI, never partial replacement
  });
  test('FA13 wrong owner and changed lineage cannot share cached frozen authority', () async {
    final f = (await h.install()).frozen;
    await expectLater(
      h.workspace.readFrozenBaseline(h.store, f.id, 77),
      throwsA(isA<SegmentedException>()),
    );
    await h.workspace.saveMetadata(
      const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
        baselineLineageFingerprint:
            '0000000000000000000000000000000000000000000000000000000000000000',
      ),
    );
    await expectLater(
      h.workspace.readFrozenPending(h.store, f.id, 1),
      throwsA(isA<SegmentedException>()),
    );
    await inspect();
  });
  test('FA14 real SQLite read snapshot excludes concurrent G2 COMMIT then permits retry', () async {
    final frozen = (await h.install()).frozen;
    final g1 = await h.store.recoverAcceptedGeneration();
    await bridge.command({'command': 'mutate'});
    final other = SegmentedClientStore.open(
      h.root,
      h.store.cache,
      adapters: true,
    );
    try {
      final base = await other.recoverAcceptedGeneration();
      final acquired = await IncrementalFetcher(
        other,
        segmentedTransportForApi(h.api),
      ).acquire(verifiedBase: base);
      final version = other.publicationDataVersion;
      final proof = await other.verifyPublicationCandidate(
        acquired.manifest,
        base,
        verifiedDataVersion: version,
      );
      final p = other.prepareGeneration(
        syncUuid(),
        acquired.stagingId,
        proof,
        base,
        verifiedDataVersion: version,
      );
      // External writes invalidate G1 provenance; revalidate before opening the scope.
      final recovered = await h.store.recoverFrozenGeneration(frozen.id);
      h.store.withFrozenRead(recovered, (r) {
        final first = r.rows('ledger_entries');
        expect(
          () => other.commitPreparedGeneration(p, finalAuthorityFence: () {}),
          throwsA(isA<SegmentedException>()),
        );
        expect(r.generation.id, g1.id);
        expect(r.rows('ledger_entries'), first);
      });
      other.commitPreparedGeneration(p, finalAuthorityFence: () {});
      expect((await h.store.recoverAcceptedGeneration()).id, isNot(g1.id));
      await inspect();
    } finally {
      other.close();
    }
  });
  test(
    'FA15 equal v7 contents cannot substitute resolved reconciliation lineage',
    () async {
      final frozen = (await h.install()).frozen;
      await h.workspace.beginOnlineWrite(1);
      final marker = h.pendingFile.readAsBytesSync(), before = rows();
      final disk =
          jsonDecode(h.baselineFile.readAsStringSync()) as Map<String, dynamic>;
      final snapshot = jsonEncode(disk['authoritative_snapshot']);
      disk['resolved_reconciliation_id'] = 'independent-different-lineage';
      h.baselineFile.writeAsStringSync(jsonEncode(disk), flush: true);
      final altered = h.baselineFile.readAsBytesSync();
      await expectLater(
        h.workspace.readFrozenBaseline(h.store, frozen.id, 1),
        throwsA(
          isA<SegmentedException>().having(
            (e) => e.code,
            'code',
            'LEGACY_LINEAGE_UNAVAILABLE',
          ),
        ),
      );
      expect(
        jsonEncode(
          jsonDecode(
            h.baselineFile.readAsStringSync(),
          )['authoritative_snapshot'],
        ),
        snapshot,
      );
      expect(h.baselineFile.readAsBytesSync(), altered);
      expect(h.pendingFile.readAsBytesSync(), marker);
      expect(rows(), before);
    },
  );
  test('FA16 real AppState offline entry remains closed after successful isolated E4', () async {
    await h.install();
    final baseline = h.baselineFile.readAsBytesSync(), before = rows();
    expect(await h.state.enterOfflineMode(), false);
    expect(
      h.state.offlineEntryMessage,
      contains('R1_RECOVERY_CONTRACT_REQUIRED'),
    );
    expect(h.state.connectivityMode, ConnectivityMode.online);
    expect(h.baselineFile.readAsBytesSync(), baseline);
    expect(await h.workspace.loadJournal(), isEmpty);
    expect(rows(), before);
    await inspect();
  });
}
