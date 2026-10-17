@Timeout(Duration(minutes: 30))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';

import 'harness.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late RealBackend backend;
  final evidence = <Map<String, dynamic>>[];
  setUpAll(() async => backend = await RealBackend.start(5));
  setUp(() async => backend.command({'command': 'advance', 'seconds': 901}));
  tearDownAll(() async {
    File(const String.fromEnvironment('CONTINUATION_OUTPUT'))
        .writeAsStringSync(jsonEncode(evidence));
    await backend.dispose();
  });
  Future<Object?> result(Future<dynamic> f) =>
      f.then<Object?>((_) => null, onError: (Object e) => e);
  void untouched(Map<String, dynamic> before, Map<String, dynamic> after) {
    for (final k in ['source', 'B', 'pending', 'installed', 'frozen']) {
      expect(after[k], before[k], reason: k);
    }
  }

  for (final fault in [
    'dataset',
    'canon',
    'base_echo',
    'context',
    'ref_size',
    'base64',
    'chunk_length',
    'duplicate_chunk',
    'content_type',
    'unexpected_status',
    'missing_descendant',
  ]) {
    test(
      'C-N-$fault real handler response mutation preserves installed Frozen B',
      () async {
        final h = await RealHarness.create(backend);
        try {
          final f = await h.state.installSegmentedLegacyForIsolatedUse(h.store);
          final originalBaseline = await h.workspace.readFrozenBaseline(
            h.store,
            f.frozen.id,
            1,
          );
          await h.workspace.beginOnlineWrite(1);
          await backend.command({
            'command': 'mutate',
            'title': '새 negative $fault',
          });
          final before = h.disk();
          await backend.command({
            'command': 'fault',
            'mode': fault,
            'path':
                [
                  'base64',
                  'chunk_length',
                  'duplicate_chunk',
                  'content_type',
                  'unexpected_status',
                  'missing_descendant',
                ].contains(fault)
                ? '/objects'
                : '/observations',
          });
          final error = await result(
            h.state.refreshSegmentedForIsolatedUse(h.store),
          );
          if (error == null) {
            final frozenRead = await h.workspace.readFrozenBaseline(
              h.store,
              f.frozen.id,
              1,
            );
            File(
              const String.fromEnvironment('CONTINUATION_OUTPUT') +
                  '.diagnostic-' +
                  fault,
            ).writeAsStringSync(
              jsonEncode({
                'id': 'C-N-$fault',
                'expected': 'rejection diagnostic; binding applicability assessed separately',
                'error': null,
                'before': before,
                'after': h.disk(),
                'frozen_fingerprint': frozenRead.serverStateFingerprint,
                'wire': await backend.stats(),
              }),
            );
          }
          expect(error, isNotNull);
          expect(h.disk(), before);
          final b = await h.workspace.readFrozenBaseline(
            h.store,
            f.frozen.id,
            1,
          );
          expect(
            b.serverStateFingerprint,
            originalBaseline.serverStateFingerprint,
          );
          // 같은 실제 HTTP client의 후속 정상 취득. Unknown pending은 유지한다.
          await backend.command({'command': 'advance', 'seconds': 901});
          await h.state.refreshSegmentedForIsolatedUse(h.store);
          expect(h.disk()['pending'], before['pending']);
          final fresh = await h.freshRead(f.frozen.id);
          evidence.add({
            'id': 'C-N-$fault',
            'error': '$error',
            'before': before,
            'after_valid_recovery': h.disk(),
            'fresh': fresh,
            'wire': await backend.stats(),
          });
        } finally {
          h.dispose();
        }
      },
    );
  }
  for (final change in [
    'same_user_reauth',
    'different_user',
    'mutation',
    'newer_segmented',
    'offline',
    'token',
    'logout',
  ]) {
    test(
      'C-A-$change after real D3a before D3b preserves original authority',
      () async {
        final h = await RealHarness.create(backend, maxConnections: 2);
        try {
          final before = h.disk();
          await backend.command({'command': 'pause', 'path': '/observations'});
          final old = result(h.state.refreshSegmentedForIsolatedUse(h.store));
          await backend.waitEntered();
          Future<dynamic>? changing;
          if (change == 'same_user_reauth' || change == 'logout') {
            changing = h.state.logout();
          } else if (change == 'different_user') {
            h.state.user = AuthUser(
              id: 2,
              username: 'other',
              displayName: 'other',
              sharePinNeedsChange: false,
            );
          } else if (change == 'mutation') {
            changing = h.state.createCashFlow(
              occurredOn: '2026-10-05',
              title: 'synthetic pending',
              amount: 1,
              isIncome: false,
              isPrimaryIncome: false,
            );
            final limit = Stopwatch()..start();
            while (!h.pending.existsSync() &&
                limit.elapsed < const Duration(seconds: 10)) {
              await Future<void>.delayed(const Duration(milliseconds: 1));
            }
            expect(h.pending.existsSync(), isTrue);
            await Future<void>.delayed(Duration.zero);
          } else if (change == 'newer_segmented') {
            changing = h.state.refreshSegmentedForIsolatedUse(h.store);
          } else if (change == 'offline') {
            h.state.connectivityMode = ConnectivityMode.offline;
          } else {
            await h.api.saveSession('${backend.token}-changed');
          }
          // authority 전환을 시작한 뒤 응답을 해제한다. 소켓 timeout을 race oracle로 쓰지 않는다.
          await backend.command({'command': 'release'});
          if (changing != null) {
            final changeError = await result(changing);
            if (change == 'newer_segmented') {
              expect(
                changeError,
                isA<AcquisitionFailure>()
                    .having((e) => e.code, 'code', 'ACQUISITION_BUSY')
                    .having((e) => e.action, 'action', 'retry_same'),
              );
              expect(await old, isNotNull);
              expect(
                (h.disk()['accepted'] as List).single['current_id'],
                isNull,
              );
              // E2는 같은 isolate/store의 acquisition 하나만 허용한다.
              // 새 원 ticket의 fresh 취득만 retry하며 오래된 후보에 ticket을 붙이지 않는다.
              await h.state.refreshSegmentedForIsolatedUse(h.store);
              expect(
                (h.disk()['accepted'] as List).single['current_id'],
                isNotNull,
              );
            }
          }
          if (change == 'same_user_reauth') {
            await h.api.saveSession(backend.token);
            h.state.user = baselineFixture().user;
          }
          final afterNewer = h.disk();
          await backend.command({'command': 'release'});
          expect(await old, isNotNull);
          expect(h.disk(), afterNewer);
          if (change != 'newer_segmented') {
            final accepted = (h.disk()['accepted'] as List).single;
            expect(accepted['current_id'], isNull);
            expect(accepted['sequence'], 0);
            if (change != 'mutation') untouched(before, h.disk());
          }
          evidence.add({
            'id': 'C-A-$change',
            'before': before,
            'after_newer_action': afterNewer,
            'after_old': h.disk(),
            'wire': await backend.stats(),
          });
        } finally {
          await backend.command({'command': 'release'});
          h.dispose();
        }
      },
    );
  }
  for (final stage in ['after_e3_acceptance', 'after_legacy_materialization']) {
    for (final change in ['mutation', 'offline', 'token']) {
      test(
        'C-I-$stage-$change authority changes before guarded legacy handoff',
        () async {
          var armed = false;
          late RealHarness h;
          h = await RealHarness.create(
            backend,
            fault: (point) {
              if (armed && point == stage) {
                armed = false;
                if (change == 'offline')
                  h.state.connectivityMode = ConnectivityMode.offline;
                if (change == 'token')
                  unawaited(h.api.saveSession('${backend.token}-changed'));
                if (change == 'mutation')
                  unawaited(
                    h.state.createCashFlow(
                      occurredOn: '2026-10-05',
                      title: 'during materialization',
                      amount: 1,
                      isIncome: false,
                      isPrimaryIncome: false,
                    ),
                  );
              }
            },
          );
          try {
            final f = await h.state.installSegmentedLegacyForIsolatedUse(
              h.store,
            );
            final before = h.disk();
            armed = true;
            final error = await result(
              h.state.installSegmentedLegacyForIsolatedUse(h.store),
            );
            expect(error, isNotNull);
            final after = h.disk();
            for (final k in ['source', 'B', 'frozen', 'installed'])
              expect(after[k], before[k], reason: k);
            final fresh = await h.freshRead(f.frozen.id);
            evidence.add({
              'id': 'C-I-$stage-$change',
              'error': '$error',
              'before': before,
              'after': after,
              'fresh': fresh,
            });
          } finally {
            h.dispose();
          }
        },
      );
    }
  }
}
