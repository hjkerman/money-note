import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/notification_bridge.dart';
import 'package:money_note_mobile/src/screens/notification_import_screen.dart';

class _CandidateBridge extends NotificationBridge {
  _CandidateBridge(this.candidates);

  final List<CardNotificationCandidate> candidates;
  bool failDelete = false;
  int deleteAttempts = 0;

  @override
  Future<List<CardNotificationCandidate>> listCandidates() async => candidates;

  @override
  Future<List<CapturedNotificationLog>> listWooriLogs() async => [];

  @override
  Future<List<CapturedNotificationLog>> listHighwayTollLogs() async => [];

  @override
  Future<void> deleteCandidate(String id) async {
    deleteAttempts += 1;
    if (failDelete) throw StateError('injected candidate deletion failure');
    candidates.removeWhere((candidate) => candidate.id == id);
  }
}

class _RecordingState extends AppState {
  _RecordingState({required bool ownerDiscount, required bool familyDiscount})
      : super(MoneyNoteApiClient(baseUrl: 'https://example.invalid')) {
    ownerDiscountMonth = CardDiscountMonth(
      month: '2026-09',
      scope: 'owner',
      policy: ownerDiscount ? 'enabled' : 'disabled',
    );
    familyDiscountMonth = CardDiscountMonth(
      month: '2026-09',
      scope: 'family',
      policy: familyDiscount ? 'enabled' : 'disabled',
    );
  }

  String? registeredTarget;
  bool? registeredDiscount;
  String? registeredKey;
  final Map<String, bool> historicalDefaults = {};
  final Map<String, Completer<bool?>> pendingDefaults = {};

  @override
  Future<bool?> notificationDiscountDefault(String date, String scope) async {
    final key = '$scope:${date.substring(0, 7)}';
    final pending = pendingDefaults[key];
    if (pending != null) return pending.future;
    return historicalDefaults[key];
  }

  @override
  Future<bool> createExpense({
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    int? netAmountOverride,
    String? spendingCategory,
    String? entryDate,
    String? candidateRegistrationKey,
  }) async {
    registeredTarget = 'ledger';
    registeredDiscount = discountEnabled;
    registeredKey = candidateRegistrationKey;
    return true;
  }

  @override
  Future<bool> createPanel({
    required String panelType,
    required String title,
    required int amount,
    bool discountEnabled = true,
    String? spentOn,
    String? candidateRegistrationKey,
  }) async {
    registeredTarget = panelType;
    registeredDiscount = discountEnabled;
    registeredKey = candidateRegistrationKey;
    return true;
  }

  @override
  Future<void> refreshNotificationInboxState({bool notify = true}) async {}
}

class _NoRefreshState extends AppState {
  _NoRefreshState(super.api);

  @override
  Future<void> refreshInputArea({bool notify = true}) async {
    throw StateError('test refresh unavailable');
  }
}

CardNotificationCandidate _candidate(String id, String role,
        {String date = '2026-09-15'}) =>
    CardNotificationCandidate(
      id: id,
      source: 'woori_card',
      capturedAt: 1,
      cardLast4: role == 'family' ? '5678' : '1234',
      cardRole: role,
      entryDate: date,
      amount: 1000,
      merchant: '가게',
      usageItem: '식사',
      rawText: '승인 알림',
    );

bool _checkboxValue(WidgetTester tester) =>
    tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value!;

Future<void> _showCandidate(
  WidgetTester tester,
  _RecordingState state,
  List<CardNotificationCandidate> candidates, {
  required bool family,
}) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(1200, 2400);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(MaterialApp(
    home: NotificationImportScreen(
      state: state,
      bridge: _CandidateBridge(candidates),
    ),
  ));
  await tester.pumpAndSettle();
  if (family) {
    await tester.tap(find.text('가족카드(${candidates.length})'));
    await tester.pumpAndSettle();
  }
}

