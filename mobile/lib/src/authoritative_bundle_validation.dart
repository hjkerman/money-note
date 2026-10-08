import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'authoritative_bundle_contract.dart';
import 'money.dart';

Never invalidBundle(String path) =>
    throw FormatException('invalid authoritative bundle: $path');

// JSON escapes can decode to unpaired UTF-16 even when transport UTF-8 is
// valid. Check ALL values and keys, including generic JSON, before hashing or
// authority admission. Never encode/replace/normalize to repair a string.
void validateBundleUnicode(Object? value) {
  if (value is String) {
    for (var i = 0; i < value.length; i++) {
      final unit = value.codeUnitAt(i);
      if (unit < 0xd800 || unit > 0xdfff) continue;
      if (unit > 0xdbff || i + 1 == value.length) {
        invalidBundle('Unicode surrogate');
      }
      final next = value.codeUnitAt(++i);
      if (next < 0xdc00 || next > 0xdfff) {
        invalidBundle('Unicode surrogate');
      }
    }
  } else if (value is Map) {
    for (final entry in value.entries) {
      validateBundleUnicode(entry.key);
      validateBundleUnicode(entry.value);
    }
  } else if (value is List) {
    for (final item in value) {
      validateBundleUnicode(item);
    }
  }
}

void validateBundleShape(Object? value,
    [String spec = '@Bundle', String path = r'$']) {
  if (spec.startsWith('?')) {
    if (value == null) return;
    return validateBundleShape(value, spec.substring(1), path);
  }
  if (spec.startsWith('[')) {
    if (value is! List) invalidBundle(path);
    for (var i = 0; i < value.length; i++) {
      validateBundleShape(
          value[i], spec.substring(1, spec.length - 1), '$path[$i]');
    }
    return;
  }
  if (spec.startsWith('{')) {
    if (value is! Map<String, dynamic>) invalidBundle(path);
    for (final entry in value.entries) {
      validateBundleShape(entry.value, spec.substring(1, spec.length - 1),
          '$path.${entry.key}');
    }
    return;
  }
  if (spec.contains('|')) {
    for (final option in spec.split('|')) {
      try {
        validateBundleShape(value, option, path);
        return;
      } on FormatException {/* try the other tagged shape */}
    }
    invalidBundle(path);
  }
  if (spec.startsWith('@')) {
    if (value is! Map<String, dynamic>) invalidBundle(path);
    final fields = bundleWireShapes[spec.substring(1)]!;
    if (value.keys.any((key) => !fields.containsKey(key))) {
      invalidBundle('$path.unknown_field');
    }
    for (final entry in fields.entries) {
      if (!value.containsKey(entry.key)) {
        invalidBundle('$path.${entry.key}.absent');
      }
      validateBundleShape(value[entry.key], entry.value, '$path.${entry.key}');
    }
    return;
  }
  final valid = switch (spec) {
    's' => value is String,
    'b' => value is bool,
    'i' => value is int,
    'n' => value is num &&
        value.isFinite &&
        value.abs() <= maxMoney &&
        value == value.truncate(),
    'h' => value is String && RegExp(r'^[0-9a-f]{64}$').hasMatch(value),
    'd' => value is String && validBundleDate(value),
    'm' => value is String &&
        RegExp(r'^\d{4}-(0[1-9]|1[0-2])$').hasMatch(value) &&
        validBundleDate('$value-01'),
    'j' => value == null ||
        value is String ||
        value is bool ||
        value is num ||
        value is Map ||
        value is List,
    _ => spec.startsWith('v:')
        ? value is String &&
            bundleFiniteDomains[spec.substring(2)]!.contains(value)
        : spec.startsWith('c:')
            ? value is int && value.toString() == spec.substring(2)
            : spec.startsWith('e:') &&
                value is String &&
                spec.substring(2).split(',').contains(value),
  };
  if (!valid) invalidBundle(path);
}

