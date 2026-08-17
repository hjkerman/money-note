package com.example.money_note_mobile

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.MessageDigest

class ApkInstallBridge(
    private val activity: Activity,
    messenger: BinaryMessenger,
) {
    companion object {
        private const val CHANNEL_NAME = "money_note/apk_install"
        private const val UPDATE_DIRECTORY = "apk-updates"
        private const val APK_MIME_TYPE = "application/vnd.android.package-archive"
    }

    private val channel = MethodChannel(messenger, CHANNEL_NAME)
    private var installerFile: File? = null
    private var waitingForInstallerReturn = false

    init {
        cleanupUpdates()
        channel.setMethodCallHandler { call, result ->
            when (call.method) {
                "canInstallPackages" -> result.success(canInstallPackages())
                "openInstallSettings" -> openInstallSettings(result)
                "installApk" -> installApk(
                    call.argument<String>("path").orEmpty(),
                    result,
                )
                else -> result.notImplemented()
            }
        }
    }

    fun dispose() {
        channel.setMethodCallHandler(null)
    }

    fun onHostResumed() {
        if (!waitingForInstallerReturn) return
        installerFile?.delete()
        installerFile = null
        waitingForInstallerReturn = false
    }

    private fun canInstallPackages(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.O ||
            activity.packageManager.canRequestPackageInstalls()
    }

    private fun openInstallSettings(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            result.success(true)
            return
        }
        try {
            activity.startActivity(
                Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${activity.packageName}"),
                ),
            )
            result.success(true)
        } catch (error: Exception) {
            result.error(
                "install_settings_failed",
                error.message ?: "APK 설치 권한 화면을 열 수 없습니다.",
                null,
            )
        }
    }

    private fun installApk(path: String, result: MethodChannel.Result) {
        if (!canInstallPackages()) {
            result.error("install_permission_required", "이 출처의 앱 설치 허용이 필요합니다.", null)
            return
        }
        val file = File(path)
        if (!isAllowedUpdateFile(file)) {
            result.error("invalid_apk_path", "허용되지 않은 APK 파일 경로입니다.", null)
            return
        }
        if (!file.isFile || file.length() <= 0L) {
            result.error("apk_missing", "다운로드한 APK 파일을 찾을 수 없습니다.", null)
            return
        }
        val validationError = validateApk(file)
        if (validationError != null) {
            result.error("apk_validation_failed", validationError, null)
            return
        }

        val authority = "${activity.packageName}.shared_files"
        val uri = FileProvider.getUriForFile(activity, authority, file)
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, APK_MIME_TYPE)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            installerFile = file
            waitingForInstallerReturn = true
            activity.startActivity(intent)
            result.success(true)
        } catch (_: ActivityNotFoundException) {
            installerFile = null
            waitingForInstallerReturn = false
            result.error("installer_not_found", "Android APK 설치 화면을 찾을 수 없습니다.", null)
        } catch (error: Exception) {
            installerFile = null
            waitingForInstallerReturn = false
            result.error("install_failed", error.message ?: "APK 설치 화면을 열 수 없습니다.", null)
        }
    }

    private fun isAllowedUpdateFile(file: File): Boolean {
        val allowedRoot = File(activity.cacheDir, UPDATE_DIRECTORY).canonicalFile
        val candidate = file.canonicalFile
        return candidate.parentFile == allowedRoot && candidate.extension.equals("apk", ignoreCase = true)
    }

    private fun validateApk(file: File): String? {
        val packageManager = activity.packageManager
        val archive = packageManager.getPackageArchiveInfo(file.path, signingFlags())
            ?: return "다운로드한 파일은 올바른 APK가 아닙니다."
        if (archive.packageName != activity.packageName) {
            return "다운로드한 APK는 Money-Note 설치 파일이 아닙니다."
        }
        val installed = packageManager.getPackageInfo(activity.packageName, signingFlags())
        val archiveSignatures = signatureDigests(archive)
        val installedSignatures = signatureDigests(installed)
        if (archiveSignatures.isEmpty() || archiveSignatures != installedSignatures) {
            return "APK 서명이 현재 Money-Note와 일치하지 않습니다."
        }
        return null
    }

    private fun signingFlags(): Int {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            @Suppress("DEPRECATION")
            PackageManager.GET_SIGNATURES
        }
    }

    private fun signatureDigests(info: PackageInfo): Set<String> {
        val signatures = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val signingInfo = info.signingInfo ?: return emptySet()
            if (signingInfo.hasMultipleSigners()) {
                signingInfo.apkContentsSigners
            } else {
                signingInfo.signingCertificateHistory
            }
        } else {
            @Suppress("DEPRECATION")
            info.signatures
        }
        return signatures.orEmpty().map { signature ->
            MessageDigest.getInstance("SHA-256")
                .digest(signature.toByteArray())
                .joinToString("") { byte -> "%02x".format(byte) }
        }.toSet()
    }

    private fun cleanupUpdates() {
        File(activity.cacheDir, UPDATE_DIRECTORY).listFiles()?.forEach(File::delete)
    }
}
