import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('durable offline store', () {
    test('unresolved registration key must not bind an unrelated new draft',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final first = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '첫 번째 생활비',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final other = <String, dynamic>{
        ...first,
        'title': '별개 지출',
        'amount_value': 700
      };
      expect(
          await store.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-first'),
          'manual-panel-first');
      final restarted = offlineStoreFixture(directory);
      await expectLater(
          restarted.reserveManualPanelRetryKey(other,
              preferredKey: 'manual-panel-other'),
          throwsA(isA<OfflinePersistenceException>()));
      expect((await restarted.loadPendingManualPanelRetry())!.key,
          'manual-panel-first');
      expect((await restarted.loadPendingManualPanelRetry())!.input, first);
    });

    test('unknown manual panel result keeps one identity across edited drafts',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final first = {
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '생활비',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final changed = {...first, 'amount_value': 700};
      final firstKey = await store.reserveManualPanelRetryKey(first,
          preferredKey: 'manual-panel-original');
      final restarted = offlineStoreFixture(directory);
      await expectLater(
          restarted.reserveManualPanelRetryKey(changed,
              preferredKey: 'manual-panel-new'),
          throwsA(isA<OfflinePersistenceException>()));
      expect(
          await restarted.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-other-process'),
          firstKey);
      expect(await restarted.reserveManualPanelRetryKey(first), firstKey);
      await expectLater(
          restarted.completeManualPanelRetryKey(changed, firstKey),
          throwsA(isA<OfflinePersistenceException>()));
      await restarted.completeManualPanelRetryKey(first, firstKey);
      expect(
          await restarted.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-fresh'),
          'manual-panel-fresh');
    });

    test('manual retry cleanup failure retains original input and key',
        () async {
      final directory = await temporaryDirectoryFixture();
      final failingStore = OfflineStore(
        directoryProvider: () async => directory,
        beforeManualRetryCleanup: () async =>
            throw StateError('cleanup failed'),
      );
      final input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'family_card',
        'title': '이전 가족카드',
        'spent_on': '2026-09-17',
        'amount_value': 10000,
        'discount_enabled': false,
      };
      final key = await failingStore.reserveManualPanelRetryKey(input,
          preferredKey: 'manual-panel-cleanup');
      await expectLater(failingStore.completeManualPanelRetryKey(input, key),
          throwsA(isA<StateError>()));
      final restarted = offlineStoreFixture(directory);
      expect((await restarted.loadPendingManualPanelRetry())!.input, input);
      expect(await restarted.hasPendingManualPanelRetry(), isTrue);
      await restarted.completeManualPanelRetryKey(input, key);
      expect(await restarted.hasPendingManualPanelRetry(), isFalse);
      expect(
          await restarted.reserveManualPanelRetryKey(
              {...input, 'title': '새 가족카드'},
              preferredKey: 'manual-panel-new'),
          'manual-panel-new');
    });
    test('legacy digest-only manual retry accepts exact input but not edits',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '이전 형식',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': true,
      };
      const key = 'manual-panel-legacy';
      await store.reserveManualPanelRetryKey(input, preferredKey: key);
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      final v2 = jsonDecode(await retryFile.readAsString()) as Map;
      await retryFile.writeAsString(jsonEncode({
        'schema_version': 1,
        'keys': {v2['input_digest']: key},
      }));
      final restarted = offlineStoreFixture(directory);
      expect((await restarted.loadPendingManualPanelRetry())!.input, isNull);
      expect(await restarted.reserveManualPanelRetryKey(input), key);
      await expectLater(
          restarted.reserveManualPanelRetryKey({...input, 'amount_value': 700}),
          throwsA(isA<OfflinePersistenceException>()));
      await restarted.completeManualPanelRetryKey(input, key);
      expect(await restarted.hasPendingManualPanelRetry(), isFalse);
    });
    test('baseline is atomically replaced and survives a new store instance',
        () async {
      final directory = await temporaryDirectoryFixture();
      final firstStore = offlineStoreFixture(directory);
      await firstStore.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      expect(
          (await firstStore.loadBaseline())!.summary.remainingLiquidity, 10000);

      await firstStore.replaceBaseline(baselineFixture(remainingLiquidity: 9000));
      final restartedStore = offlineStoreFixture(directory);
      final restored = await restartedStore.loadBaseline();

      expect(restored!.summary.remainingLiquidity, 9000);
      expect(restored.syncedAt, DateTime.utc(2026, 9, 17, 3, 14));
      expect(restored.user.sessionToken, isNull);
      expect(
        restored.ownerDiscountMonth.projectionPolicy!.rate,
        '0.012',
      );
      expect(
        directory
            .listSync(recursive: true)
            .whereType<File>()
            .where((file) => file.path.endsWith('.tmp')),
        isEmpty,
      );
    });

    test('journal is append-only, ordered, durable, and rejects derived values',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(
        directory,
        clock: () => DateTime.utc(2026, 9, 17, 4),
      );

      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      await store.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: const {
          'entry_date': '2026-09-01',
          'usage_place': '가게',
          'amount_value': 100,
        },
      );

      final restored = await offlineStoreFixture(directory).loadJournal();
      expect(restored.map((operation) => operation.sequence), [1, 2]);
      expect(restored.map((operation) => operation.operationId).toSet(),
          hasLength(2));
      expect(
          restored.every((operation) => operation.status == 'pending'), isTrue);
      await expectLater(
        store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: const {'remaining_liquidity': 1},
        ),
        throwsArgumentError,
      );

      final journal = File('${directory.path}/offline-mode/journal.ndjson');
      await journal.writeAsString(
        'interrupted-json-row',
        mode: FileMode.append,
        flush: true,
      );
      await offlineStoreFixture(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-02',
          'title': '재시작 후 입금',
          'amount_value': 200,
          'is_primary_income': 0,
        },
      );
      expect(await offlineStoreFixture(directory).loadJournal(), hasLength(3));

      final rows = const LineSplitter()
          .convert(await journal.readAsString())
          .map((line) => jsonDecode(line) as Map<String, dynamic>);
      expect(
        rows.every((row) {
          final payload = row['payload'] as Map<String, dynamic>;
          return !payload.containsKey('remaining_liquidity') &&
              !payload.containsKey('effective_amount_value');
        }),
        isTrue,
      );
    });
    test('valid EOF record remains durable when the next record is appended',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      for (final amount in [-500, -700]) {
        await store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: {
            'occurred_on': '2026-09-17',
            'title': '현금',
            'amount_value': amount,
            'is_primary_income': 0,
          },
        );
      }
      final journal = File('${directory.path}/offline-mode/journal.ndjson');
      final bytes = await journal.readAsBytes();
      expect(bytes.last, 0x0a);
      await journal.writeAsBytes(bytes.sublist(0, bytes.length - 1),
          flush: true);

      expect(
        (await offlineStoreFixture(directory).loadJournal())
            .map((operation) => operation.payload['amount_value']),
        [-500, -700],
      );

      await offlineStoreFixture(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '추가',
          'amount_value': -300,
          'is_primary_income': 0,
        },
      );
      final restarted = await offlineStoreFixture(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2, 3]);
      expect(
        restarted.map((operation) => operation.payload['amount_value']),
        [-500, -700, -300],
      );
    });

    test('truncated JSON and UTF-8 tails preserve every complete record',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '정상',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      final journal = File('${directory.path}/offline-mode/journal.ndjson');
      final koreanPrefix = utf8.encode('한').sublist(0, 2);
      await journal.writeAsBytes(koreanPrefix,
          mode: FileMode.append, flush: true);

      final recovered = await offlineStoreFixture(directory).loadJournal();
      expect(recovered, hasLength(1));
      expect(recovered.single.payload['amount_value'], 500);

      await offlineStoreFixture(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '복구 후',
          'amount_value': 700,
          'is_primary_income': 0,
        },
      );
      final restarted = await offlineStoreFixture(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2]);
      expect(restarted.map((operation) => operation.payload['amount_value']),
          [500, 700]);

      await journal.writeAsString('{"schema_version":',
          mode: FileMode.append, flush: true);
      expect(await offlineStoreFixture(directory).loadJournal(), hasLength(2));
      await offlineStoreFixture(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '두 번째 복구 후',
          'amount_value': 300,
          'is_primary_income': 0,
        },
      );
      expect(await offlineStoreFixture(directory).loadJournal(), hasLength(3));
    });

    test('concurrent appends serialize sequence allocation and durable writes',
        () async {
      final directory = await temporaryDirectoryFixture();
      final firstWriteEntered = Completer<void>();
      final releaseFirstWrite = Completer<void>();
      var hookCalls = 0;
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeJournalAppendWrite: () async {
          hookCalls += 1;
          if (hookCalls == 1) {
            firstWriteEntered.complete();
            await releaseFirstWrite.future;
          }
        },
      );

      final first = store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': 'A',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await firstWriteEntered.future;
      final second = store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': 'B',
          'amount_value': -700,
          'is_primary_income': 0,
        },
      );
      releaseFirstWrite.complete();

      final appended = await Future.wait([first, second]);
      expect(appended.map((operation) => operation.sequence), [1, 2]);
      final restarted = await offlineStoreFixture(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2]);
      expect(restarted.map((operation) => operation.payload['amount_value']),
          [-500, -700]);
    });
  });
}
