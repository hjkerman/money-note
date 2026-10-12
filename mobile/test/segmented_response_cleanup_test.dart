import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart' show IOStreamedResponse;
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

import 'support/segmented_fixture.dart';

class _Client extends http.BaseClient {
  _Client(this.handle);
  final Future<http.StreamedResponse> Function(http.BaseRequest) handle;
  bool closed = false;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      handle(request);
  @override
  void close() => closed = true;
}

class _OwnedBody {
  _OwnedBody({Future<void> Function()? release}) {
    controller = StreamController<List<int>>(
      onListen: () => owners++,
      onCancel: () async {
        cancelCalls++;
        cancellationStarted.complete();
        try {
          await release?.call();
        } finally {
          owners--;
          released.complete();
        }
      },
    );
  }
  late final StreamController<List<int>> controller;
  final cancellationStarted = Completer<void>(), released = Completer<void>();
  int owners = 0, cancelCalls = 0;
  void dispose() => controller.close().ignore();
}

class _BadLength extends http.StreamedResponse {
  _BadLength(Stream<List<int>> stream) : super(stream, 200) {
    armed = true;
  }
  bool armed = false;
  @override
  int? get contentLength => armed ? -1 : super.contentLength;
}

class _UnreadableHeader extends http.StreamedResponse {
  _UnreadableHeader(Stream<List<int>> stream) : super(stream, 200) {
    armed = true;
  }
  bool armed = false;
  @override
  int? get contentLength =>
      armed ? throw StateError('synthetic header') : super.contentLength;
}

class _Socket extends Fake implements Socket {
  bool destroyed = false;
  @override
  void destroy() => destroyed = true;
}

class _DelayedIOResponse extends IOStreamedResponse {
  _DelayedIOResponse(this.socket, Stream<List<int>> stream)
      : super(stream, 302);
  final Future<Socket> socket;
  @override
  Future<Socket> detachSocket() => socket;
}

