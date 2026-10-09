import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/coherent_refresh_coordinator.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/offline/online_write_state.dart';

import 'authoritative_bundle_test.dart' show specimen, owner, baseline;

String? legacySection(Uri uri) =>
    {
      '/api/month/current/status': 'month_close_status',
      '/api/entries/current': 'entries',
      '/api/month/current/panels': 'panels',
      '/api/month/current/summary': 'summary',
      '/api/card-payments/current': 'card_payment_status',
      '/api/judgment/current': 'judgment',
      '/api/month/current/planned/confirmed': 'confirmed_planned_entries',
      '/api/settings': 'settings',
      '/api/cash-flows': 'cash_flows',
    }[uri.path] ??
    (uri.path.startsWith('/api/card-discounts/months/')
        ? '${uri.queryParameters['scope']}_discount_month'
        : uri.path.startsWith('/api/card-discounts/profiles/transit/')
            ? 'transit_discount_profile'
            : null);

class BundleTransport {
  final calls = <String>[];
  Map<String, dynamic> wire = specimen();
  Object? getFailure;
  int getStatus = 200;
  String? getBody;
  int postStatus = 200;
  bool losePost = false;
  int loginId = 1;
  Completer<void>? requested;
  Completer<void>? release;

  late final api = MoneyNoteApiClient(
      baseUrl: 'https://synthetic.invalid', client: MockClient(request));

  Future<http.Response> request(http.Request r) async {
    calls.add('${r.method} ${r.url.path}');
    if (r.method == 'GET' && r.url.path == '/api/authoritative-state') {
      final captured = utf8.encode(getBody ?? jsonEncode(wire));
      requested?.complete();
      final gate = release;
      requested = null;
      release = null;
      if (gate != null) await gate.future;
      if (getFailure != null) throw getFailure!;
      return http.Response.bytes(captured, getStatus);
    }
    if (r.method == 'POST' && r.url.path == '/api/entries') {
      if (losePost) throw http.ClientException('response lost');
      return http.Response(
          jsonEncode(postStatus == 200
              ? wire['state']['entries'].first
              : {'detail': 'rejected'}),
          postStatus);
    }
    if (r.method == 'POST' && r.url.path == '/api/cash-flows') {
      return http.Response(jsonEncode({'id': 100, ...jsonDecode(r.body)}), 200);
    }
    if (r.method == 'POST' && r.url.path == '/api/month/current/panels') {
      return http.Response(jsonEncode({'id': 100, ...jsonDecode(r.body)}), 200);
    }
    if (r.method == 'POST' && r.url.path.endsWith('/confirm-fixed') ||
        r.method == 'POST' && r.url.path.endsWith('/confirm')) {
      return http.Response('{}', 200);
    }
    if (r.method == 'PATCH' && r.url.path.startsWith('/api/settings/')) {
      return http.Response(jsonEncode(wire['state']['settings']), 200);
    }
    if (r.url.path == '/health') return http.Response('{}', 200);
    if (r.method == 'POST' && r.url.path == '/api/auth/logout') {
      return http.Response('{}', 200);
    }
    if (r.method == 'POST' && r.url.path == '/api/auth/mobile-login') {
      return http.Response(
          jsonEncode({
            'id': loginId,
            'username': 'owner',
            'display_name': 'Owner',
            'share_pin_needs_change': false,
            'session_token': 'synthetic-token'
          }),
          200);
    }
    if (r.method == 'GET' && r.url.path == '/api/admin/snapshot') {
      return http.Response(jsonEncode(wire['snapshot']), 200);
    }
    throw MoneyNoteApiException('unexpected legacy/auxiliary ${r.url}');
  }
}

Future<(AppState, OfflineStore, File)> stateFixture(BundleTransport t,
    {OfflineStore Function(Directory)? makeStore}) async {
  final dir = await Directory.systemTemp.createTemp('mn-b3-');
  addTearDown(() => dir.delete(recursive: true));
  final store =
      makeStore?.call(dir) ?? OfflineStore(directoryProvider: () async => dir);
  final state = AppState(t.api,
      offlineStore: store,
      connectivityRetryDelay: (_) => Completer<void>().future)
    ..user = owner
    ..isBootstrapping = false;
  addTearDown(state.dispose);
  return (state, store, File('${dir.path}/offline-mode/baseline.json'));
}

