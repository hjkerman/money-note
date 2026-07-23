package com.example.money_note_mobile

internal enum class NotificationSource(
    val wireName: String,
    val packageName: String,
    val logFileName: String,
    val debugTitle: String,
    val createsCandidate: Boolean
) {
    WOORI_CARD(
        wireName = "woori_card",
        packageName = "com.wooricard.smartapp",
        logFileName = "woori_notification_logs.json",
        debugTitle = "Woori Card",
        createsCandidate = true
    ),
    HIGHWAY_TOLL(
        wireName = "highway_toll",
        packageName = "com.ex.hipass_app",
        logFileName = "highway_toll_notification_logs.json",
        debugTitle = "Highway Toll Plus",
        createsCandidate = false
    ),
    MOBILE_TMONEY(
        wireName = "mobile_tmoney",
        packageName = "com.lgt.tmoney",
        logFileName = "mobile_tmoney_notification_logs.json",
        debugTitle = "Mobile Tmoney",
        createsCandidate = false
    );

    companion object {
        fun fromPackageName(packageName: String): NotificationSource? =
            entries.firstOrNull { it.packageName == packageName }

        fun fromWireName(wireName: String): NotificationSource? =
            entries.firstOrNull { it.wireName == wireName }
    }
}
