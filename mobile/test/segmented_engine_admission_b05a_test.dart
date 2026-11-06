import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'support/segmented_fixture.dart';
void main() {
  final golden=ServerGolden();
  FinancialContext context(String engine)=>FinancialContext.parse({'evaluation_date':'2026-10-05','timezone_offset_minutes':540,'financial_engine':engine});
  const accepted=[
    'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3',
    '7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c',
    'afe26b70856b5a3fa06477641d91e8e1784e9184906281843f0a39a9c99cbdf5',
    'f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d',
  ];
  for(final engine in accepted) {
    test('명시 승인된 exact engine 유지 $engine',()=>const ReleaseContract().verify(golden.manifest.target.versions,context(engine)));
  }
  final witness=jsonDecode(File('../docs/benchmarks/t66f-b05a/mutation-witness.json').readAsStringSync()) as Map;
  for(final engine in ['0'*64,'a${accepted.first.substring(1)}','d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae',witness['mutated_source_engine_sha'] as String]) {
    test('미승인·변조·payload hash를 engine으로 거부 $engine',()=>expect(()=>const ReleaseContract().verify(golden.manifest.target.versions,context(engine)),throwsA(isA<SegmentedException>().having((e)=>e.code,'code','UNSUPPORTED_CONTRACT'))));
  }
  test('현재 artifact는 선언된 정확한 source engine을 포함한다',(){
    final bundle=jsonDecode(File('assets/segmented/isolated-release-artifacts.json').readAsStringSync()) as Map;
    final engine=bundle['artifacts']['financial_engine'] as Map;
    expect(sha256.convert(base64Decode(engine['data_base64'] as String)).toString(),accepted.first);
    expect(engine['sha256'],accepted.first);
    expect(ReleaseContract.financialEngine,accepted.first);
  });
}