Future<bool> card(AppState s) => s.createExpense(
    usagePlace: 'shop', usageItem: 'fact', amount: 100, discountEnabled: true);

class InterruptedStore extends OfflineStore {
  InterruptedStore(Directory d) : super(directoryProvider: () async => d);
  bool failPublication = false;
  bool failCleanup = false;
  bool failCommittedMarker = false;
  Completer<void>? publicationStarted;
  Completer<void>? publicationRelease;
  @override
  Future<void> savePendingOnlineWrite(PendingOnlineWrite pending) async {
    if (failCommittedMarker &&
        pending.status == OnlineWriteStatus.serverCommittedRebuildPending) {
      throw const OfflinePersistenceException('interrupted committed marker');
    }
    await super.savePendingOnlineWrite(pending);
  }

  @override
  Future<void> replaceBaseline(OfflineBaseline b,
      {void Function()? beforePublish}) async {
    publicationStarted?.complete();
    final gate = publicationRelease;
    publicationStarted = null;
    publicationRelease = null;
    if (gate != null) await gate.future;
    if (failPublication) {
      throw const OfflinePersistenceException('interrupted publication');
    }
    await super.replaceBaseline(b, beforePublish: beforePublish);
  }

  @override
  Future<void> completeOnlineWrite(PendingOnlineWrite pending) async {
    if (failCleanup) {
      throw const OfflinePersistenceException('interrupted cleanup');
    }
    await super.completeOnlineWrite(pending);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (_) async => null);
  test('normal authoritative refresh is exactly one bundle GET', () async {
    final t = BundleTransport();
    final (s, store, _) = await stateFixture(t);
    await s.refreshInputArea(notify: false);
    expect(t.calls, ['GET /api/authoritative-state']);
    expect((await store.loadBaseline())!.authoritativeSnapshot,
        t.wire['snapshot']);
    expect(s.summary!.cardTotal, t.wire['state']['summary']['card_total']);
  });
  test('successful submit is POST then bundle, durable before completion',
      () async {
    final t = BundleTransport();
    final (s, store, _) = await stateFixture(t);
    expect(await card(s), true);
    expect(t.calls, ['POST /api/entries', 'GET /api/authoritative-state']);
    expect(await store.loadPendingOnlineWrite(owner.id), isNull);
    expect((await store.loadBaseline())!.authoritativeSnapshot,
        t.wire['snapshot']);
    expect(s.authoritativeRebuildPending, false);
  });
  test('bundle success is not an ambiguous POST receipt', () async {
    final t = BundleTransport()..losePost = true;
    final (s, store, _) = await stateFixture(t);
    expect(await card(s), false);
    expect((await store.loadPendingOnlineWrite(owner.id))!.status,
        OnlineWriteStatus.outcomeUnknown);
    t.losePost = false;
    expect(await s.rebuildAfterOnlineWrite(), false);
    expect(t.calls.where((c) => c.startsWith('POST')).length, 1);
    expect((await store.loadPendingOnlineWrite(owner.id))!.status,
        OnlineWriteStatus.outcomeUnknown);
    expect(await s.enterOfflineMode(), false);
  });

