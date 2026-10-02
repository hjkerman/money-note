import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_projection.dart';
import 'support/offline_mode_fixtures.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/formatters.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('exact boundary and invalid money are not truncated', () {
    expect(exactMoney(maxMoney), maxMoney);
    for (final value in [maxMoney + 1, maxMoney + 2, 0.5, -0.5]) {
      expect(() => exactMoney(value), throwsFormatException);
    }
    expect(exactMoney(10000.0), 10000);
    expect(won(maxMoney), '9,007,199,254,740,991원');
    final payload = jsonDecode(jsonEncode({'cash_flow_balance': maxMoney}));
    expect(Summary.fromJson(payload).cashFlowBalance, maxMoney);
    expect(() => Summary.fromJson({'cash_flow_balance': maxMoney + 1}),
        throwsFormatException);
    expect(() => Summary.fromJson({'cash_flow_balance': 0.5}),
        throwsFormatException);
  });
  test('nested monetary fields are checked without treating rates as money',
      () {
    expect(
        () => validateMoneyPayload({
              'rows': [
                {'amount_value': maxMoney + 1}
              ]
            }),
        throwsFormatException);
    expect(() => validateMoneyPayload({'rate': 0.012, 'amount_value': 10000}),
        returnsNormally);
    for (final key in [
      'scheduled_income',
      'cash_flow_balance',
      'card_limit',
      'base_next_month_liquidity',
      'liquidity_status'
    ]) {
      expect(() => validateMoneyPayload({key: '9007199254740993'}),
          throwsFormatException);
      expect(
          () => validateMoneyPayload({'key': key, 'value': '9007199254740993'}),
          throwsFormatException);
      expect(() => validateMoneyPayload({key: '9007199254740991'}),
          returnsNormally);
    }
  });
  test('journal rejects unsafe row and aggregate before durable append',
      () async {
    final directory = await temporaryDirectoryFixture();
    final store = offlineStoreFixture(directory);
    final json = baselineFixture().toJson();
    (json['summary'] as Map)['cash_flow_balance'] = maxMoney;
    (json['summary'] as Map)['remaining_liquidity'] = maxMoney;
    (json['summary'] as Map)['current_month_spendable'] = maxMoney;
    final baseline = OfflineBaseline.fromJson(json);
    await store.replaceBaseline(baseline);
    for (final amount in [maxMoney + 1, 1]) {
      await expectLater(
          store.appendOperation(
              type: OfflineOperationType.createCashFlow,
              payload: {
                'occurred_on': '2026-09-17',
                'amount_value': amount,
                'sort_order': 1
              },
              baseline: baseline),
          throwsFormatException);
      expect(await store.loadJournal(), isEmpty);
    }
    await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: {
          'occurred_on': '2026-09-17',
          'amount_value': -1,
          'sort_order': 1
        },
        baseline: baseline);
    final restarted = offlineStoreFixture(directory);
    final loaded = await restarted.loadBaseline();
    final journal = await restarted.loadJournal();
    expect(loaded!.summary.cashFlowBalance, maxMoney);
    expect(journal.single.payload['amount_value'], -1);
    expect(
        OfflineProjection.from(loaded, journal,
                projectedAt: DateTime(2026, 9, 17))
            .summary
            .cashFlowBalance,
        maxMoney - 1);
  });

  test('nine digit rate descriptor does not overflow native intermediate', () {
    final json = baselineFixture(remainingLiquidity: maxMoney).toJson();
    for (final key in [
      'card_total',
      'current_spending_total',
      'current_discount_total'
    ]) {
      (json['summary'] as Map)[key] = 0;
    }
    (json['owner_discount_month'] as Map)['projection_policy'] = {
      'schema_version': 1,
      'policy_id': 'test-rate',
      'type': 'flat_statement',
      'rounding': 'floor',
      'parameters': {'rate': '0.999999999'},
    };
    final baseline = OfflineBaseline.fromJson(json);
    final projection = OfflineProjection.from(baseline, [
      OfflineJournalOperation(
        operationId: 'exact-rate-test',
        type: OfflineOperationType.createCardExpense,
        payload: {
          'amount_value': maxMoney,
          'entry_date': '2026-09-17',
          'usage_place': 'shop'
        },
        createdAt: DateTime.utc(2026, 9, 17),
        sequence: 1,
      )
    ]);
    expect(projection.entries.last.effectiveDiscountAmount, 9007199245733791);
  });

  test(
      'invalid online input is definite before request, invalid response remains ambiguous',
      () async {
    var writes = 0;
    final api = MoneyNoteApiClient(
        baseUrl: 'http://localhost',
        client: MockClient((request) async {
          writes++;
          return http.Response(
              jsonEncode({
                'id': 1,
                'occurred_on': '2026-09-17',
                'title': 'cash',
                'amount_value': maxMoney + 1,
                'sort_order': 1
              }),
              200);
        }));
    await expectLater(
        api.createCashFlow(
            occurredOn: '2026-09-17',
            title: 'cash',
            amount: maxMoney + 1,
            isPrimaryIncome: false),
        throwsA(isA<MoneyNoteApiException>()
            .having((error) => error.statusCode, 'definite pre-request', 422)));
    expect(writes, 0);
    await expectLater(
        api.createCashFlow(
            occurredOn: '2026-09-17',
            title: 'cash',
            amount: 10000,
            isPrimaryIncome: false),
        throwsFormatException);
    expect(writes, 1);
  });
}
