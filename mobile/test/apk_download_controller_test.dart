import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/apk_download_controller.dart';
import 'package:money_note_mobile/src/apk_install_bridge.dart';

void main() {
  test('화면 위젯과 무관하게 APK 다운로드 상태를 유지한다', () async {
    final completion = Completer<void>();
    void Function(double? progress)? reportProgress;
    var downloadCalls = 0;
    final controller = ApkDownloadController(
      installedVersionReader: () async => const InstalledAppVersion(
        versionName: '2.3.3',
        versionCode: 13,
      ),
      downloadRunner: (api, {onProgress}) {
        downloadCalls += 1;
        reportProgress = onProgress;
        return completion.future;
      },
    );
    final api = MoneyNoteApiClient(baseUrl: 'https://example.invalid');

    await controller.initialize();
    final download = controller.download(api);
    await controller.download(api);
    reportProgress?.call(0.5);

    expect(controller.installedVersion?.label, '2.3.3 (13)');
    expect(controller.isDownloading, isTrue);
    expect(controller.progress, 0.5);
    expect(downloadCalls, 1);

    completion.complete();
    await download;

    expect(controller.isDownloading, isFalse);
    expect(controller.progress, isNull);
    controller.dispose();
  });
}
