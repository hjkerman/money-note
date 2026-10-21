// T6.6C §7. Independent of the frozen B-2 / Snapshot encoder.
import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
// B03 diagnostics: begin.
import '../diagnostics/logical_cost.dart';
// B03 diagnostics: end.

class SegmentedException implements Exception {
  const SegmentedException(this.code, {this.storageCode});
  final String code;
  final int?
      storageCode; // SQLite numeric result only, never SQL or bound values.
  @override
  String toString() => 'SegmentedException($code)';
}

Never rejectSegment(String code) => throw SegmentedException(code);

const maxExactMoney = 9007199254740991;
final maxSigned64 = BigInt.parse('9223372036854775807');
final minSigned64 = BigInt.parse('-9223372036854775808');

bool sameBytes(List<int> a, List<int> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

void scalarString(String value) {
  for (var i = 0; i < value.length; i++) {
    final c = value.codeUnitAt(i);
    if (c < 0xd800 || c > 0xdfff) continue;
    if (c > 0xdbff || ++i == value.length) rejectSegment('UNICODE_INVALID');
    final next = value.codeUnitAt(i);
    if (next < 0xdc00 || next > 0xdfff) rejectSegment('UNICODE_INVALID');
  }
}

int scalarCompare(String a, String b) =>
    byteCompare(utf8.encode(a), utf8.encode(b));
int byteCompare(List<int> a, List<int> b) {
  for (var i = 0; i < a.length && i < b.length; i++) {
    if (a[i] != b[i]) return a[i].compareTo(b[i]);
  }
  return a.length.compareTo(b.length);
}

Uint8List encodeC1(Object? value, {int maxDepth = 128}) {
  final out = StringBuffer();
  void emit(Object? v, int depth) {
    if (depth > maxDepth) rejectSegment('LOCAL_PARSE_BUDGET');
    if (v == null) {
      out.write('null');
    } else if (v is bool) {
      out.write(v ? 'true' : 'false');
    } else if (v is int) {
      final exact = BigInt.from(v);
      if (exact < minSigned64 || exact > maxSigned64) {
        rejectSegment('INTEGER_INVALID');
      }
      out.write(v);
    } else if (v is double) {
      if (!v.isFinite || v.abs() > maxExactMoney || v != v.truncateToDouble()) {
        rejectSegment('NUMBER_INVALID');
      }
      // All supported integral REALs are below Python's exponential threshold.
      out.write(v == 0 ? (v.isNegative ? '-0.0' : '0.0') : '${v.toInt()}.0');
    } else if (v is String) {
      scalarString(v);
      out.write('"');
      for (final c in v.runes) {
        out.write(switch (c) {
          0x22 => r'\"',
          0x5c => r'\\',
          8 => r'\b',
          12 => r'\f',
          10 => r'\n',
          13 => r'\r',
          9 => r'\t',
          < 32 => '\\u${c.toRadixString(16).padLeft(4, '0')}',
          _ => String.fromCharCode(c),
        });
      }
      out.write('"');
    } else if (v is List) {
      out.write('[');
      for (var i = 0; i < v.length; i++) {
        if (i != 0) out.write(',');
        emit(v[i], depth + 1);
      }
      out.write(']');
    } else if (v is Map<String, dynamic>) {
      for (final key in v.keys) {
        scalarString(key);
      }
      final keys = v.keys.toList()..sort(scalarCompare);
      out.write('{');
      for (var i = 0; i < keys.length; i++) {
        if (i != 0) out.write(',');
        emit(keys[i], depth + 1);
        out.write(':');
        emit(v[keys[i]], depth + 1);
      }
      out.write('}');
    } else {
      rejectSegment('REPRESENTATION_INVALID');
    }
  }

  emit(value, 0);
  // B03 encoding observation: begin.
  final bytes = Uint8List.fromList(utf8.encode(out.toString()));
  LogicalCost.observe(LogicalCostOperation.encoding,
      LogicalCostMetric.outputBytes, bytes.length);
  return bytes;
  // B03 encoding observation: end.
}

Object? decodeC1(List<int> bytes,
    {bool requireCanonical = true, int maxDepth = 128}) {
  // B03 decode observation: begin.
  LogicalCost.observe(LogicalCostOperation.c1, LogicalCostMetric.calls, 1);
  LogicalCost.observe(
      LogicalCostOperation.c1, LogicalCostMetric.submittedBytes, bytes.length);
  var completed = false;
  // B03 decode observation: end.
  try {
    final parser = _Parser(utf8.decode(bytes, allowMalformed: false), maxDepth);
    final value = parser.read(0);
    parser.space();
    if (parser.position != parser.text.length) {
      rejectSegment('REPRESENTATION_INVALID');
    }
    if (requireCanonical &&
        !sameBytes(bytes, encodeC1(value, maxDepth: maxDepth))) {
      rejectSegment('CANONICAL_INVALID');
    }
    // B03 decode completion: begin.
    completed = true;
    LogicalCost.observe(LogicalCostOperation.c1,
        LogicalCostMetric.completedBytes, bytes.length);
    // B03 decode completion: end.
    return value;
  } on FormatException {
    rejectSegment('REPRESENTATION_INVALID');
    // B03 decode failure: begin.
  } finally {
    if (!completed) {
      LogicalCost.observe(
          LogicalCostOperation.c1, LogicalCostMetric.failedCalls, 1);
      LogicalCost.observe(LogicalCostOperation.c1,
          LogicalCostMetric.failedSubmittedBytes, bytes.length);
    }
    // B03 decode failure: end.
  }
}

String objectHash(String kind, List<int> bytes) {
  if (!const {
    'row',
    'snapshot-leaf',
    'snapshot-node',
    'raw-root',
    'hot',
    'control',
    'index-empty',
    'index-leaf',
    'index-node',
    'index-root',
    'view',
    'fact-key'
  }.contains(kind)) {
    rejectSegment('HASH_DOMAIN_INVALID');
  }
  final result = _DigestSink();
  final sink = sha256.startChunkedConversion(result);
  // B03 hash observation: begin.
  final framing = ascii.encode('money-note.sync.v1/$kind');
  sink.add(framing);
  LogicalCost.observe(
      LogicalCostOperation.objectHash, LogicalCostMetric.calls, 1);
  LogicalCost.observe(LogicalCostOperation.objectHash,
      LogicalCostMetric.hashInputBytes, framing.length);
  // B03 hash observation: end.
  sink.add(const [0]);
  // B03 NUL observation: begin.
  LogicalCost.observe(
      LogicalCostOperation.objectHash, LogicalCostMetric.hashInputBytes, 1);
  // B03 NUL observation: end.
  sink.add(bytes);
  // B03 payload observation: begin.
  LogicalCost.observe(LogicalCostOperation.objectHash,
      LogicalCostMetric.hashInputBytes, bytes.length);
  // B03 payload observation: end.
  sink.close();
  return result.digest!.toString();
}

class _DigestSink implements Sink<Digest> {
  Digest? digest;
  @override
  void add(Digest value) {
    digest = value;
  }

  @override
  void close() {}
}

// Local bookkeeping checksum, deliberately not a protocol object identity.
// B03 checksum observation: begin.
String localChecksum(List<int> bytes) {
  final result = sha256.convert(bytes).toString();
  LogicalCost.observe(
      LogicalCostOperation.checksum, LogicalCostMetric.calls, 1);
  LogicalCost.observe(LogicalCostOperation.checksum,
      LogicalCostMetric.hashInputBytes, bytes.length);
  return result;
}
// B03 checksum observation: end.

class _Parser {
  _Parser(this.text, this.maxDepth);
  final String text;
  final int maxDepth;
  int position = 0;
  void space() {
    while (position < text.length && ' \t\n\r'.contains(text[position])) {
      position++;
    }
  }

  bool consume(String c) {
    space();
    if (position < text.length && text[position] == c) {
      position++;
      return true;
    }
    return false;
  }

  void need(String c) {
    if (!consume(c)) rejectSegment('REPRESENTATION_INVALID');
  }

  String string() {
    space();
    final start = position;
    need('"');
    while (position < text.length) {
      final c = text[position++];
      if (c == '\\') {
        position++;
        continue;
      }
      if (c == '"') {
        final value = jsonDecode(text.substring(start, position)) as String;
        scalarString(value);
        return value;
      }
    }
    rejectSegment('REPRESENTATION_INVALID');
  }

  Object? read(int depth) {
    if (depth > maxDepth) rejectSegment('LOCAL_PARSE_BUDGET');
    space();
    if (position == text.length) rejectSegment('REPRESENTATION_INVALID');
    if (text[position] == '"') return string();
    if (consume('{')) {
      final result = <String, dynamic>{};
      if (consume('}')) return result;
      do {
        final key = string();
        if (result.containsKey(key)) rejectSegment('DUPLICATE_KEY');
        need(':');
        result[key] = read(depth + 1);
      } while (consume(','));
      need('}');
      return result;
    }
    if (consume('[')) {
      final result = <dynamic>[];
      if (consume(']')) return result;
      do {
        result.add(read(depth + 1));
      } while (consume(','));
      need(']');
      return result;
    }
    for (final literal
        in {'true': true, 'false': false, 'null': null}.entries) {
      if (text.startsWith(literal.key, position)) {
        position += literal.key.length;
        return literal.value;
      }
    }
    final match =
        RegExp(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
            .matchAsPrefix(text, position);
    if (match == null) rejectSegment('REPRESENTATION_INVALID');
    final token = match[0]!;
    position = match.end;
    if (!token.contains(RegExp('[.eE]'))) {
      if (token.length > 20) rejectSegment('INTEGER_INVALID');
      final exact = BigInt.parse(token);
      if (exact < minSigned64 || exact > maxSigned64) {
        rejectSegment('INTEGER_INVALID');
      }
      return exact.toInt();
    }
    // Decimal lexical admission BEFORE binary64 conversion. No underflow repair.
    final parts = token.toLowerCase().split('e');
    final mantissa = parts[0].replaceAll('-', '').split('.');
    final exponentText = parts.length == 2 ? parts[1] : '0';
    if (exponentText.length > 6 || token.length > 128) {
      rejectSegment('LOCAL_PARSE_BUDGET');
    }
    final exponent = int.parse(exponentText) -
        (mantissa.length == 2 ? mantissa[1].length : 0);
    var coefficient = BigInt.parse(mantissa.join());
    if (coefficient != BigInt.zero) {
      if (exponent.abs() > 128) rejectSegment('NUMBER_INVALID');
      if (exponent < 0) {
        final divisor = BigInt.from(10).pow(-exponent);
        if (coefficient % divisor != BigInt.zero) {
          rejectSegment('NUMBER_INVALID');
        }
        coefficient ~/= divisor;
      } else {
        coefficient *= BigInt.from(10).pow(exponent);
      }
      if (coefficient > BigInt.from(maxExactMoney)) {
        rejectSegment('NUMBER_INVALID');
      }
    }
    final result = double.parse(token);
    if (!result.isFinite || BigInt.from(result.abs()) != coefficient) {
      rejectSegment('NUMBER_INVALID');
    }
    return result;
  }
}
