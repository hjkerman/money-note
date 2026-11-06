import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
void main() {
  test('현재 exact guard는 원 baseline을 허용하고 미승인 B05를 거부한다', () {
    final artifact=jsonDecode(File(const String.fromEnvironment('B05_PROPOSED_BUNDLE')).readAsStringSync()) as Map<String,dynamic>;
    final versions=SyncVersions.parse(artifact['versions']);
    FinancialContext context(String hash)=>FinancialContext.parse({'evaluation_date':'2026-10-05','timezone_offset_minutes':540,'financial_engine':hash});
    const ReleaseContract().verify(versions,context('7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'));
    expect(()=>const ReleaseContract().verify(versions,context(artifact['artifacts']['financial_engine']['sha256'] as String)),throwsA(isA<SegmentedException>().having((e)=>e.code,'code','UNSUPPORTED_CONTRACT')));
  });
}
