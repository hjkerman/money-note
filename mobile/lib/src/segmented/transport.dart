// Explicit, inactive E2 transport. No credential persistence or app startup hook.
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/io_client.dart' show IOStreamedResponse;

import 'c1.dart';
import 'protocol.dart';

class SyncCancellation {
  final _signal = Completer<void>();
  final _listeners = <void Function()>{};
  bool get cancelled => _signal.isCompleted;
  Future<void> get whenCancelled => _signal.future;
  void cancel() {
    if (cancelled) return;
    _signal.complete();
    final callbacks = _listeners.toList(growable: false);
    _listeners.clear();
    for (final callback in callbacks) {
      try {
        callback();
      } catch (error, stack) {
        Zone.current.handleUncaughtError(error, stack);
      }
    }
  }

  // Futures cannot detach a registered then callback. Removable listeners keep
  // a long successful acquisition from retaining one callback per HTTP request.
  void Function() onCancel(void Function() callback) {
    if (cancelled) {
      callback();
      return () {};
    }
    _listeners.add(callback);
    return () => _listeners.remove(callback);
  }

  void check() {
    if (cancelled) rejectSegment('ACQUISITION_CANCELLED');
  }
}

class SyncReply {
  const SyncReply(this.status, this.bytes);
  final int status;
  final Uint8List bytes;
}

abstract interface class SegmentedTransport {
  String get origin;
  void checkSession();
  Future<SyncReply> exchange(String method, String path, Uint8List? body,
      SyncCancellation cancellation, int maxResponseBytes);
}

class AuthenticatedSegmentedTransport implements SegmentedTransport {
  AuthenticatedSegmentedTransport(
      {required this.client,
      required this.origin,
      required String? Function() credential,
      this.timeout = const Duration(seconds: 15)})
      : _credential = credential,
        _token = credential() {
    final uri = Uri.tryParse(origin);
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.path.isNotEmpty ||
        uri.origin != origin) {
      rejectSegment('ORIGIN_INVALID');
    }
    if (timeout <= Duration.zero || timeout > const Duration(seconds: 60)) {
      rejectSegment('FETCH_LIMIT_INVALID');
    }
    checkSession();
  }
  final http.Client client; // Borrowed: never close the application's client.
  @override
  final String origin;
  final Duration timeout;
  final String? Function() _credential;
  final String?
      _token; // Original existing Bearer session, never persisted here.
  @override
  void checkSession() {
    if (_token == null || _token.isEmpty) rejectSegment('AUTH_REQUIRED');
    if (_credential() != _token) rejectSegment('AUTHENTICATION_CHANGED');
  }

  @override
  Future<SyncReply> exchange(String method, String path, Uint8List? body,
      SyncCancellation cancellation, int maxResponseBytes) async {
    checkSession();
    cancellation.check();
    // Never resolve a caller supplied URL, follow redirects or forward a token
    // to another origin. Object hashes occur only in the bounded JSON body.
    final observation = RegExp(r'^/api/sync/v1/observations/[0-9a-f-]{36}$');
    final objects =
        RegExp(r'^/api/sync/v1/observations/[0-9a-f-]{36}/objects$');
    if (!(method == 'POST' &&
            (path == '/api/sync/v1/observations' || objects.hasMatch(path))) &&
        !(method == 'DELETE' && observation.hasMatch(path))) {
      rejectSegment('TRANSFER_PATH_INVALID');
    }
    if (body != null && body.length > 3 * 1048576) {
      rejectSegment('LOCAL_REQUEST_BUDGET');
    }
    final abort = Completer<void>();
    final ended = Completer<SyncReply>();
    void abortRequest() {
      if (!abort.isCompleted) abort.complete();
    }

    final timer = Timer(timeout, () {
      abortRequest();
      if (!ended.isCompleted) {
        ended.completeError(const SegmentedException('TRANSPORT_TIMEOUT'));
      }
    });
    // A per-request listener is removed on success too; no growing chain of
    // callbacks retained by a long-lived cancellation token.
    final removeCancellation = cancellation.onCancel(() {
      abortRequest();
      if (!ended.isCompleted) {
        ended.completeError(const SegmentedException('ACQUISITION_CANCELLED'));
      }
    });
    Future<SyncReply> run() async {
      final request = http.AbortableRequest(method, Uri.parse('$origin$path'),
          abortTrigger: abort.future)
        ..followRedirects = false
        ..headers['Authorization'] = 'Bearer $_token';
      if (body != null) {
        request.headers['Content-Type'] = 'application/json';
        request.bodyBytes = body;
      }
      final response = await client.send(request);
      final int? length;
      try {
        checkSession();
        cancellation.check();
        length = response.contentLength;
        if (length != null && (length < 0 || length > maxResponseBytes)) {
          abortRequest();
          rejectSegment('RESPONSE_SIZE_EXCEEDED');
        }
        if (response.statusCode >= 300 && response.statusCode < 400) {
          abortRequest();
          rejectSegment('REDIRECT_REJECTED');
        }
      } catch (_) {
        // The failure is already determined. Cleanup must not replace it with
        // a later timeout/cancel signal while awaiting native stream release.
        timer.cancel();
        removeCancellation();
        await _discardResponse(response);
        rethrow;
      }
      final bytes = BytesBuilder(copy: false);
      await for (final chunk in response.stream) {
        checkSession();
        cancellation.check();
        if (bytes.length + chunk.length > maxResponseBytes) {
          abortRequest();
          rejectSegment('RESPONSE_SIZE_EXCEEDED');
        }
        bytes.add(chunk);
      }
      if (length != null && bytes.length != length) {
        rejectSegment('RESPONSE_TRUNCATED');
      }
      checkSession();
      cancellation.check();
      return SyncReply(response.statusCode, bytes.takeBytes());
    }

    // Observe all late errors from a cancelled/timeout client. IOClient supports
    // AbortableRequest; injected clients must implement the same abort contract.
    run().then((reply) {
      if (!ended.isCompleted) ended.complete(reply);
    }, onError: (Object error, StackTrace stack) {
      if (ended.isCompleted) return;
      if (error is SegmentedException) {
        ended.completeError(error, stack);
      } else if (error is http.ClientException ||
          error is SocketException ||
          error is TimeoutException) {
        ended.completeError(
            const SegmentedException('TRANSPORT_UNAVAILABLE'), stack);
      } else {
        ended.completeError(
            const SegmentedException('TRANSPORT_FAILED'), stack);
      }
    });
    try {
      return await ended.future;
    } finally {
      timer.cancel();
      removeCancellation();
    }
  }
}