  for (final name in [
    'empty',
    'rich',
    'early',
    'boundary',
    'real',
    'closed',
    'canonical_edges',
    'identity_edges'
  ]) {
    test('normal AppState candidate and durable baseline equal legacy/$name',
        () async {
      final t = BundleTransport()
        ..wire = name == 'identity_edges'
            ? jsonDecode(
                File('test/fixtures/authoritative_bundle/identity_edges.json')
                    .readAsStringSync())
            : specimen(name);
      final legacyCalls = <String>[];
      final oracle = MoneyNoteApiClient(
          baseUrl: 'https://synthetic.invalid',
          client: MockClient((r) async {
            legacyCalls.add(r.url.path);
            final value = r.url.path == '/api/offline-reconciliation/baseline'
                ? {...t.wire['authority'], 'snapshot': t.wire['snapshot']}
                : t.wire['state'][legacySection(r.url)];
            expect(value, isNotNull, reason: r.url.toString());
            return http.Response.bytes(utf8.encode(jsonEncode(value)), 200);
          }));
      final c = CoherentRefreshCoordinator(oracle,
          localToday: () => t.wire['authority']['evaluation_date'],
          formatDate: (d) => d.toIso8601String().substring(0, 10));
      final legacy = await c.acquireLegacyForDiagnostics(() => owner);
      expect(legacyCalls.length, 14);
      final (s, store, _) = await stateFixture(t);
      await store.replaceBaseline(baseline(legacy));
      await s.refreshInputArea(notify: false);
      expect(t.calls, ['GET /api/authoritative-state']);
      final persisted = (await store.loadBaseline())!.toJson();
      final expected = baseline(legacy).toJson();
      // The local publication timestamp is volatile, not evaluation authority.
      persisted['synced_at'] = expected['synced_at'];
      expect(persisted, expected);
      expect(s.user, same(owner));
      expect(s.summary!.cardTotal, legacy.candidate.summary.cardTotal);
      expect(s.confirmedPlannedEntries.map((e) => e.id).toList(),
          legacy.candidate.confirmedPlannedEntries.map((e) => e.id).toList());
    });
  }

  for (final operation in [
    'cash',
    'claim',
    'family_card',
    'fixed',
    'planned',
    'settings'
  ]) {
    test('normal $operation mutation uses only receipt plus bundle', () async {
      final t = BundleTransport();
      final (s, _, _) = await stateFixture(t);
      await s.refreshInputArea(notify: false);
      t.calls.clear();
      switch (operation) {
        case 'cash':
          expect(
              await s.createCashFlow(
                  occurredOn: '2026-10-05',
                  title: 'cash',
                  amount: 100,
                  isIncome: true,
                  isPrimaryIncome: false),
              true);
        case 'claim':
        case 'family_card':
          expect(
              await s.createPanel(
                  panelType: operation, title: 'fact', amount: 100),
              true);
        case 'fixed':
          expect(await s.confirmFixedPanel(4, '2026-10-05', 100), true);
        case 'planned':
          expect(await s.confirmPlannedEntry(10, '2026-10-05', 100), true);
        case 'settings':
          await s.updateSetting('card_limit', '100000');
      }
      expect(t.calls.length, 2);
      expect(t.calls.first.split(' ').first,
          operation == 'settings' ? 'PATCH' : 'POST');
      expect(t.calls.last, 'GET /api/authoritative-state');
    });
  }

  for (final kind in [
    '401',
    '403',
    '500',
    'timeout',
    'refused',
    'reset',
    'partial',
    'json',
    'version',
    'money',
    'unicode',
    'hash',
    'principal'
  ]) {
    for (final existing in [false, true]) {
      test('confirmed POST plus $kind bundle fails closed/$existing', () async {
        final t = BundleTransport();
        final (s, store, file) = await stateFixture(t);
        if (existing) await s.refreshInputArea(notify: false);
        final before = existing ? await file.readAsBytes() : null;
        final oldSummary = s.summary;
        t.calls.clear();
        switch (kind) {
          case '401':
          case '403':
          case '500':
            t.getStatus = int.parse(kind);
            t.getBody = '{"detail":"failed"}';
          case 'timeout':
            t.getFailure = TimeoutException('timeout');
          case 'refused':
            t.getFailure = const SocketException('refused');
          case 'reset':
            t.getFailure = http.ClientException('reset');
          case 'partial':
            t.getBody = '{"bundle_version":';
          case 'json':
            t.getBody = 'not JSON';
          case 'version':
            t.wire['bundle_version'] = 99;
          case 'money':
            t.getBody = jsonEncode(t.wire)
                .replaceFirst('"card_total":', '"card_total":0.5,"other":');
          case 'unicode':
            t.wire['state']['judgment']['budget']['message'] =
                String.fromCharCode(0xd800);
          case 'hash':
            t.wire['snapshot']['snapshot_id'] = '0' * 64;
          case 'principal':
            t.wire['principal']['user_id'] = 2;
        }
        expect(await card(s), false);
        expect(s.onlineWriteStatus,
            OnlineWriteStatus.serverCommittedRebuildPending);
        expect((await store.loadPendingOnlineWrite(owner.id))!.status,
            OnlineWriteStatus.serverCommittedRebuildPending);
        expect(s.summary, same(oldSummary));
        expect(t.calls, ['POST /api/entries', 'GET /api/authoritative-state']);
        if (existing) {
          expect(await file.readAsBytes(), before);
        } else {
          expect(await file.exists(), false);
        }
      });
    }
  }

