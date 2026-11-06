import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'verified_gzip.dart';

const snapshotJsonLimit = 25 * 1024 * 1024;
const snapshotGzipLimit = 26 * 1024 * 1024;

bool isSnapshotName(String name) =>
    name.endsWith('.money-note-snapshot.json') ||
    name.endsWith('.money-note-snapshot.json.gz');
String snapshotMimeType(String name) =>
    name.endsWith('.json.gz') ? 'application/gzip' : 'application/json';

class SnapshotByteLimit implements Sink<List<int>> {
  SnapshotByteLimit(this.limit);
  final int limit;
  int count = 0;
  @override
  void add(List<int> chunk) {
    if (chunk.length > limit - count) {
      throw const FormatException('Snapshot size limit exceeded');
    }
    count += chunk.length;
  }

  @override
  void close() {}
}

Future<Uint8List> readSnapshotBytes(File file,
    {required bool compressed}) async {
  final limit = compressed ? snapshotGzipLimit : snapshotJsonLimit;
  final counter = SnapshotByteLimit(limit);
  final bytes = BytesBuilder(copy: false);
  await for (final chunk in file.openRead()) {
    counter.add(chunk);
    bytes.add(chunk);
  }
  return decodeSnapshotBytes(bytes.takeBytes(), compressed: compressed);
}

Uint8List decodeSnapshotBytes(Uint8List bytes, {required bool compressed}) {
  if (bytes.length > (compressed ? snapshotGzipLimit : snapshotJsonLimit)) {
    throw const FormatException('Snapshot input too large');
  }
  final magic = bytes.length >= 2 && bytes[0] == 0x1f && bytes[1] == 0x8b;
  if (magic != compressed) {
    throw const FormatException('Snapshot extension/content mismatch');
  }
  if (!compressed) return bytes;
  try {
    // Count-only preflight BEFORE archive allocates a complete output buffer.
    final sink = gzip.decoder
        .startChunkedConversion(SnapshotByteLimit(snapshotJsonLimit));
    try {
      sink.add(bytes);
    } finally {
      sink.close();
    }
    final decoded = decodeVerifiedGzip(bytes);
    if (decoded.length > snapshotJsonLimit) {
      throw const FormatException('Snapshot output too large');
    }
    return decoded is Uint8List ? decoded : Uint8List.fromList(decoded);
  } catch (_) {
    throw const FormatException(
        'Invalid, incomplete or oversized gzip Snapshot');
  }
}

Uint8List encodeSnapshotRestoreBody(Map<String, String> body) =>
    _encodeBoundedSnapshotJson(body);

Uint8List encodeSnapshotJson(Map<String, dynamic> snapshot) =>
    _encodeBoundedSnapshotJson(snapshot);

Uint8List _encodeBoundedSnapshotJson(Object body) {
  final output = _SnapshotRequestOutput();
  final encoder = json.fuse(utf8).encoder.startChunkedConversion(output);
  encoder.add(body);
  encoder.close();
  return output.bytes.takeBytes();
}

class _SnapshotRequestOutput extends SnapshotByteLimit {
  _SnapshotRequestOutput() : super(snapshotJsonLimit);
  final bytes = BytesBuilder(copy: false);
  @override
  void add(List<int> chunk) {
    super.add(chunk);
    bytes.add(chunk);
  }
}
