import 'dart:io';
import 'verified_gzip.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// Only the two completed JSON GET bodies use raw HTTP and verified decoding.
/// Injected clients must also deliver raw bytes when declaring Content-Encoding.
class ResponseCodingClient extends http.BaseClient {
  ResponseCodingClient({http.Client? client})
      : _ordinary = client ?? http.Client(),
        _raw = client ?? IOClient(HttpClient()..autoUncompress = false);

  final http.Client _ordinary;
  final http.Client _raw;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final affected = request.method == 'GET' &&
        const {'/api/authoritative-state', '/api/admin/snapshot'}
            .contains(request.url.path);
    if (!affected) return _ordinary.send(request);
    final response = await _raw.send(request);
    final bytes = await response.stream.toBytes();
    final length = response.contentLength;
    if (length != null && length != bytes.length) {
      throw http.ClientException('Incomplete HTTP response', request.url);
    }
    final encoding = response.headers['content-encoding']?.trim().toLowerCase();
    if (encoding == null || encoding == 'identity') {
      if (bytes.length >= 2 && bytes[0] == 0x1f && bytes[1] == 0x8b) {
        throw http.ClientException(
            'Gzip body without gzip metadata', request.url);
      }
      final headers = Map<String, String>.from(response.headers)
        ..remove('transfer-encoding')
        ..['content-length'] = '${bytes.length}';
      return http.StreamedResponse(Stream.value(bytes), response.statusCode,
          contentLength: bytes.length,
          headers: headers,
          request: response.request,
          isRedirect: response.isRedirect,
          persistentConnection: response.persistentConnection,
          reasonPhrase: response.reasonPhrase);
    }
    if (encoding != 'gzip') {
      throw http.ClientException(
          'Unsupported response Content-Encoding', request.url);
    }
    try {
      final decoded = decodeVerifiedGzip(bytes);
      final headers = Map<String, String>.from(response.headers)
        ..remove('content-encoding')
        ..remove('transfer-encoding')
        ..['content-length'] = '${decoded.length}';
      return http.StreamedResponse(Stream.value(decoded), response.statusCode,
          contentLength: decoded.length,
          headers: headers,
          request: response.request,
          isRedirect: response.isRedirect,
          persistentConnection: response.persistentConnection,
          reasonPhrase: response.reasonPhrase);
    } catch (_) {
      throw http.ClientException(
          'Invalid or incomplete gzip response', request.url);
    }
  }

  @override
  void close() {
    _ordinary.close();
    if (!identical(_ordinary, _raw)) _raw.close();
  }
}