  test('definite POST rejection does not acquire or leave pending', () async {
    final t = BundleTransport()..postStatus = 422;
    final (s, store, file) = await stateFixture(t);
    expect(await card(s), false);
    expect(t.calls, ['POST /api/entries']);
    expect(await store.loadPendingOnlineWrite(owner.id), isNull);
    expect(await file.exists(), false);
  });

  for (final race in ['newer-refresh', 'mutation', 'mode', 'logout', 'owner']) {
    test('normal late bundle cannot cross $race', () async {
      final t = BundleTransport();
      final (s, store, file) = await stateFixture(t);
      await s.refreshInputArea(notify: false);
      final before = await file.readAsBytes();
      final started = Completer<void>();
      final release = Completer<void>();
      t.requested = started;
      t.release = release;
      final late = s.refreshInputArea(notify: false);
      final rejected = expectLater(late, throwsA(isA<MoneyNoteApiException>()));
      await started.future;
      if (race == 'newer-refresh') await s.refreshInputArea(notify: false);
      if (race == 'mutation') expect(await card(s), true);
      if (race == 'mode') expect(await s.enterOfflineMode(), true);
      if (race == 'logout') await s.logout();
      if (race == 'owner') {
        s.user = AuthUser(
            id: 2,
            username: 'other',
            displayName: 'other',
            sharePinNeedsChange: false);
      }
      final current = await file.readAsBytes();
      release.complete();
      await rejected;
      expect(await file.readAsBytes(), current);
      if (race == 'owner' || race == 'logout') {
        expect(await file.readAsBytes(), before);
      }
      if (race == 'mode') expect(s.isOffline, true);
      expect(await store.loadBaseline(), isNotNull);
    });
  }

  for (final boundary in ['publication', 'cleanup', 'committed-marker']) {
    test('interruption at $boundary preserves recovery evidence', () async {
      final t = BundleTransport();
      late InterruptedStore disk;
      final (s, store, file) =
          await stateFixture(t, makeStore: (d) => disk = InterruptedStore(d));
      await s.refreshInputArea(notify: false);
      final before = await file.readAsBytes();
      disk.failPublication = boundary == 'publication';
      disk.failCleanup = boundary == 'cleanup';
      disk.failCommittedMarker = boundary == 'committed-marker';
      expect(await card(s), false);
      expect(s.authoritativeRebuildPending, true);
      expect(await store.loadPendingOnlineWrite(owner.id), isNotNull);
      if (boundary != 'cleanup') expect(await file.readAsBytes(), before);
      disk.failPublication = false;
      disk.failCleanup = false;
      disk.failCommittedMarker = false;
      // Simulate restart with the SAME durable evidence; never replay a POST.
      final restarted = AppState(t.api, offlineStore: store)
        ..user = owner
        ..isBootstrapping = false;
      addTearDown(restarted.dispose);
      final posts = t.calls.where((r) => r.startsWith('POST')).length;
      final restored =
          await restarted.restorePersistedOfflineWorkspace(notify: false);
      // false means the persisted workspace is online (not an offline view).
      expect(restored, false);
      expect(restarted.isOnline, true);
      if (boundary == 'committed-marker') {
        expect(restarted.onlineWriteStatus, OnlineWriteStatus.outcomeUnknown);
        expect(await restarted.rebuildAfterOnlineWrite(), false);
      } else {
        expect(await restarted.rebuildAfterOnlineWrite(), true);
        expect(await store.loadPendingOnlineWrite(owner.id), isNull);
      }
      expect(t.calls.where((r) => r.startsWith('POST')).length, posts);
    });
  }