void main() {
  const origin = 'https://cleanup.synthetic';
  final credential = syncUuid();
  Matcher code(String expected) =>
      isA<SegmentedException>().having((error) => error.code, 'code', expected);
  Future<SyncReply> request(AuthenticatedSegmentedTransport transport,
          {SyncCancellation? cancel}) =>
      transport.exchange('POST', '/api/sync/v1/observations', null,
          cancel ?? SyncCancellation(), 4096);

  for (final kind in ['auth', 'redirect', 'oversized', 'negative', 'header']) {
    test('header $kind releases owned body once and keeps shared client usable',
        () async {
      final body = _OwnedBody();
      addTearDown(body.dispose);
      var token = credential, calls = 0;
      final client = _Client((_) async {
        if (++calls > 1) {
          return http.StreamedResponse(Stream.value(utf8.encode('{}')), 200,
              contentLength: 2);
        }
        if (kind == 'auth') token = syncUuid();
        if (kind == 'negative') return _BadLength(body.controller.stream);
        if (kind == 'header') return _UnreadableHeader(body.controller.stream);
        return http.StreamedResponse(
            body.controller.stream, kind == 'redirect' ? 302 : 200,
            contentLength: kind == 'oversized' ? 4097 : 4096);
      });
      final transport = AuthenticatedSegmentedTransport(
          client: client, origin: origin, credential: () => token);
      await expectLater(
          request(transport),
          throwsA(code(kind == 'auth'
              ? 'AUTHENTICATION_CHANGED'
              : kind == 'redirect'
                  ? 'REDIRECT_REJECTED'
                  : kind == 'header'
                      ? 'TRANSPORT_FAILED'
                      : 'RESPONSE_SIZE_EXCEEDED')));
      expect(body.released.isCompleted, isTrue);
      expect(body.owners, 0);
      expect(body.cancelCalls, 1);
      expect(client.closed, isFalse);
      final fresh = AuthenticatedSegmentedTransport(
          client: client, origin: origin, credential: () => token);
      expect((await request(fresh)).status, 200);
      expect(calls, 2);
    });
  }

  test('header rejection awaits cleanup; later timeout cannot mask the error',
      () async {
    final allowRelease = Completer<void>();
    final body = _OwnedBody(release: () => allowRelease.future);
    addTearDown(body.dispose);
    final client = _Client(
        (_) async => http.StreamedResponse(body.controller.stream, 302));
    final transport = AuthenticatedSegmentedTransport(
        client: client,
        origin: origin,
        credential: () => credential,
        timeout: const Duration(milliseconds: 20));
    var completed = false;
    final result = request(transport).whenComplete(() => completed = true);
    final assertion = expectLater(result, throwsA(code('REDIRECT_REJECTED')));
    await body.cancellationStarted.future;
    // Deliberately cross the request deadline while the release barrier is held.
    await Future<void>.delayed(const Duration(milliseconds: 40));
    expect(completed, isFalse);
    expect(body.owners, 1);
    allowRelease.complete();
    await assertion;
    expect(body.owners, 0);
    expect(client.closed, isFalse);
  });

  test(
      'cleanup failure preserves original header error and observes late errors',
      () async {
    final body = _OwnedBody(release: () async {
      throw StateError('synthetic cancellation failure');
    });
    addTearDown(body.dispose);
    final transport = AuthenticatedSegmentedTransport(
        client: _Client(
            (_) async => http.StreamedResponse(body.controller.stream, 302)),
        origin: origin,
        credential: () => credential);
    await expectLater(request(transport), throwsA(code('REDIRECT_REJECTED')));
    expect(body.owners, 0);
    expect(body.cancelCalls, 1);
  });

  test(
      'IO response destroys only its detached socket before reporting rejection',
      () async {
    final socket = _Socket(), body = _OwnedBody();
    addTearDown(body.dispose);
    final client = _Client((_) async =>
        _DelayedIOResponse(Future.value(socket), body.controller.stream));
    final transport = AuthenticatedSegmentedTransport(
        client: client, origin: origin, credential: () => credential);
    await expectLater(request(transport), throwsA(code('REDIRECT_REJECTED')));
    expect(socket.destroyed, isTrue);
    expect(client.closed, isFalse);
    expect(body.owners, 0);
  });

  test('IO response without socket falls back to awaited stream cancellation',
      () async {
    final body = _OwnedBody();
    addTearDown(body.dispose);
    final transport = AuthenticatedSegmentedTransport(
        client: _Client(
            (_) async => IOStreamedResponse(body.controller.stream, 302)),
        origin: origin,
        credential: () => credential);
    await expectLater(request(transport), throwsA(code('REDIRECT_REJECTED')));
    expect(body.released.isCompleted, isTrue);
    expect(body.cancelCalls, 1);
    expect(body.owners, 0);
  });

  test(
      'bounded cleanup keeps original error and destroys a late detached socket',
      () async {
    final late = Completer<Socket>(), socket = _Socket(), body = _OwnedBody();
    addTearDown(body.dispose);
    final transport = AuthenticatedSegmentedTransport(
        client: _Client((_) async =>
            _DelayedIOResponse(late.future, body.controller.stream)),
        origin: origin,
        credential: () => credential,
        timeout: const Duration(milliseconds: 20));
    final watch = Stopwatch()..start();
    await expectLater(request(transport), throwsA(code('REDIRECT_REJECTED')));
    expect(watch.elapsed, lessThan(const Duration(seconds: 5)));
    expect(socket.destroyed, isFalse);
    late.complete(socket);
    await Future<void>.delayed(Duration.zero);
    expect(socket.destroyed, isTrue);
  });

  for (final mode in ['cancel', 'timeout']) {
    test('$mode before late response still releases its response ownership',
        () async {
      final late = Completer<http.StreamedResponse>();
      final entered = Completer<void>(), body = _OwnedBody();
      addTearDown(body.dispose);
      final cancellation = SyncCancellation();
      final client = _Client((_) {
        entered.complete();
        return late.future;
      });
      final transport = AuthenticatedSegmentedTransport(
          client: client,
          origin: origin,
          credential: () => credential,
          timeout: mode == 'timeout'
              ? const Duration(milliseconds: 20)
              : const Duration(seconds: 15));
      final assertion = expectLater(
          request(transport, cancel: cancellation),
          throwsA(code(mode == 'cancel'
              ? 'ACQUISITION_CANCELLED'
              : 'TRANSPORT_TIMEOUT')));
      await entered.future;
      if (mode == 'cancel') cancellation.cancel();
      await assertion;
      // The deliberately late injected client ignores abort. Exercise this
      // correction's header-rejection cleanup without changing timeout policy.
      late.complete(http.StreamedResponse(
          body.controller.stream, mode == 'timeout' ? 302 : 200));
      await body.released.future;
      expect(body.owners, 0);
      expect(body.cancelCalls, 1);
      expect(client.closed, isFalse);
    });
  }

  test('valid byte stream still matches independent server C1/hash golden',
      () async {
    final golden = ServerGolden();
    const kind = 'raw-root';
    final raw = golden.bytes(kind);
    final client = _Client((_) async => http.StreamedResponse(
        Stream.fromIterable([
          raw.sublist(0, 1),
          raw.sublist(1, raw.length - 1),
          raw.sublist(raw.length - 1)
        ]),
        200,
        contentLength: raw.length));
    final transport = AuthenticatedSegmentedTransport(
        client: client, origin: origin, credential: () => credential);
    final reply = await request(transport);
    expect(reply.bytes, raw);
    expect(
        sha256.convert([
          ...ascii.encode('money-note.sync.v1/$kind'),
          0,
          ...reply.bytes
        ]).toString(),
        golden.ref(kind).hash);
    expect(
        VerifiedObject.verify(reply.bytes, golden.ref(kind), golden.cache).kind,
        kind);
    expect(client.closed, isFalse);
  });
}
