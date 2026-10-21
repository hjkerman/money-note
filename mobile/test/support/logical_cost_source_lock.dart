import 'dart:convert';

import 'package:crypto/crypto.dart';

// Approval is limited to these exact reviewed revisions, not arbitrary markers.
String restoreReviewedB03Source(String path, String source, Map review) {
  final file = (review['files'] as Map)[path] as Map;
  String hash(String value) => sha256.convert(utf8.encode(value)).toString();
  if (hash(source) != file['reviewed_sha256']) {
    throw StateError(
        'B03 current source is not the exact reviewed revision: $path');
  }
  var original = source;
  for (final replacement in file['exact_replacements'] as List) {
    final current = replacement['reviewed'] as String;
    if (current.allMatches(original).length != 1) {
      throw StateError('B03 exact replacement not unique: $path');
    }
    original =
        original.replaceFirst(current, replacement['historical'] as String);
  }
  if (hash(original) != file['historical_sha256']) {
    throw StateError('B03 did not restore the exact historical source: $path');
  }
  return original;
}