  test('UI stays locked until guarded baseline publication completes',
      () async {
    final t = BundleTransport();
    late InterruptedStore disk;
    final (s, store, _) =
        await stateFixture(t, makeStore: (d) => disk = InterruptedStore(d));
    final started = Completer<void>();
    final release = Completer<void>();
    disk.publicationStarted = started;
    disk.publicationRelease = release;
    final submitting = card(s);
    await started.future;
    expect(s.isBusy, true);
    expect(s.summary, isNull);
    expect((await store.loadPendingOnlineWrite(owner.id))!.status,
        OnlineWriteStatus.serverCommittedRebuildPending);
    release.complete();
    expect(await submitting, true);
    expect(s.isBusy, false);
    expect(s.summary, isNotNull);
    expect(await store.loadBaseline(), isNotNull);
  });

  test('owner change while publication awaits cannot publish older authority',
      () async {
    final t = BundleTransport();
    late InterruptedStore disk;
    final (s, _, file) =
        await stateFixture(t, makeStore: (d) => disk = InterruptedStore(d));
    await s.refreshInputArea(notify: false);
    final before = await file.readAsBytes();
    final started = Completer<void>();
    final release = Completer<void>();
    disk.publicationStarted = started;
    disk.publicationRelease = release;
    final late = s.refreshInputArea(notify: false);
    final rejected = expectLater(late, throwsA(isA<MoneyNoteApiException>()));
    await started.future;
    s.user = AuthUser(
        id: 2,
        username: 'other',
        displayName: 'other',
        sharePinNeedsChange: false);
    release.complete();
    await rejected;
    expect(s.user!.id, 2);
    expect(await file.readAsBytes(), before);
  });

  for (final id in [1, 2]) {
    test('logout/relogin generation rejects old normal bundle, owner $id',
        () async {
      final t = BundleTransport()..loginId = id;
      final (s, _, file) = await stateFixture(t);
      await s.refreshInputArea(notify: false);
      final started = Completer<void>();
      final release = Completer<void>();
      t.requested = started;
      t.release = release;
      final old = s.refreshInputArea(notify: false);
      final rejected = expectLater(old, throwsA(isA<MoneyNoteApiException>()));
      await started.future;
      await s.logout();
      t.wire['principal']['user_id'] = id;
      await s.login('owner', 'synthetic-password');
      expect(s.user!.id, id);
      final fresh = await file.readAsBytes();
      release.complete();
      await rejected;
      expect(s.user!.id, id);
      expect(await file.readAsBytes(), fresh);
      // Auxiliary health, authentication and launch-backup requests are real
      // operation HTTP calls, but not the authoritative acquisition graph.
      expect(
          t.calls.where((c) => c == 'GET /api/authoritative-state').length, 3);
      expect(t.calls, contains('GET /health'));
      expect(t.calls, contains('GET /api/admin/snapshot'));
    });
  }

  test('owner is pinned before notification wait and pending retirement',
      () async {
    final t = BundleTransport();
    final (s, store, file) = await stateFixture(t);
    await s.refreshInputArea(notify: false);
    final before = await file.readAsBytes();
    t.getStatus = 500;
    expect(await card(s), false);
    t.getStatus = 200;
    const channel = MethodChannel('money_note/notifications');
    final entered = Completer<void>();
    final release = Completer<void>();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      if (call.method == 'permissionStatus') {
        entered.complete();
        await release.future;
        return <String, bool>{};
      }
      return null;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding
        .instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null));
    final refresh = s.refresh(notify: false);
    final rejected =
        expectLater(refresh, throwsA(isA<MoneyNoteApiException>()));
    await entered.future;
    s.user = AuthUser(
        id: 2,
        username: 'other',
        displayName: 'other',
        sharePinNeedsChange: false);
    t.wire['principal']['user_id'] = 2;
    release.complete();
    await rejected;
    expect(await file.readAsBytes(), before);
    expect((await store.loadPendingOnlineWrite(owner.id))!.status,
        OnlineWriteStatus.serverCommittedRebuildPending);
    expect(s.user!.id, 2);
  });
}
