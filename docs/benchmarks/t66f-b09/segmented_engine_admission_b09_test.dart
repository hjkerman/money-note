import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'support/segmented_fixture.dart';
void main() {
 test('B08 source manifest mutation remains an unknown exact engine', () {
  final v=jsonDecode(File('../docs/benchmarks/t66f-b09/B08-mutation-witness.json').readAsStringSync()) as Map;
  final context=FinancialContext.parse({'evaluation_date':'2026-10-05','timezone_offset_minutes':540,'financial_engine':v['mutated_engine']});
  expect(()=>const ReleaseContract().verify(ServerGolden().manifest.target.versions,context),throwsA(isA<SegmentedException>().having((e)=>e.code,'code','UNSUPPORTED_CONTRACT')));
 });
}
