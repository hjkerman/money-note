import 'dart:convert';
import 'dart:io';

import 'package:sqlite3/sqlite3.dart';

// 자체 데이터베이스를 열지 않는 HOST native library 환경 관찰이다.
void main() {
  stdout.writeln(
    jsonEncode({
      'dart_runtime': Platform.version,
      'native_sqlite': sqlite3.version.toString(),
      'platform': Platform.operatingSystem,
      'android_device_evidence': false,
    }),
  );
}
