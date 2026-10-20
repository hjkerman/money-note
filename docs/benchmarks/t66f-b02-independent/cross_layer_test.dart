@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../../../mobile/test/support/segmented_large_transport.dart';
import '../t66f-b02-implementation/verification_profile.dart';

List<Map<String, dynamic>> sql(SegmentedClientStore store, String query) {
  final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
  try {
    return db.select(query).map((r) => Map<String, dynamic>.from(r)).toList();
  } finally {
    db.close();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final mode in [
    'cancel',
    'logout',
    'session',
    'different_user',
    'supersede',
    'commit_cancel',
    'commit_session',
    'commit_mode',
  ]) {
    test(
      'independent real D-to-E prior accepted and original ticket: $mode',
      () async {
        // 감사 test가 package 밖 docs에 있으므로 analyzer의 경로 판정을 명시한다.
        // ignore: invalid_use_of_visible_for_testing_member
        FlutterSecureStorage.setMockInitialValues({});
        final bridge = await BackendBridge.start(history: 12),
            root = Directory.systemTemp.createTempSync(
              'mn-b02-audit-authority-',
            );
        final api = MoneyNoteApiClient(
          client: bridge,
          baseUrl: syntheticOrigin,
        );
        await api.saveSession(bridge.token);
        final legacy = OfflineStore(directoryProvider: () async => root);
        await legacy.replaceBaseline(baselineFixture());
        await legacy.beginOnlineWrite(1);
        final originalFiles = {
          for (final f in Directory(
            '${root.path}/offline-mode',
          ).listSync().whereType<File>())
            f.path: f.readAsBytesSync(),
        };
        final state = AppState(api, offlineStore: legacy)
          ..user = baselineFixture().user;
        final cancel = SyncCancellation();
        var armed = false, triggered = false;
        Future<void>? tokenChange;
        Object? supersedeError;
        final store = SegmentedClientStore.open(
          root,
          GenerationFixture(bridge.fixture).cache,
          publication: true,
          limits: largeVerificationStoreLimits,
          fault: (point) {
            if (!armed ||
                !mode.startsWith('commit_') ||
                point != 'before_publication_commit')
              return;
            armed = false;
            triggered = true;
            if (mode == 'commit_cancel') cancel.cancel();
            if (mode == 'commit_session')
              tokenChange = api.saveSession('independent-replacement');
            if (mode == 'commit_mode')
              state.connectivityMode = ConnectivityMode.offline;
          },
        );
        try {
          await state.publishSegmentedForIsolatedUse(
            store,
            verificationLimits: largeVerificationFetchLimits,
          );
          final before = store.acceptedGeneration(),
              acceptedSql = sql(store, 'SELECT * FROM accepted'),
              pins = sql(store, 'SELECT * FROM generation_roots ORDER BY 1,2');
          await bridge.command({'command': 'mutate'});
          armed = true;
          bridge.before = (path) async {
            if (!armed ||
                mode.startsWith('commit_') ||
                !path.endsWith('/objects'))
              return;
            armed = false;
            triggered = true;
            if (mode == 'cancel') cancel.cancel();
            if (mode == 'logout') await state.logout();
            if (mode == 'session')
              await api.saveSession('independent-replacement');
            if (mode == 'different_user')
              state.user = AuthUser(
                id: 2,
                username: 'synthetic-other',
                displayName: '다른 합성 사용자',
                sharePinNeedsChange: false,
              );
            if (mode == 'supersede') {
              try {
                await state.publishSegmentedForIsolatedUse(
                  store,
                  verificationLimits: largeVerificationFetchLimits,
                );
              } catch (e) {
                supersedeError = e;
              }
            }
          };
          await expectLater(
            state.publishSegmentedForIsolatedUse(
              store,
              cancellation: cancel,
              verificationLimits: largeVerificationFetchLimits,
            ),
            throwsA(
              anyOf(
                isA<MoneyNoteApiException>(),
                isA<SegmentedException>(),
                isA<AcquisitionFailure>(),
              ),
            ),
          );
          await tokenChange;
          expect(triggered, true);
          if (mode == 'supersede')
            expect(
              supersedeError,
              isA<AcquisitionFailure>().having(
                (e) => e.code,
                'code',
                'ACQUISITION_BUSY',
              ),
            );
          expect(store.acceptedGeneration().id, before.id);
          expect(sql(store, 'SELECT * FROM accepted'), acceptedSql);
          expect(
            sql(store, 'SELECT * FROM generation_roots ORDER BY 1,2'),
            pins,
          );
          expect(sql(store, 'PRAGMA foreign_key_check'), isEmpty);
          for (final e in originalFiles.entries)
            expect(File(e.key).readAsBytesSync(), e.value);
          expect(await legacy.loadPendingOnlineWrite(1), isNotNull);
          // A new store connection must recover the prior accepted graph, never a partial candidate.
          store.close();
          final reopened = SegmentedClientStore.open(
            root,
            GenerationFixture(bridge.fixture).cache,
            publication: true,
            limits: largeVerificationStoreLimits,
          );
          try {
            expect((await reopened.recoverAcceptedGeneration()).id, before.id);
            expect(reopened.inspectStoreHealth().healthy, true);
          } finally {
            reopened.close();
          }
        } finally {
          store.close();
          state.dispose();
          await bridge.dispose();
          root.deleteSync(recursive: true);
        }
      },
    );
  }
  test('independent exact backend monetary string through E2 E3 E4', () async {
    final result = await Process.run('../.venv/bin/python', [
      'test/support/e4_backend_oracle.py',
    ]);
    expect(result.exitCode, 0, reason: result.stderr as String);
    final oracle = jsonDecode(result.stdout as String) as Map<String, dynamic>,
        fixture = GenerationFixture(oracle['fixture']);
    final root = Directory.systemTemp.createTempSync('mn-b02-audit-money-'),
        store = SegmentedClientStore.open(
          root,
          fixture.cache,
          publication: true,
          limits: largeVerificationStoreLimits,
        );
    try {
      final base = await store.recoverAcceptedGeneration(),
          got = await IncrementalFetcher(
            store,
            BatchFixtureTransport(fixture),
            limits: largeVerificationFetchLimits,
          ).acquire(verifiedBase: base);
      final version = store.publicationDataVersion,
          proof = await store.verifyPublicationCandidate(
            got.manifest,
            base,
            verifiedDataVersion: version,
          );
      final prepared = store.prepareGeneration(
        syncUuid(),
        got.stagingId,
        proof,
        base,
        verifiedDataVersion: version,
      );
      store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
      final accepted = store.acceptedGeneration();
      final view = store.withAcceptedRead(
        accepted,
        (r) => readSegmentedAuthority(r, baselineFixture().user),
      );
      expect(
        view.candidate.settings.values['cash_flow_balance'],
        '\u001c+0001000.00\u001f',
      );
      expect(
        store.withAcceptedRead(accepted, (r) => r.hot['state']),
        oracle['wire']['state'],
      );
      for (final table in fixture.source.keys) {
        final expected = (fixture.source[table] as List).cast<Map>();
        final actual = store.withAcceptedRead(accepted, (r) => r.rows(table));
        expect(actual, unorderedEquals(expected), reason: table);
      }
    } finally {
      store.close();
      root.deleteSync(recursive: true);
    }
  });
}