Future<void> _discardResponse(http.StreamedResponse response) async {
  Future<void> release() async {
    if (response is IOStreamedResponse) {
      try {
        // Public response-scoped API: remove this socket from the IOClient pool
        // and destroy it, without draining the body or closing the shared client.
        // Abort-before-listen in http 1.6.0 cannot do this. The continuation also
        // destroys a late socket if the bounded cleanup wait has already ended.
        await response.detachSocket().then((socket) => socket.destroy());
        return;
      } on Object {/* Injected IO responses may not have an inner socket. */}
    }
    await response.stream
        .listen(null, onError: (Object _, StackTrace __) {})
        .cancel();
  }

  try {
    await release().timeout(const Duration(seconds: 2));
  } on Object {/* Cleanup must not mask the original validation error. */}
}

class SyncRemoteException implements Exception {
  const SyncRemoteException(
      this.code, this.action, this.status, this.retryAfter);
  final String code, action;
  final int status;
  final int? retryAfter;
  @override
  String toString() => 'SyncRemoteException($code,$action)';
  factory SyncRemoteException.parse(SyncReply reply, String? requestId) {
    final v = record(decodeC1(reply.bytes, requireCanonical: false),
        ['protocol', 'request_id', 'error']);
    if (v['protocol'] != 1 ||
        v['protocol'] is! int ||
        (v['request_id'] != null && v['request_id'] != requestId)) {
      rejectSegment('ERROR_ENVELOPE_INVALID');
    }
    final e =
        record(v['error'], ['code', 'action', 'retry_after_ms', 'current_ns']);
    final code = e['code'], action = e['action'], retry = e['retry_after_ms'];
    if (code is! String ||
        !RegExp(r'^[A-Z][A-Z0-9_]{0,63}$').hasMatch(code) ||
        ![
          'retry_same',
          'new_observation',
          'full_resync',
          'blocked',
          'reauthenticate'
        ].contains(action) ||
        (retry != null && (retry is! int || retry < 0))) {
      rejectSegment('ERROR_ENVELOPE_INVALID');
    }
    if (e['current_ns'] != null) SyncNamespace.parse(e['current_ns']);
    const statuses = {
      'AUTH_REQUIRED': 401,
      'PRINCIPAL_OR_SESSION_CHANGED': 403,
      'EPOCH_CHANGED': 409,
      'BASE_INVALID': 409,
      'REQUEST_CONFLICT': 409,
      'OBSERVATION_CONFLICT': 409,
      'OBSERVATION_EXPIRED': 410,
      'OBSERVATION_INCOMPLETE': 410,
      'UNSUPPORTED_CONTRACT': 422,
      'INVALID_REQUEST': 422,
      'TRANSFER_BUDGET': 413,
      'LEASE_LIMIT': 429,
      'ROOT_NOT_READY': 503,
      'STORAGE_FAILED': 500
    };
    if (statuses[code] != reply.status) rejectSegment('ERROR_ENVELOPE_INVALID');
    const actions = {
      'AUTH_REQUIRED': 'reauthenticate',
      'PRINCIPAL_OR_SESSION_CHANGED': 'reauthenticate',
      'EPOCH_CHANGED': 'full_resync',
      'BASE_INVALID': 'full_resync',
      'REQUEST_CONFLICT': 'blocked',
      'OBSERVATION_CONFLICT': 'new_observation',
      'OBSERVATION_EXPIRED': 'new_observation',
      'OBSERVATION_INCOMPLETE': 'new_observation',
      'UNSUPPORTED_CONTRACT': 'blocked',
      'INVALID_REQUEST': 'blocked',
      'TRANSFER_BUDGET': 'retry_same',
      'LEASE_LIMIT': 'retry_same',
      'ROOT_NOT_READY': 'retry_same',
      'STORAGE_FAILED': 'blocked'
    };
    if (actions[code] != action) rejectSegment('ERROR_ENVELOPE_INVALID');
    return SyncRemoteException(
        code, action as String, reply.status, retry as int?);
  }
}
