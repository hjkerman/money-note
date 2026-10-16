@Timeout(Duration(minutes: 18))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../t66e4-a01-reaudit/cost_test.dart' as original;

void main() {
  // The original observer/assertions run unchanged in the same disposable copy.
  original.main();
  final results = <Map<String, dynamic>>[];
  tearDownAll(() {
    const out = String.fromEnvironment('AUDIT_E4_COST');
    File('$out.handoff.json').writeAsStringSync(jsonEncode(results));
  });
  for (final size in [5, 512]) {
    test('RA01 independent native prerequisite/handoff cost history=$size', () async {
      final bridge = await BackendBridge.start(history: size);
      final h = await E4Harness.create(bridge, await e4WireOracle());
      final phases = <Map<String, dynamic>>[];
      final source = File('${h.workspace.root.path}/e4-source.json');
      try {
        Map<String, Map<String, dynamic>> pins() {
          final db = sqlite3.open(h.store.path);
          try {
            return {
              for (final r in db.select('SELECT * FROM generation_roots'))
                '${r['generation_id']}:${r['hash']}': Map<String, dynamic>.from(
                  r,
                ),
            };
          } finally {
            db.close();
          }
        }

        Future<Map<String, dynamic>> measure(
          String name,
          Future<void> Function() operation,
        ) async {
          final pinsBefore =
              pins(); // Independent connection, outside measured work.
          AuditTrace.reset(name);
          final watch = Stopwatch()..start();
          await operation();
          watch.stop();
          final events = AuditTrace.stop();
          final pinsAfter = pins();
          int sum(String k) =>
              events.fold(0, (n, e) => n + (e[k] as int? ?? 0));
          final sql = <String, int>{};
          for (final e in events) {
            if (e['sql'] is String) {
              final statement = e['sql'] as String;
              sql.update(statement, (n) => n + 1, ifAbsent: () => 1);
            }
          }
          final c = <String, dynamic>{
            'name': name,
            'sql': sql.values.fold(0, (a, b) => a + b),
            'sql_frequency': sql,
            'returned_rows': sum('rows_returned'),
            'body_bytes': sum('body_bytes_read'),
            'raw_rows': sum('raw_rows_read'),
            'raw_nodes': sum('raw_objects_read'),
            'index_nodes': sum('index_objects_read'),
            'pin_insert': sum('pin_insert'),
            'pin_delete': sum('pin_delete'),
            'pin_update': sum('pin_update'),
            'pin_events': events
                .where((e) => e.containsKey('pin_parameters'))
                .toList(),
            'pin_owners_before': pinsBefore.values
                .map((r) => r['generation_id'])
                .toSet()
                .toList(),
            'pin_owners_after': pinsAfter.values
                .map((r) => r['generation_id'])
                .toSet()
                .toList(),
            'pins_added': [
              for (final id in pinsAfter.keys.toSet().difference(
                pinsBefore.keys.toSet(),
              ))
                pinsAfter[id],
            ],
            'pins_removed': [
              for (final id in pinsBefore.keys.toSet().difference(
                pinsAfter.keys.toSet(),
              ))
                pinsBefore[id],
            ],
            'transactions': sql['BEGIN IMMEDIATE'] ?? 0,
            'full_verify_calls': events
                .where((e) => e['note'] == 'full_verify')
                .length,
            'frozen_recovery_calls': events
                .where((e) => e['note'] == 'frozen_full_recovery')
                .length,
            'legacy_full_reads': events
                .where((e) => e['note'] == 'legacy_full_read')
                .length,
            'elapsed_us': watch.elapsedMicroseconds,
            'transaction_us': events
                .where((e) => e.containsKey('transaction_us'))
                .map((e) => e['transaction_us'])
                .toList(),
            'objects': events
                .expand((e) => (e['object_identities'] as List? ?? []))
                .toList(),
            'rss_bytes': ProcessInfo.currentRss,
          };
          phases.add(c);
          return c;
        }

        await h.workspace.beginOnlineWrite(1);
        final pending = h.pendingFile.readAsBytesSync();
        final oldB = h.baselineFile.readAsBytesSync();
        await measure('legitimate_first_native', () async {
          await h.state.refreshSegmentedForIsolatedUse(h.store);
        });
        expect(jsonDecode(source.readAsStringSync())['previous_source'], null);
        expect(h.pendingFile.readAsBytesSync(), pending);
        expect(h.baselineFile.readAsBytesSync(), oldB);
        final f = (await h.install()).frozen;
        final baseline = h.baselineFile.readAsBytesSync();
        await measure('valid_previous_source_native_handoff', () async {
          await h.state.refreshSegmentedForIsolatedUse(h.store);
        });
        final repeat = await measure('repeated_native_handoff', () async {
          await h.state.refreshSegmentedForIsolatedUse(h.store);
        });
        // Unlike a Frozen-B-only read, a native refresh also verifies hot/raw
        // correspondence (§25). Assert the exact server-derived H frontier,
        // not the incorrect invented requirement of zero snapshot reads.
        // The observer records EVERY actual object SELECT independently.
        final oracle = await bridge.command({'command': 'oracle'});
        final bodies = <String, Map<String, dynamic>>{
          for (final o in oracle['objects'])
            o['ref']['hash'] as String: jsonDecode(
              utf8.decode(base64Decode(o['data_base64'])),
            ),
        };
        final hot = bodies.values.singleWhere(
          (o) => o['kind'] == 'hot',
        )['state'];
        final hotIds = <String, Set<Object>>{
          'ledger_entries': {
            for (final row in [
              ...hot['entries'],
              ...hot['confirmed_planned_entries'],
            ])
              row['id'],
            for (final row in hot['card_payment_status']['rows'])
              ...row['entry_ids'],
          },
          'monthly_panels': {for (final row in hot['panels']) row['id']},
          'cash_flows': {
            for (final row in hot['cash_flows']) row['id'],
            for (final row in hot['panels'])
              if (row['confirmed_cash_flow_id'] != null)
                row['confirmed_cash_flow_id'],
          },
          'card_payment_events': {
            for (final row in hot['card_payment_status']['events']) row['id'],
          },
        };
        final allowedRaw = {
          for (final e in bodies.entries)
            if (e.value['kind'] == 'snapshot-leaf' &&
                (e.value['rows'] as List).any(
                  (r) =>
                      hotIds[e.value['table']]?.contains(r['value']['id']) ??
                      false,
                ))
              e.key,
        };
        final observedRaw = (repeat['objects'] as List)
            .where(
              (id) => (bodies[id]?['kind'] as String? ?? '').startsWith(
                'snapshot-',
              ),
            )
            .toList();
        final observedIndex = (repeat['objects'] as List)
            .where(
              (id) =>
                  (bodies[id]?['kind'] as String? ?? '').startsWith('index-'),
            )
            .toList();
        // Unchanged raw/index roots need no descendant traversal. Raw leaves
        // may be touched ONLY for the actual bounded hot rows, once per leaf.
        expect(observedRaw.toSet().difference(allowedRaw), isEmpty);
        expect(observedRaw.length, observedRaw.toSet().length);
        expect(repeat['raw_nodes'], observedRaw.length);
        expect(
          repeat['raw_rows'],
          observedRaw.fold<int>(
            0,
            (n, id) => n + (bodies[id]!['rows'] as List).length,
          ),
        );
        final indexRoot = oracle['manifest']['target']['index_ref']['hash'];
        // Existing PatriciaEdit.finish reads the root's facts HEAD count.
        // It does not traverse that head's left/right descendants on no-op.
        final allowedIndex = {indexRoot, bodies[indexRoot]!['facts']['hash']};
        const costOutput = String.fromEnvironment('AUDIT_E4_COST');
        File('$costOutput.frontier-$size.json').writeAsStringSync(
          jsonEncode({
            'history': size,
            'repeat': repeat,
            'allowed_hot_raw_leaves': allowedRaw.toList(),
            'allowed_index_root_and_head': allowedIndex.toList(),
            'observed_index': [
              for (final id in observedIndex)
                {
                  'hash': id,
                  'kind': bodies[id]?['kind'],
                  'facts': bodies[id]?['facts'],
                },
            ],
          }),
        );
        expect(observedIndex.toSet().difference(allowedIndex), isEmpty);
        expect(observedIndex.length, observedIndex.toSet().length);
        expect(repeat['index_nodes'], observedIndex.length);
        repeat['allowed_hot_raw_leaves'] = allowedRaw.toList();
        // §24/§25 require root metadata for a newly accepted local generation.
        // Compare EVERY actual row write/owner with before/after sets. E3 also
        // creates one temporary candidate's four root relations and discards
        // that candidate on idempotent publication. This is bounded metadata,
        // NOT rewriting the unchanged accepted/Frozen pin set.
        final added = repeat['pins_added'] as List,
            removed = repeat['pins_removed'] as List;
        expect(repeat['pin_update'], 0);
        final rootHashes = {
          for (final role in ['control', 'hot', 'raw', 'index'])
            oracle['manifest']['target']['${role}_ref']['hash'],
        };
        final newOwners = added.map((r) => r['generation_id']).toSet();
        final pinEvents = repeat['pin_events'] as List;
        final inserted = pinEvents
            .where((e) => e['pin_insert'] != null)
            .toList();
        final deleted = pinEvents
            .where((e) => e['pin_delete'] != null)
            .toList();
        final beforeOwners = (repeat['pin_owners_before'] as List).toSet(),
            afterOwners = (repeat['pin_owners_after'] as List).toSet();
        final temporaryOwners = inserted
            .map((e) => e['pin_parameters'][0])
            .toSet()
            .difference(afterOwners);
        expect(temporaryOwners.intersection(beforeOwners), isEmpty);
        // Exactly one local candidate is prepared by one native request.
        expect(inserted.map((e) => e['pin_parameters'][0]).toSet().length, 1);
        for (final e in inserted) {
          expect(beforeOwners.contains(e['pin_parameters'][0]), false);
          expect(rootHashes.contains(e['pin_parameters'][1]), true);
          expect(e['pin_insert'], 1);
        }
        for (final owner in temporaryOwners) {
          expect(
            inserted
                .where((e) => e['pin_parameters'][0] == owner)
                .map((e) => e['pin_parameters'][1])
                .toSet(),
            rootHashes,
          );
          final deletion = deleted.singleWhere(
            (e) => e['pin_parameters'][0] == owner,
          );
          expect(deletion['pin_delete'], rootHashes.length);
        }
        expect(
          repeat['pin_insert'],
          added.length + temporaryOwners.length * rootHashes.length,
        );
        expect(
          repeat['pin_delete'],
          removed.length + temporaryOwners.length * rootHashes.length,
        );
        repeat['temporary_candidate_owners'] = temporaryOwners.toList();
        expect(
          newOwners.difference({h.store.acceptedGeneration().id}),
          isEmpty,
        );
        expect(added.length, newOwners.length * rootHashes.length);
        expect(added.every((r) => rootHashes.contains(r['hash'])), true);
        expect(removed.any((r) => r['generation_id'] == f.generationId), false);
        for (final key in [
          'full_verify_calls',
          'frozen_recovery_calls',
          'legacy_full_reads',
        ]) {
          expect(repeat[key], 0, reason: key);
        }
        final s = jsonDecode(source.readAsStringSync()) as Map<String, dynamic>;
        await bridge.command({'command': 'mutate'});
        await h.state.publishSegmentedForIsolatedUse(h.store);
        h.workspace.prepareSegmentedSource(
          h.store,
          h.store.acceptedGeneration(),
          () {},
        );
        final invalid =
            jsonDecode(source.readAsStringSync()) as Map<String, dynamic>;
        invalid['previous_source'] = null;
        source.writeAsStringSync(jsonEncode(invalid), flush: true);
        final rejectedBytes = source.readAsBytesSync();
        final installed = h.store.installedGeneration()!;
        final reject = await measure(
          'missing_previous_source_rejection',
          () async {
            await expectLater(
              h.state.refreshSegmentedForIsolatedUse(h.store),
              throwsA(
                isA<SegmentedException>().having(
                  (e) => e.code,
                  'code',
                  'SOURCE_PROVENANCE_REQUIRED',
                ),
              ),
            );
          },
        );
        expect(reject['full_verify_calls'], 0);
        expect(reject['frozen_recovery_calls'], 0);
        expect(reject['pin_insert'], 0);
        expect(reject['pin_delete'], 0);
        expect(source.readAsBytesSync(), rejectedBytes);
        expect(h.store.installedGeneration()!.id, installed.id);
        expect(h.pendingFile.readAsBytesSync(), pending);
        expect(h.baselineFile.readAsBytesSync(), baseline);
        // Test-only restoration of the exact known valid predecessor. Product
        // recovery never guesses it. A fresh store must validate the full proof.
        source.writeAsStringSync(jsonEncode(s), flush: true);
        h.reopen();
        final fresh = E4Workspace(h.root);
        await measure('fresh_store_recovery', () async {
          await fresh.recoverLegacyHandoff(h.store);
          await fresh.readFrozenBaseline(h.store, f.id, 1);
        });
        final d = sqlite3.open(h.store.path);
        try {
          expect(d.select('PRAGMA foreign_key_check'), isEmpty);
          final frozen = d.select('SELECT * FROM frozen').single;
          expect(frozen['id'], f.id);
          expect(
            d.select(
              'SELECT count(*) AS n FROM generation_roots '
              'WHERE generation_id=?',
              [f.generationId],
            ).single['n'],
            4,
          );
        } finally {
          d.close();
        }
        expect(h.pendingFile.readAsBytesSync(), pending);
        expect(h.baselineFile.readAsBytesSync(), baseline);
        results.add({
          'history': size,
          'phases': phases,
          'frozen_preserved': true,
          'baseline_preserved': true,
          'pending_preserved': true,
        });
      } finally {
        h.dispose();
        await bridge.dispose();
      }
    });
  }
}
