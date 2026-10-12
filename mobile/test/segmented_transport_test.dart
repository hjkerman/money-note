import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

import 'support/segmented_e2_fixture.dart';

class StubClient extends http.BaseClient {
  StubClient(this.handle);
  final Future<http.StreamedResponse> Function(http.BaseRequest) handle;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      handle(request);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final syntheticToken = syncUuid();
  test('cancellation listener removal does not accumulate completed requests',
      () {
    final token = SyncCancellation();
    var called = 0;
    for (var n = 0; n < 2000; n++) {
      final remove = token.onCancel(() => called++);
      remove();
    }
    final remove = token.onCancel(() => called++);
    token.cancel();
    token.cancel();
    remove();
    expect(called, 1);
    token.onCancel(() => called++);
    expect(called, 2);
  });
  Matcher code(String value) =>
      isA<SegmentedException>().having((e) => e.code, 'code', value);
  test(
      'borrows real API existing secure-storage Bearer without new login/store',
      () async {
    FlutterSecureStorage.setMockInitialValues({});
    final client = StubClient((request) async {
      expect(request.headers['Authorization'], 'Bearer $syntheticToken');
      expect(request.followRedirects, isFalse);
      expect(request.url.origin, syntheticOrigin);
      return http.StreamedResponse(Stream.value(utf8.encode('{}')), 200,
          contentLength: 2);
    });
    final api = MoneyNoteApiClient(client: client, baseUrl: syntheticOrigin);
    await api.saveSession(syntheticToken);
    final transport = segmentedTransportForApi(api);
    expect(
        (await transport.exchange('POST', '/api/sync/v1/observations',
                encodeC1(<String, dynamic>{}), SyncCancellation(), 8192))
            .status,
        200);
    await api.saveSession(null);
    expect(transport.checkSession, throwsA(code('AUTHENTICATION_CHANGED')));
  });
  for (final origin in [
    'http://e2.synthetic',
    'https://e2.synthetic/path',
    'https://u@e2.synthetic',
    'https://e2.synthetic?q=x',
    'https://e2.synthetic#x',
    'https://E2.synthetic',
    'https://e2.synthetic/'
  ]) {
    test('reject origin $origin before any credential forwarding', () {
      expect(
          () => AuthenticatedSegmentedTransport(
              client: http.Client(),
              origin: origin,
              credential: () => syntheticToken),
          throwsA(code('ORIGIN_INVALID')));
    });
  }
  test('missing existing credential fails before HTTP dispatch', () {
    expect(
        () => AuthenticatedSegmentedTransport(
            client: http.Client(),
            origin: syntheticOrigin,
            credential: () => null),
        throwsA(code('AUTH_REQUIRED')));
  });
  for (final path in [
    'https://other.synthetic/api/sync/v1/observations',
    '//other.synthetic/path',
    '/api/month/current/summary',
    '/api/sync/v1/observations/../objects',
    '/api/sync/v1/observations?x=y'
  ]) {
    test('reject unapproved transport locator $path', () async {
      var called = false;
      final client = StubClient((request) async {
        called = true;
        throw StateError('must not send');
      });
      final transport = AuthenticatedSegmentedTransport(
          client: client,
          origin: syntheticOrigin,
          credential: () => syntheticToken);
      await expectLater(
          transport.exchange('POST', path, null, SyncCancellation(), 8192),
          throwsA(code('TRANSFER_PATH_INVALID')));
      expect(called, isFalse);
    });
  }
  for (final kind in [
    'declared_size',
    'stream_size',
    'truncated',
    'redirect',
    'session_change',
    'stream_error'
  ]) {
    test('bounded HTTP response rejects $kind', () async {
      var token = syntheticToken;
      final client = StubClient((request) async {
        if (kind == 'session_change') token = '$syntheticToken-changed';
        return http.StreamedResponse(
            kind == 'stream_error'
                ? Stream.error(http.ClientException('synthetic'))
                : Stream.value(Uint8List(kind == 'stream_size' ? 1025 : 2)),
            kind == 'redirect' ? 302 : 200,
            contentLength: kind == 'declared_size'
                ? 1025
                : kind == 'truncated'
                    ? 3
                    : kind == 'stream_size'
                        ? null
                        : 2);
      });
      final transport = AuthenticatedSegmentedTransport(
          client: client, origin: syntheticOrigin, credential: () => token);
      final expected = {
        'declared_size': 'RESPONSE_SIZE_EXCEEDED',
        'stream_size': 'RESPONSE_SIZE_EXCEEDED',
        'truncated': 'RESPONSE_TRUNCATED',
        'redirect': 'REDIRECT_REJECTED',
        'session_change': 'AUTHENTICATION_CHANGED',
        'stream_error': 'TRANSPORT_UNAVAILABLE'
      }[kind]!;
      await expectLater(
          transport.exchange('POST', '/api/sync/v1/observations', null,
              SyncCancellation(), 1024),
          throwsA(code(expected)));
    });
  }
  for (final kind in ['cancel', 'timeout']) {
    test('real AbortableRequest propagates $kind; late exceptions observed',
        () async {
      final entered = Completer<void>(), aborted = Completer<void>();
      final client = StubClient((request) async {
        expect(request, isA<http.AbortableRequest>());
        entered.complete();
        await (request as http.AbortableRequest).abortTrigger;
        aborted.complete();
        throw http.ClientException('synthetic abort');
      });
      final transport = AuthenticatedSegmentedTransport(
          client: client,
          origin: syntheticOrigin,
          credential: () => syntheticToken,
          timeout: kind == 'timeout'
              ? const Duration(milliseconds: 20)
              : const Duration(seconds: 15));
      final cancellation = SyncCancellation();
      final result = transport.exchange(
          'POST', '/api/sync/v1/observations', null, cancellation, 1024);
      final assertion = expectLater(
          result,
          throwsA(code(kind == 'timeout'
              ? 'TRANSPORT_TIMEOUT'
              : 'ACQUISITION_CANCELLED')));
      await entered.future;
      if (kind == 'cancel') cancellation.cancel();
      await assertion;
      await aborted.future;
    });
  }
  test('request body budget checked before allocation by HTTP client',
      () async {
    final client = StubClient((_) async => throw StateError('must not send'));
    final transport = AuthenticatedSegmentedTransport(
        client: client,
        origin: syntheticOrigin,
        credential: () => syntheticToken);
    await expectLater(
        transport.exchange('POST', '/api/sync/v1/observations',
            Uint8List(3 * 1048576 + 1), SyncCancellation(), 8192),
        throwsA(code('LOCAL_REQUEST_BUDGET')));
  });
  for (final fault in [
    'status',
    'action',
    'nonce',
    'unknown_code',
    'extra',
    'retry_type'
  ]) {
    test('protocol error envelope rejects $fault', () {
      final nonce = syncUuid(),
          reply = remoteError('ROOT_NOT_READY', 'retry_same', 503, nonce);
      final b = decodeC1(reply.bytes) as Map<String, dynamic>;
      var status = 503;
      if (fault == 'status') status = 500;
      if (fault == 'action') b['error']['action'] = 'blocked';
      if (fault == 'nonce') b['request_id'] = syncUuid();
      if (fault == 'unknown_code') b['error']['code'] = 'MADE_UP';
      if (fault == 'extra') b['extra'] = null;
      if (fault == 'retry_type') b['error']['retry_after_ms'] = '100';
      expect(
          () =>
              SyncRemoteException.parse(SyncReply(status, encodeC1(b)), nonce),
          throwsA(isA<SegmentedException>()));
    });
  }
}
