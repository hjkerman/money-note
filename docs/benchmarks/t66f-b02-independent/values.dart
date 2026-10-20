// 재계산 없이 backend authoritative 값의 canonical digest만 비교한다.
import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

class DigestSink implements Sink<Digest> {
  Digest? value;
  @override
  void add(Digest x) => value = x;
  @override
  void close() {}
}

Map<String, dynamic> independentReadDigests(AcceptedReadView view) {
  final out = <String, dynamic>{};
  for (final table in segmentedTables) {
    final sink = DigestSink();
    final hasher = sha256.startChunkedConversion(sink);
    TreeKey? after;
    var count = 0;
    while (true) {
      final page = view.rows(table, after: after);
      for (final row in page) {
        hasher.add(ascii.encode('${sha256.convert(encodeC1(row))}\n'));
        count++;
      }
      if (page.length < 256) break;
      final key = page.last[primaryColumn(table)];
      after = TreeKey.parse([key is int ? 'i' : 't', '$key'], table);
    }
    hasher.close();
    out[table] = {'count': count, 'sha256': '${sink.value}'};
  }
  return out;
}
