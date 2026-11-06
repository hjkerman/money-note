import 'dart:io';
import 'package:archive/archive.dart';

/// Existing complete-stream verification, shared without changing HTTP policy.
List<int> decodeVerifiedGzip(List<int> bytes) {
  // This bounded profile accepts a single standard member. Optional-header
  // flags (including FHCRC, not verified by archive 3.x) are rejected.
  // Parsing/inflation/trailer verification belong to archive, not this code.
  if (bytes.length < 18 || bytes[3] != 0) {
    throw const FormatException('Unsupported or incomplete gzip header');
  }
  final input = InputStream(bytes);
  final decoded = GZipDecoder().decodeBuffer(input, verify: true);
  if (input.position != bytes.length) {
    throw const FormatException('Trailing gzip data or multiple members');
  }
  // archive verifies the complete trailer but can accept reserved DEFLATE
  // blocks. The independent SDK/zlib parser rejects invalid DEFLATE but can
  // accept missing trailers. Require BOTH, with byte-identical output.
  final comparison = _VerifiedOutput(decoded);
  final validation = gzip.decoder.startChunkedConversion(comparison);
  try {
    validation.add(bytes);
  } finally {
    validation.close();
  }
  if (!comparison.complete) {
    throw const FormatException('Incomplete DEFLATE validation');
  }
  return decoded;
}

/// Streaming output comparison only; no gzip or DEFLATE parsing here.
class _VerifiedOutput implements Sink<List<int>> {
  _VerifiedOutput(this.expected);
  final List<int> expected;
  int offset = 0;
  bool complete = false;

  @override
  void add(List<int> chunk) {
    if (complete || offset + chunk.length > expected.length) {
      throw const FormatException('Inconsistent gzip output length');
    }
    for (final byte in chunk) {
      if (expected[offset++] != byte) {
        throw const FormatException('Inconsistent gzip output');
      }
    }
  }

  @override
  void close() {
    if (offset != expected.length) {
      throw const FormatException('Incomplete gzip output');
    }
    complete = true;
  }
}
