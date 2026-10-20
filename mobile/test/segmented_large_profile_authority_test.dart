@Timeout(Duration(minutes: 4))
library;

import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/offline_mode_fixtures.dart';
import 'support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final scenario in ['valid', 'session', 'cancel', 'mode', 'budget']) {
    test(
        'B02 isolated profile keeps original final authority and prior state: $scenario',
        () async {
      FlutterSecureStorage.setMockInitialValues({});
      final bridge = await BackendBridge.start();
      final root = Directory.systemTemp.createTempSync('mn-b02-authority-');
      final api = MoneyNoteApiClient(client: bridge, baseUrl: syntheticOrigin);
      await api.saveSession(bridge.token);
      final legacy = OfflineStore(directoryProvider: () async => root);
      await legacy.replaceBaseline(baselineFixture());
      await legacy.beginOnlineWrite(1);
      final files = {
        for (final f in Directory('${root.path}/offline-mode')
            .listSync()
            .whereType<File>())
          f.path: f.readAsBytesSync()
      };
      final state = AppState(api, offlineStore: legacy)
        ..user = baselineFixture().user;
      var armed = false;
      Future<void>? sessionChange;
      final cancel = SyncCancellation();
      final store = SegmentedClientStore.open(
          root, GenerationFixture(bridge.fixture).cache,
          publication: true,
          limits: largeVerificationStoreLimits, fault: (point) {
        if (!armed || point != 'before_publication_commit') return;
        armed = false;
        if (scenario == 'session') {
          sessionChange = api.saveSession('synthetic-replacement');
        }
        if (scenario == 'cancel') cancel.cancel();
        if (scenario == 'mode') {
          state.connectivityMode = ConnectivityMode.offline;
        }
      });
      try {
        final first = await state.publishSegmentedForIsolatedUse(store,
            verificationLimits: largeVerificationFetchLimits);
        final before = store.acceptedGeneration();
        final workBefore = store.work.snapshot();
        final pinsBeforeDb = sqlite3.open(store.path);
        final pinsBefore = pinsBeforeDb
            .select('SELECT * FROM generation_roots ORDER BY 1,2')
            .map((r) => Map<String, dynamic>.from(r))
            .toList();
        pinsBeforeDb.close();
        armed = true;
        final next = state.publishSegmentedForIsolatedUse(store,
            cancellation: cancel,
            verificationLimits: scenario == 'budget'
                ? const FetchLimits.largeGraphVerification(graphObjects: 1)
                : largeVerificationFetchLimits);
        if (scenario == 'valid') {
          final second = await next;
          expect(second.idempotent, isTrue);
          expect(second.sequence, first.sequence);
          expect(second.generationId, first.generationId);
          final work = store.work.since(workBefore);
          for (final key in [
            'full_recoveries',
            'full_verifications',
            'full_raw_rows'
          ]) {
            expect(work[key] ?? 0, 0, reason: key);
          }
          // Preparing/discarding an idempotent candidate may touch its four
          // root metadata pins; it must never rewrite the retained graph.
          final rootCount = before.manifest!.target.roots.length;
          expect(work['pin_inserts'] ?? 0, lessThanOrEqualTo(rootCount));
          expect(work['pin_deletes'] ?? 0, lessThanOrEqualTo(rootCount));
          final pinsAfterDb = sqlite3.open(store.path);
          expect(
              pinsAfterDb
                  .select('SELECT * FROM generation_roots ORDER BY 1,2')
                  .map((r) => Map<String, dynamic>.from(r))
                  .toList(),
              pinsBefore);
          pinsAfterDb.close();
        } else {
          await expectLater(
              next,
              throwsA(anyOf(isA<MoneyNoteApiException>(),
                  isA<SegmentedException>(), isA<AcquisitionFailure>())));
          final after = store.acceptedGeneration();
          expect(after.id, before.id);
          expect(after.sequence, before.sequence);
        }
        await sessionChange;
        final db = sqlite3.open(store.path);
        try {
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
          expect(
              db
                  .select('SELECT count(*) AS n FROM generation_roots')
                  .single['n'],
              greaterThanOrEqualTo(4));
          expect(
              db.select('SELECT current_id FROM accepted').single['current_id'],
              store.acceptedGeneration().id);
        } finally {
          db.close();
        }
        for (final e in files.entries) {
          expect(File(e.key).readAsBytesSync(), e.value);
        }
        expect(await legacy.loadPendingOnlineWrite(1), isNotNull);
      } finally {
        store.close();
        state.dispose();
        await bridge.dispose();
        root.deleteSync(recursive: true);
      }
    });
  }
}
