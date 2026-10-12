// T6.6C data contracts. No HTTP, credential, financial computation or activation.
import 'dart:convert';
import 'dart:typed_data';

import 'c1.dart';

Map<String, dynamic> record(Object? value, Iterable<String> fields) {
  if (value is! Map<String, dynamic> ||
      value.length != fields.length ||
      !fields.every(value.containsKey)) {
    rejectSegment('SHAPE_INVALID');
  }
  return value;
}

String hashValue(Object? value) {
  if (value is! String || !RegExp(r'^[0-9a-f]{64}$').hasMatch(value)) {
    rejectSegment('HASH_INVALID');
  }
  return value;
}

String uuidValue(Object? value) {
  if (value is! String ||
      !RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
          .hasMatch(value)) {
    rejectSegment('UUID_INVALID');
  }
  return value;
}

String u64(Object? value) {
  if (value is! String ||
      value.length > 19 ||
      !RegExp(r'^(0|[1-9][0-9]*)$').hasMatch(value) ||
      BigInt.parse(value) > maxSigned64) {
    rejectSegment('U64_INVALID');
  }
  return value;
}

bool validDate(Object? value) {
  if (value is! String ||
      !RegExp(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$').hasMatch(value)) {
    return false;
  }
  final date = DateTime.tryParse(value);
  return date != null &&
      date.year > 0 &&
      date.toIso8601String().substring(0, 10) == value;
}

DateTime wireTime(Object? value) {
  if (value is! String ||
      !RegExp(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$')
          .hasMatch(value) ||
      !validDate(value.substring(0, 10)) ||
      int.parse(value.substring(11, 13)) > 23 ||
      int.parse(value.substring(14, 16)) > 59 ||
      int.parse(value.substring(17, 19)) > 59) {
    rejectSegment('TIME_INVALID');
  }
  return DateTime.parse(value);
}

class SyncNamespace {
  SyncNamespace._(this.serverId, this.datasetId, this.epoch);
  factory SyncNamespace.parse(Object? value) {
    final v = record(value, ['server_id', 'dataset_id', 'epoch']);
    return SyncNamespace._(uuidValue(v['server_id']),
        uuidValue(v['dataset_id']), uuidValue(v['epoch']));
  }
  final String serverId, datasetId, epoch;
  Map<String, dynamic> toJson() =>
      {'server_id': serverId, 'dataset_id': datasetId, 'epoch': epoch};
  bool matches(SyncNamespace other) =>
      sameBytes(encodeC1(toJson()), encodeC1(other.toJson()));
}

class ObjectRef {
  ObjectRef._(this.hash, this.bytes);
  factory ObjectRef.parse(Object? value) {
    final v = record(value, ['hash', 'bytes']);
    return ObjectRef._(hashValue(v['hash']), u64(v['bytes']));
  }
  final String hash, bytes; // U64 is never a JSON number.
  int get byteLength => int.parse(bytes);
  Map<String, dynamic> toJson() => {'hash': hash, 'bytes': bytes};
  bool matches(ObjectRef other) => hash == other.hash && bytes == other.bytes;
}

class SyncVersions {
  SyncVersions._(this._raw);
  factory SyncVersions.parse(Object? value) {
    final v = record(value, [
      'sync',
      'canon',
      'structural',
      'raw_schema',
      'snapshot',
      'recurring_ownership',
      'projection_schema',
      'policy_registry'
    ]);
    for (final e in {
      'sync': 1,
      'canon': 1,
      'structural': 1,
      'snapshot': 7,
      'recurring_ownership': 1
    }.entries) {
      if (v[e.key] is! int || v[e.key] != e.value) {
        rejectSegment('UNSUPPORTED_CONTRACT');
      }
    }
    for (final name in ['raw_schema', 'projection_schema', 'policy_registry']) {
      hashValue(v[name]);
    }
    return SyncVersions._(encodeC1(v));
  }
  final Uint8List _raw;
  Map<String, dynamic> toJson() => decodeC1(_raw) as Map<String, dynamic>;
  String get rawSchema => toJson()['raw_schema'] as String;
  String get projectionSchema => toJson()['projection_schema'] as String;
}

class FinancialContext {
  FinancialContext._(this.date, this.offsetMinutes, this.engine);
  factory FinancialContext.parse(Object? value) {
    final v = record(value,
        ['evaluation_date', 'timezone_offset_minutes', 'financial_engine']);
    if (!validDate(v['evaluation_date']) ||
        v['timezone_offset_minutes'] is! int ||
        (v['timezone_offset_minutes'] as int).abs() > 1439) {
      rejectSegment('CONTEXT_INVALID');
    }
    return FinancialContext._(v['evaluation_date'] as String,
        v['timezone_offset_minutes'] as int, hashValue(v['financial_engine']));
  }
  final String date, engine;
  final int offsetMinutes;
  Map<String, dynamic> toJson() => {
        'evaluation_date': date,
        'timezone_offset_minutes': offsetMinutes,
        'financial_engine': engine
      };
}

// Exact isolated D3b release artifacts, reviewed at the E1 starting commit.
// Not a production capability advertisement or a downloaded compatibility rule.
class ReleaseContract {
  const ReleaseContract();
  static const rawSchema =
      'b948a0e33fc0abb6957af76beac643ac7131d2fcac3ab53265c02d16783f953e';
  static const projectionSchema =
      '89e2bd7bf3f1683ddff95a0b33b1e9ff08ff19d5a001f4007c40ed4c6c5b3437';
  static const policyRegistry =
      '18be2d36483467e9250d568bcbfed6458c15a364fa99896eb1b8daad05db043d';
  static const financialEngine =
      'f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d';
  void verify(SyncVersions versions, FinancialContext context) {
    final v = versions.toJson();
    if (v['raw_schema'] != rawSchema ||
        v['projection_schema'] != projectionSchema ||
        v['policy_registry'] != policyRegistry ||
        context.engine != financialEngine) {
      rejectSegment('UNSUPPORTED_CONTRACT');
    }
  }
}

class SyncTarget {
  SyncTarget._(this._raw, this.ns, this.principalId, this.versions,
      this.revision, this.context, this.roots, this.syncRoot);
  factory SyncTarget.parse(Object? value) {
    final v = record(value, [
      'ns',
      'principal_id',
      'versions',
      'revision',
      'context',
      'raw_ref',
      'index_ref',
      'hot_ref',
      'control_ref',
      'sync_root'
    ]);
    final principal = v['principal_id'];
    if (principal is! int || principal <= 0) rejectSegment('PRINCIPAL_INVALID');
    final ns = SyncNamespace.parse(v['ns']);
    final versions = SyncVersions.parse(v['versions']);
    final context = FinancialContext.parse(v['context']);
    const ReleaseContract().verify(versions, context);
    final roots = {
      for (final role in ['raw', 'index', 'hot', 'control'])
        role: ObjectRef.parse(v['${role}_ref'])
    };
    final digest = hashValue(v['sync_root']);
    final preimage = Map<String, dynamic>.from(v)..remove('sync_root');
    if (objectHash('view', encodeC1(preimage)) != digest) {
      rejectSegment('TARGET_HASH_INVALID');
    }
    return SyncTarget._(encodeC1(v), ns, principal, versions,
        u64(v['revision']), context, Map.unmodifiable(roots), digest);
  }
  final Uint8List _raw;
  final SyncNamespace ns;
  final int principalId;
  final SyncVersions versions;
  final String revision, syncRoot;
  final FinancialContext context;
  final Map<String, ObjectRef> roots;
  Map<String, dynamic> toJson() => decodeC1(_raw) as Map<String, dynamic>;
}

class ObjectChunk {
  ObjectChunk._(this.ref, this.offset, this._bytes);
  factory ObjectChunk.parse(Object? value) {
    final v = record(value, ['ref', 'offset', 'length', 'data_base64']);
    final ref = ObjectRef.parse(v['ref']);
    final offset = u64(v['offset']);
    final length = v['length'];
    final data = v['data_base64'];
    if (length is! int ||
        length < 1 ||
        length > 1048576 ||
        data is! String ||
        data.length != 4 * ((length + 2) ~/ 3) ||
        BigInt.parse(offset) + BigInt.from(length) > BigInt.parse(ref.bytes)) {
      rejectSegment('CHUNK_INVALID');
    }
    try {
      final decoded = base64.decode(data);
      if (decoded.length != length || base64.encode(decoded) != data) {
        rejectSegment('CHUNK_INVALID');
      }
      return ObjectChunk._(ref, offset, decoded);
    } on FormatException {
      rejectSegment('CHUNK_INVALID');
    }
  }
  final ObjectRef ref;
  final String offset;
  final Uint8List _bytes;
  Uint8List get bytes => Uint8List.fromList(_bytes);
}

class ObservationManifest {
  ObservationManifest._(this._raw, this.id, this.requestId, this.target,
      this.validatedAt, this.expiresAt);
  factory ObservationManifest.fromBytes(List<int> raw,
      {int maxBytes = 8 * 1024 * 1024}) {
    if (raw.length > maxBytes) rejectSegment('LOCAL_METADATA_BUDGET');
    final v = record(decodeC1(raw, requireCanonical: false), [
      'protocol',
      'request_id',
      'status',
      'observation_id',
      'validated_at',
      'expires_at',
      'base_sync_root',
      'change_kind',
      'target',
      'inline_objects'
    ]);
    if (v['protocol'] is! int ||
        v['protocol'] != 1 ||
        v['status'] != 'available' ||
        !['initial', 'unchanged', 'context', 'raw']
            .contains(v['change_kind'])) {
      rejectSegment('MANIFEST_INVALID');
    }
    final start = wireTime(v['validated_at']), end = wireTime(v['expires_at']);
    if (!end.isAfter(start) || end.difference(start).inSeconds > 900) {
      rejectSegment('LEASE_INVALID');
    }
    if (v['base_sync_root'] != null) hashValue(v['base_sync_root']);
    if ((v['change_kind'] == 'initial') != (v['base_sync_root'] == null)) {
      rejectSegment('MANIFEST_INVALID');
    }
    if (v['inline_objects'] is! List) rejectSegment('MANIFEST_INVALID');
    final inline = v['inline_objects'] as List;
    if (inline.length > 64) rejectSegment('CHUNK_INVALID');
    var count = 0;
    for (final item in inline) {
      count += ObjectChunk.parse(item).bytes.length;
      if (count > 1048576) rejectSegment('CHUNK_INVALID');
    }
    return ObservationManifest._(encodeC1(v), uuidValue(v['observation_id']),
        uuidValue(v['request_id']), SyncTarget.parse(v['target']), start, end);
  }
  final Uint8List _raw;
  final String id, requestId;
  final SyncTarget target;
  final DateTime validatedAt, expiresAt;
  Uint8List get bytes => Uint8List.fromList(_raw);
  // Lease metadata only. This does not authenticate or authorize a request.
  bool leaseElapsedAt(DateTime time) => !time.toUtc().isBefore(expiresAt);
}

class CacheNamespace {
  CacheNamespace._(
      this.origin, this.ns, this.principalId, this.versions, this.key);
  factory CacheNamespace.forTarget(String origin, SyncTarget target) {
    final uri = Uri.tryParse(origin);
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.path.isNotEmpty ||
        uri.origin != origin) {
      rejectSegment('ORIGIN_INVALID');
    }
    return CacheNamespace._(
        origin,
        target.ns,
        target.principalId,
        target.versions,
        localChecksum(encodeC1({
          'origin': origin,
          'ns': target.ns.toJson(),
          'principal_id': target.principalId,
          'versions': target.versions.toJson()
        })));
  }
  final String origin, key;
  final SyncNamespace ns;
  final int principalId;
  final SyncVersions versions;
  void verifyTarget(SyncTarget target) {
    if (!ns.matches(target.ns) ||
        principalId != target.principalId ||
        !sameBytes(
            encodeC1(versions.toJson()), encodeC1(target.versions.toJson()))) {
      rejectSegment('CACHE_CONTEXT_MISMATCH');
    }
  }
}