void main() {
  testWidgets(
      'candidate deletion failure keeps native evidence after successful submit',
      (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1200, 2400);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final state = _RecordingState(ownerDiscount: true, familyDiscount: false);
    final bridge = _CandidateBridge([_candidate('delete-failure', 'owner')])
      ..failDelete = true;
    await tester.pumpWidget(MaterialApp(
      home: NotificationImportScreen(state: state, bridge: bridge),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('등록'));
    await tester.pumpAndSettle();
    expect(state.registeredKey, 'woori_card:delete-failure');
    expect(bridge.deleteAttempts, 1);
    expect(bridge.candidates, hasLength(1));
    expect(find.text('등록'), findsNothing);
  });

  test('historical default requests the transaction month from server',
      () async {
    final requested = <String>[];
    final api = MoneyNoteApiClient(
      baseUrl: 'https://example.invalid',
      client: MockClient((request) async {
        requested.add(request.url.toString());
        return http.Response(
            jsonEncode({
              'month': '2026-08',
              'scope': 'family',
              'policy': 'enabled',
            }),
            200,
            headers: {'content-type': 'application/json'});
      }),
    );
    final state = AppState(api)
      ..familyDiscountMonth = CardDiscountMonth(
        month: '2026-09',
        scope: 'family',
        policy: 'disabled',
      );
    expect(await state.notificationDiscountDefault('2026-08-31', 'family'),
        isTrue);
    expect(requested.single,
        contains('/api/card-discounts/months/2026-08?scope=family'));
  });

  testWidgets(
      'August Main ON beats September Main OFF for historical candidate',
      (tester) async {
    final state = _RecordingState(ownerDiscount: false, familyDiscount: false)
      ..historicalDefaults['owner:2026-08'] = true;
    await _showCandidate(
        tester, state, [_candidate('aug-owner', 'owner', date: '2026-08-31')],
        family: false);
    expect(_checkboxValue(tester), isTrue);
    await tester.tap(find.text('등록'));
    await tester.pumpAndSettle();
    expect(state.registeredDiscount, isTrue);
  });

  testWidgets('Family historical month default survives usage ownership switch',
      (tester) async {
    final state = _RecordingState(ownerDiscount: true, familyDiscount: false)
      ..historicalDefaults['family:2026-08'] = true;
    await _showCandidate(
        tester, state, [_candidate('aug-family', 'family', date: '2026-08-31')],
        family: true);
    expect(_checkboxValue(tester), isTrue);
    await tester.tap(find.text('본인 사용'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isTrue);
    await tester.tap(find.text('등록'));
    await tester.pumpAndSettle();
    expect(state.registeredTarget, 'ledger');
    expect(state.registeredDiscount, isTrue);
  });

  testWidgets(
      'stale policy result from previous date cannot change current default',
      (tester) async {
    final state = _RecordingState(ownerDiscount: false, familyDiscount: false);
    final old = Completer<bool?>();
    state.pendingDefaults['owner:2026-08'] = old;
    state.historicalDefaults['owner:2026-07'] = false;
    await _showCandidate(
        tester, state, [_candidate('date-switch', 'owner', date: '2026-08-31')],
        family: false);
    await tester.enterText(find.byType(TextField).first, '2026-07-31');
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
    old.complete(true);
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
  });

  for (final testCase in [
    (
      role: 'owner',
      owner: true,
      family: false,
      target: 'ledger',
      expected: true
    ),
    (
      role: 'owner',
      owner: false,
      family: true,
      target: 'ledger',
      expected: false
    ),
    (
      role: 'family',
      owner: false,
      family: true,
      target: 'family_card',
      expected: true
    ),
    (
      role: 'family',
      owner: false,
      family: true,
      target: 'ledger',
      expected: true
    ),
    (
      role: 'family',
      owner: true,
      family: false,
      target: 'family_card',
      expected: false
    ),
    (
      role: 'family',
      owner: true,
      family: false,
      target: 'ledger',
      expected: false
    ),
  ]) {
    testWidgets(
        '${testCase.role} 알림 ${testCase.target} 등록은 알림 카드 정책을 기본값으로 사용한다',
        (tester) async {
      final state = _RecordingState(
        ownerDiscount: testCase.owner,
        familyDiscount: testCase.family,
      );
      final candidate = _candidate('candidate-1', testCase.role);
      await _showCandidate(tester, state, [candidate],
          family: testCase.role == 'family');

      if (testCase.target == 'ledger' && testCase.role == 'family') {
        await tester.tap(find.text('본인 사용'));
        await tester.pumpAndSettle();
      }
      expect(_checkboxValue(tester), testCase.expected);
      await tester.tap(find.text('등록'));
      await tester.pumpAndSettle();

      expect(state.registeredTarget, testCase.target);
      expect(state.registeredDiscount, testCase.expected);
      expect(state.registeredKey, candidate.registrationKey);
    });
  }

  testWidgets('본인카드 알림의 청구 사용 전환도 본인카드 기본값을 유지한다', (tester) async {
    final state = _RecordingState(ownerDiscount: false, familyDiscount: true);
    final candidate = _candidate('owner-claim', 'owner');
    await _showCandidate(tester, state, [candidate], family: false);
    await tester.tap(find.text('청구 사용'));
    await tester.pumpAndSettle();

    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('등록'));
    await tester.pumpAndSettle();
    expect(state.registeredTarget, 'claim');
    expect(state.registeredDiscount, isFalse);
    expect(state.registeredKey, candidate.registrationKey);
  });

  testWidgets('명시적으로 바꾼 체크값은 가족/본인 사용 전환에도 유지된다', (tester) async {
    final state = _RecordingState(ownerDiscount: false, familyDiscount: true);
    await _showCandidate(tester, state, [_candidate('explicit', 'family')],
        family: true);
    expect(_checkboxValue(tester), isTrue);

    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('본인 사용'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('가족 사용'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('등록'));
    await tester.pumpAndSettle();
    expect(state.registeredTarget, 'family_card');
    expect(state.registeredDiscount, isFalse);
  });

  testWidgets('후보 이동 시 각 카드의 기본값과 explicit override가 섞이지 않는다', (tester) async {
    final state = _RecordingState(ownerDiscount: false, familyDiscount: true);
    await _showCandidate(tester, state,
        [_candidate('owner-1', 'owner'), _candidate('family-1', 'family')],
        family: false);
    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('가족카드(1)'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isTrue);
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
    await tester.tap(find.text('본인카드(1)'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
    await tester.tap(find.text('가족카드(1)'));
    await tester.pumpAndSettle();
    expect(_checkboxValue(tester), isFalse);
  });

  test('원장 HTTP 요청은 final checkbox false를 보내고 true는 자동할인 기본값을 따른다', () async {
    final bodies = <Map<String, dynamic>>[];
    final api = MoneyNoteApiClient(
      baseUrl: 'https://example.invalid',
      client: MockClient((request) async {
        bodies.add(jsonDecode(request.body) as Map<String, dynamic>);
        return http.Response(
          '{"id":1,"book_section":"current","entry_kind":"expense","title":"가게","amount_value":1000}',
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );
    final state = _NoRefreshState(api);
    for (final value in [false, true]) {
      final saved = await state.createExpense(
        entryDate: '2026-09-15',
        usagePlace: '가게',
        usageItem: '식사',
        amount: 1000,
        discountEnabled: value,
        candidateRegistrationKey: 'woori_card:family-1',
      );
      expect(saved, isTrue);
    }
    expect(bodies[0]['discount_enabled'], isFalse);
    expect(bodies[1].containsKey('discount_enabled'), isFalse);
    expect(bodies[0]['candidate_registration_key'], 'woori_card:family-1');
    expect(bodies[1]['candidate_registration_key'], 'woori_card:family-1');
  });
}
