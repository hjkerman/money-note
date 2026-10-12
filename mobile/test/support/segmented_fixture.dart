import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

class ServerGolden {
  ServerGolden([String path = 'test/fixtures/segmented_server_golden.json'])
      : json =
            jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;
  final Map<String, dynamic> json;
  ObservationManifest get manifest => ObservationManifest.fromBytes(
      base64Decode(json['manifest_base64'] as String));
  CacheNamespace get cache =>
      CacheNamespace.forTarget('https://synthetic.invalid', manifest.target);
  List<Map<String, dynamic>> get objects =>
      (json['objects'] as List).cast<Map<String, dynamic>>();
  Map<String, dynamic> object(String kind) =>
      objects.singleWhere((o) => o['kind'] == kind);
  Uint8List bytes(String kind) =>
      base64Decode(object(kind)['data_base64'] as String);
  ObjectRef ref(String kind) => ObjectRef.parse(object(kind)['ref']);
  Map<String, dynamic> body(String kind) =>
      decodeC1(bytes(kind)) as Map<String, dynamic>;
}

ObjectRef refFor(String kind, List<int> bytes) => ObjectRef.parse(
    {'hash': objectHash(kind, bytes), 'bytes': '${bytes.length}'});

Map<String, dynamic> targetChanged(
    ServerGolden golden, void Function(Map<String, dynamic>) edit) {
  final target = golden.manifest.target.toJson();
  edit(target);
  target.remove('sync_root');
  target['sync_root'] = objectHash('view', encodeC1(target));
  return target;
}

const stageId = '12345678-1234-4234-8234-123456789012';
