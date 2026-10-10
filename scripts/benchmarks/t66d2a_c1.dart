// Independent formatter only. NOT a mobile parser or production admission path.
import 'dart:convert';
import 'dart:io';

String quoted(String value) {
  final result = StringBuffer('"');
  final units = value.codeUnits;
  for (var i = 0; i < units.length; i++) {
    final c = units[i];
    if (c >= 0xd800 && c <= 0xdbff) {
      if (++i >= units.length || units[i] < 0xdc00 || units[i] > 0xdfff) {
        throw const FormatException('REJECT_UNICODE');
      }
      result.writeCharCode(c);
      result.writeCharCode(units[i]);
    } else if (c >= 0xdc00 && c <= 0xdfff) {
      throw const FormatException('REJECT_UNICODE');
    } else {
      const escapes = {
        34: r'\"',
        92: r'\\',
        8: r'\b',
        12: r'\f',
        10: r'\n',
        13: r'\r',
        9: r'\t',
      };
      if (escapes.containsKey(c)) {
        result.write(escapes[c]);
      } else if (c < 32) {
        result.write(r'\u' + c.toRadixString(16).padLeft(4, '0'));
      } else {
        result.writeCharCode(c);
      }
    }
  }
  result.write('"');
  return result.toString();
}

int scalarOrder(String a, String b) {
  final x = a.runes.toList(), y = b.runes.toList();
  for (var i = 0; i < x.length && i < y.length; i++) {
    if (x[i] != y[i]) return x[i].compareTo(y[i]);
  }
  return x.length.compareTo(y.length);
}

String c1(dynamic value) {
  if (value == null) return 'null';
  if (value is bool || value is int) return value.toString();
  if (value is double) {
    if (!value.isFinite ||
        value.abs() > 9007199254740991 ||
        value != value.truncateToDouble()) {
      throw const FormatException('REJECT_NUMBER');
    }
    return value.toStringAsFixed(1);
  }
  if (value is String) return quoted(value);
  if (value is List) return '[${value.map(c1).join(',')}]';
  if (value is Map<String, dynamic>) {
    final keys = value.keys.toList()..sort(scalarOrder);
    return '{${keys.map((k) => '${quoted(k)}:${c1(value[k])}').join(',')}}';
  }
  throw const FormatException('REJECT_TYPE');
}

Future<void> main() async {
  final input = jsonDecode(await stdin.transform(utf8.decoder).join()) as List;
  final output = <dynamic>[];
  for (final raw in input) {
    try {
      output.add(base64Encode(utf8.encode(c1(jsonDecode(raw as String)))));
    } on FormatException catch (error) {
      output.add({'error': error.message});
    }
  }
  stdout.write(jsonEncode(output));
}
