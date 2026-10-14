@Timeout(Duration(minutes: 3))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

// Diagnostic assertions document a BLOCKED boundary. PASS here is NOT an E4
// implementation PASS: the original legacy rejection is the expected finding.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, dynamic> evidence;
  late GenerationFixture fixture;
  setUpAll(() async {
    final root = Directory.current.parent.path;
    final result = await Process.run('$root/.venv/bin/python', [
      '$root/docs/benchmarks/t66e4-contract/probe.py',
    ]);
    expect(result.exitCode, 0, reason: result.stderr as String);
    evidence = jsonDecode(result.stdout as String) as Map<String, dynamic>;
    fixture = GenerationFixture(evidence['fixture']);
  });

  test(
    'backend complete Snapshot and coherent bundle preserve the raw string',
    () {
      final wire = evidence['wire'] as Map;
      const text = '\u001c+0001000.00\u001f';
      expect(wire['state']['settings']['cash_flow_balance'], text);
      expect(
        (wire['snapshot']['data']['app_settings'] as List).singleWhere(
          (r) => r['key'] == 'cash_flow_balance',
        )['value'],
        text,
      );
      expect(
        wire['authority']['state_fingerprint'],
        isNot(fixture.target.syncRoot),
      );
    },
  );

  test(
    'backend-derived monetary differential identifies the legacy boundary',
    () {
      var disagreement = 0;
      for (final raw in evidence['vectors']) {
        final row = raw as Map;
        var dartAccepted = true;
        try {
          exactMoney(row['value']);
        } on FormatException {
          dartAccepted = false;
        }
        expect(row['segmented'], row['legacy_server']);
        final text = row['value'] as String;
        final pythonOnlyWhitespace = text.runes.any(
          (c) => c >= 0x1c && c <= 0x1f,
        );
        final edgeBom = text.startsWith('\ufeff') || text.endsWith('\ufeff');
        expect(
          dartAccepted,
          edgeBom || (row['segmented'] == true && !pythonOnlyWhitespace),
          reason: text.runes.map((c) => c.toRadixString(16)).join(' '),
        );
        if (dartAccepted != row['segmented']) disagreement++;
      }
      // Four Python-only whitespace characters, the combined input, and two
      // edge-BOM cases. Middle BOM is rejected by both implementations.
      expect(disagreement, 7);
    },
  );

  test(
    'existing E1/E2/E3 accepts the complete server graph and persists bytes',
    () async {
      final root = Directory.systemTemp.createTempSync('e4-contract-');
      SegmentedClientStore? store;
      try {
        store = SegmentedClientStore.open(
          root,
          fixture.cache,
          publication: true,
        );
        final base = await store.recoverAcceptedGeneration();
        final acquired = await IncrementalFetcher(
          store,
          FixtureTransport(fixture),
        ).acquire();
        final version = store.publicationDataVersion;
        final proof = await store.verifyPublicationCandidate(
          acquired.manifest,
          base,
          verifiedDataVersion: version,
        );
        final prepared = store.prepareGeneration(
          syncUuid(),
          acquired.stagingId,
          proof,
          base,
          verifiedDataVersion: version,
        );
        // Storage-only synthetic data evidence, not AppState installation authority.
        store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
        final db = sqlite3.open(store.path);
        try {
          expect(
            db.select('SELECT sequence FROM accepted').single['sequence'],
            1,
          );
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
          final bodies = db.select(
            "SELECT body FROM objects WHERE kind='snapshot-leaf'",
          );
          final settings = bodies
              .map((r) => decodeC1(r['body'] as List<int>) as Map)
              .where((r) => r['table'] == 'app_settings')
              .expand((r) => r['rows'] as List)
              .singleWhere((r) => r['value']['key'] == 'cash_flow_balance');
          expect(settings['value']['value'], '\u001c+0001000.00\u001f');
        } finally {
          db.close();
        }
        store.close();
        store = SegmentedClientStore.open(
          root,
          fixture.cache,
          publication: true,
        );
        expect((await store.recoverAcceptedGeneration()).sequence, 1);
      } finally {
        store?.close();
        root.deleteSync(recursive: true);
      }
    },
  );

  test(
    'CURRENT full bundle admission rejects the server-approved original',
    () {
      expect(
        () => AuthoritativeBundle.decode(
          utf8.encode(jsonEncode(evidence['wire'])),
        ),
        throwsA(
          isA<FormatException>().having(
            (e) => e.message,
            'message',
            'money must be an exact safe integer',
          ),
        ),
      );
    },
  );

  test(
    'CURRENT OfflineBaseline v4 parser rejects the same complete Snapshot',
    () {
      final wire = evidence['wire'] as Map;
      final baseline = <String, dynamic>{
        ...wire['state'] as Map<String, dynamic>,
        'schema_version': 4,
        'synced_at': wire['snapshot']['exported_at'],
        'user': baselineFixture().toJson()['user'],
        'authoritative_snapshot': wire['snapshot'],
        'server_state_fingerprint': wire['authority']['state_fingerprint'],
        'resolved_reconciliation_id': null,
        'discount_policy_defaults':
            wire['authority']['discount_policy_defaults'],
      };
      expect(
        () => OfflineBaseline.fromJson(baseline),
        throwsA(
          isA<FormatException>().having(
            (e) => e.message,
            'message',
            'money must be an exact safe integer',
          ),
        ),
      );
    },
  );
}