bool validBundleDate(String value) {
  if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) return false;
  final parsed = DateTime.tryParse(value);
  return parsed != null &&
      parsed.year > 0 &&
      parsed.toIso8601String().substring(0, 10) == value;
}

bool validBundleTimestamp(Object? value) {
  if (value is! String ||
      !RegExp(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?$')
          .hasMatch(value)) {
    return false;
  }
  if (!validBundleDate(value.substring(0, 10)) ||
      int.parse(value.substring(11, 13)) > 23 ||
      int.parse(value.substring(14, 16)) > 59 ||
      int.parse(value.substring(17, 19)) > 59) {
    return false;
  }
  final offset = RegExp(r'[+-](\d{2}):(\d{2})$').firstMatch(value);
  return (offset == null ||
          (int.parse(offset[1]!) < 24 && int.parse(offset[2]!) < 60)) &&
      DateTime.tryParse(value) != null;
}

String bundleCanonicalJson(Object? value) => jsonEncode(_canonical(value));
Object? _canonical(Object? value) {
  if (value is Map<String, dynamic>) {
    final keys = value.keys.toList()..sort();
    return {for (final key in keys) key: _canonical(value[key])};
  }
  if (value is List) return value.map(_canonical).toList();
  return value;
}

String bundleHash(Object? value) =>
    sha256.convert(utf8.encode(bundleCanonicalJson(value))).toString();

class _JsonFrame {
  _JsonFrame(this.object, this.moneyMap);
  final bool object;
  final bool moneyMap;
  bool keyExpected = true;
  String? key;
  final keys = <String>{};
}

// Only the diagnostic bundle uses this preflight. It does not rewrite bytes,
// hashes or existing API parsing. Rate/opaque policy numbers are not money.
void validateBundleRawMoney(String text) {
  final moneyKeys = {
    for (final fields in bundleWireShapes.values)
      for (final entry in fields.entries)
        if (entry.value == 'n' || entry.value == '?n') entry.key
  };
  final stack = <_JsonFrame>[];
  final tokens =
      RegExp(r'"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[{}\[\]:,]');
  for (final match in tokens.allMatches(text)) {
    final token = match[0]!;
    final parent = stack.isEmpty ? null : stack.last;
    if (token == '{' || token == '[') {
      stack.add(_JsonFrame(token == '{', parent?.key == 'discounts'));
    } else if (token == '}' || token == ']') {
      if (stack.isEmpty) invalidBundle('JSON nesting');
      stack.removeLast();
    } else if (token == ',') {
      if (parent != null) {
        parent.keyExpected = true;
        parent.key = null;
      }
    } else if (token == ':') {
      if (parent != null) parent.keyExpected = false;
    } else if (token.startsWith('"')) {
      if (parent != null && parent.object && parent.keyExpected) {
        final key = jsonDecode(token) as String;
        if (!parent.keys.add(key)) invalidBundle('duplicate JSON key');
        parent.key = key;
      }
    } else if (parent != null &&
        (parent.moneyMap || moneyKeys.contains(parent.key))) {
      _exactRawMoney(token);
    }
  }
}

void _exactRawMoney(String token) {
  final m =
      RegExp(r'^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$').firstMatch(token)!;
  var digits = '${m[2]}${m[3] ?? ''}'.replaceFirst(RegExp(r'^0+'), '');
  if (digits.isEmpty) return;
  final exponent = int.tryParse(m[4] ?? '0');
  if (exponent == null || exponent.abs() > token.length + 20) {
    invalidBundle('raw money exponent');
  }
  final shift = exponent - (m[3]?.length ?? 0);
  if (shift < 0) {
    if (-shift >= digits.length ||
        digits.substring(digits.length + shift).contains(RegExp(r'[1-9]'))) {
      invalidBundle('fractional raw money');
    }
    digits = digits.substring(0, digits.length + shift);
  } else {
    if (digits.length + shift > 16) invalidBundle('unsafe raw money');
    digits += '0' * shift;
  }
  if (digits.length > 16 || int.parse(digits) > maxMoney) {
    invalidBundle('unsafe raw money');
  }
}
