package com.example.money_note_mobile

import java.security.MessageDigest
import java.util.GregorianCalendar

data class ParsedHighwayToll(
    val entryDate: String?,
    val eventTime: String?,
    val amount: Int?,
    val route: String?
)

data class HighwayTollParseResult(
    val isTollCandidate: Boolean,
    val status: String,
    val reason: String,
    val toll: ParsedHighwayToll
) {
    val createsCandidate: Boolean
        get() = isTollCandidate && toll.entryDate != null && status in setOf("parsed", "partial")
}

/**
 * 고속도로통행료+ 알림을 강한 표식별로 나눠 읽는다.
 *
 * 문장 전체 형식을 고정하지 않고 날짜·시각을 먼저 찾은 뒤, 그 뒤 구간에서만
 * 금액과 요금 확인 불가 표식을 찾는다. route는 그 표식 사이의 인덱스 구간이다.
 */
object HighwayTollNotificationParser {
    private val dateTimePattern = Regex(
        """(?<!\d)(\d{4})[./-](\d{1,2})[./-](\d{1,2})\s+""" +
            """(\d{1,2}):(\d{2})(?::(\d{2}))?(?!\d)"""
    )
    private val amountPattern = Regex("""(?<![0-9,])([0-9][0-9,]*)(?![0-9,])\s*원""")
    private val endpointQualifierPattern = Regex("""\((?:입구|출구)\)""")

    fun parse(record: RawNotificationRecord): HighwayTollParseResult = parse(
        title = record.title,
        text = record.text,
        bigText = record.bigText,
        rawText = record.rawText
    )

    internal fun parse(
        title: String,
        text: String,
        bigText: String,
        rawText: String
    ): HighwayTollParseResult {
        val empty = ParsedHighwayToll(null, null, null, null)
        if (!isTollNotificationCandidate(title, text, bigText, rawText)) {
            return HighwayTollParseResult(false, "ignored", "", empty)
        }

        val dateTime = dateTimePattern.find(rawText)
            ?: return HighwayTollParseResult(
                true,
                "failed",
                "필수 필드 누락: entry_date",
                empty
            )
        val entryDate = normalizedDate(dateTime)
            ?: return HighwayTollParseResult(
                true,
                "failed",
                "날짜·시각 형식 오류",
                empty
            )
        val eventTime = normalizedTime(dateTime)
        val afterDateTime = rawText.substring(dateTime.range.last + 1)
        val amountMatch = amountPattern.find(afterDateTime)
        val amount = amountMatch
            ?.groupValues
            ?.getOrNull(1)
            ?.let(::parseAmount)
        val unavailableMarker = unavailableMarkerStart(afterDateTime)
        val routeEnd = listOfNotNull(
            amountMatch?.range?.first,
            unavailableMarker
        ).minOrNull() ?: afterDateTime.length
        val route = normalizeRoute(afterDateTime.substring(0, routeEnd))

        if (amount != null) {
            return HighwayTollParseResult(
                true,
                "parsed",
                "",
                ParsedHighwayToll(entryDate, eventTime, amount, route)
            )
        }

        val reason = if (unavailableMarker != null) {
            "요금 확인 불가 - 금액 입력 필요"
        } else {
            "금액 누락 - 수동 입력 필요"
        }
        return HighwayTollParseResult(
            true,
            "partial",
            reason,
            ParsedHighwayToll(entryDate, eventTime, null, route)
        )
    }

    internal fun isTollNotificationCandidate(
        title: String,
        text: String,
        bigText: String,
        rawText: String
    ): Boolean {
        val body = normalizeWhitespace(listOf(title, text, bigText, rawText).joinToString(" "))
        if (body.isBlank()) return false

        val cardUsageNotice = listOf("카드", "내역", "알림").all(body::contains)
        val tollPassageNotice = body.contains("통과") &&
            (body.contains("유료도로") || body.contains("영업소"))
        return cardUsageNotice || tollPassageNotice
    }

    internal fun semanticCandidateId(parsed: ParsedHighwayToll): String {
        val value = listOf(
            NotificationSource.HIGHWAY_TOLL.wireName,
            parsed.entryDate.orEmpty(),
            parsed.eventTime.orEmpty(),
            parsed.route.orEmpty(),
            parsed.amount?.toString().orEmpty()
        ).joinToString("|")
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }.take(24)
    }

    private fun unavailableMarkerStart(value: String): Int? {
        val feeIndex = value.indexOf("요금")
        if (feeIndex < 0) return null
        val confirmIndex = value.indexOf("확인", startIndex = feeIndex)
        if (confirmIndex < 0) return null
        val negativeIndex = listOf("없", "불가", "어렵")
            .map { value.indexOf(it, startIndex = confirmIndex) }
            .filter { it >= 0 }
            .minOrNull()
            ?: return null

        val gateIndex = value.indexOf("입출구")
        return if (gateIndex in 0 until feeIndex && gateIndex < negativeIndex) gateIndex else feeIndex
    }

    private fun parseAmount(value: String): Int? {
        if (value.contains(',') && !Regex("""\d{1,3}(?:,\d{3})+""").matches(value)) {
            return null
        }
        return value.replace(",", "").toIntOrNull()
    }

    private fun normalizeRoute(value: String): String? {
        val normalized = normalizeWhitespace(value)
            .trim(' ', '-', ':', '/', '·')
            .replace(endpointQualifierPattern, "")
            .replace(Regex("""\s*-\s*"""), "-")
            .trim()
        if (normalized.isEmpty()) return null

        val endpoints = normalized.split('-', limit = 2).map(String::trim)
        return if (endpoints.size == 2 && endpoints[0] == endpoints[1]) {
            endpoints[0]
        } else {
            normalized
        }
    }

    private fun normalizedDate(match: MatchResult): String? {
        val year = match.groupValues[1].toIntOrNull() ?: return null
        val month = match.groupValues[2].toIntOrNull() ?: return null
        val day = match.groupValues[3].toIntOrNull() ?: return null
        val hour = match.groupValues[4].toIntOrNull() ?: return null
        val minute = match.groupValues[5].toIntOrNull() ?: return null
        val second = match.groupValues[6].ifEmpty { "0" }.toIntOrNull() ?: return null
        val calendar = GregorianCalendar().apply {
            isLenient = false
            clear()
            set(year, month - 1, day, hour, minute, second)
        }
        return try {
            calendar.time
            "%04d-%02d-%02d".format(year, month, day)
        } catch (_: IllegalArgumentException) {
            null
        }
    }

    private fun normalizedTime(match: MatchResult): String {
        val hour = match.groupValues[4].toInt()
        val minute = match.groupValues[5].toInt()
        val second = match.groupValues[6].ifEmpty { "0" }.toInt()
        return "%02d:%02d:%02d".format(hour, minute, second)
    }

    private fun normalizeWhitespace(value: String): String =
        value.replace(Regex("""\s+"""), " ").trim()
}
