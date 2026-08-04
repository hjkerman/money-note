package com.example.money_note_mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HighwayTollNotificationParserTest {
    @Test
    fun parsesCardUsageNoticeByIndependentMarkers() {
        val result = parse(
            title = "하이패스카드 사용내역 알림",
            body = "2026/08/04 16:53:57 미지정(입구)-인천 450원"
        )

        assertTrue(result.createsCandidate)
        assertEquals("parsed", result.status)
        assertEquals("2026-08-04", result.toll.entryDate)
        assertEquals("16:53:57", result.toll.eventTime)
        assertEquals("미지정-인천", result.toll.route)
        assertEquals(450, result.toll.amount)
    }

    @Test
    fun parsesPrivateRoadNoticeAndCollapsesSameEndpoints() {
        val result = parse(
            title = "민자/지자체 유료도로 영업소를 통과하였습니다.",
            body = "서울터널\n2026/08/04 16:44:59 신월여의지하도로-신월여의지하도로 1,350원"
        )

        assertEquals("parsed", result.status)
        assertEquals("신월여의지하도로", result.toll.route)
        assertEquals(1350, result.toll.amount)
    }

    @Test
    fun createsPartialCandidateWhenFeeCannotBeConfirmed() {
        val result = parse(
            title = "민자 유료도로 영업소 통과 알림",
            body = "2026/08/04 14:33:41 미지정(입구)-고양 " +
                "입출구 확인이 어려워 요금정보를 확인할 수 없습니다."
        )

        assertTrue(result.createsCandidate)
        assertEquals("partial", result.status)
        assertEquals("요금 확인 불가 - 금액 입력 필요", result.reason)
        assertEquals("미지정-고양", result.toll.route)
        assertNull(result.toll.amount)
    }

    @Test
    fun keepsDateOnlyNotificationAsPartialCandidate() {
        val result = parse(
            title = "카드 내역 알림",
            body = "2026-08-04 14:16 미지정(입구)-인천"
        )

        assertTrue(result.createsCandidate)
        assertEquals("partial", result.status)
        assertEquals("금액 누락 - 수동 입력 필요", result.reason)
        assertEquals("미지정-인천", result.toll.route)
    }

    @Test
    fun searchesAmountOnlyAfterTheDiscoveredDateTime() {
        val result = parse(
            title = "450원 카드 내역 알림",
            body = "2026/08/04 14:16:21 미지정(입구)-인천"
        )

        assertEquals("partial", result.status)
        assertNull(result.toll.amount)
    }

    @Test
    fun malformedAmountIsNotSilentlyConverted() {
        val result = parse(
            title = "하이패스 카드 내역 알림",
            body = "2026/08/04 14:16:21 미지정(입구)-인천 1,,350원"
        )

        assertEquals("partial", result.status)
        assertNull(result.toll.amount)
    }

    @Test
    fun doesNotUseLooseConfirmationWordsAsUnavailableMarker() {
        val result = parse(
            title = "하이패스 카드 내역 알림",
            body = "2026/08/04 14:16:21 미지정-인천 확인할 정보 없음"
        )

        assertEquals("금액 누락 - 수동 입력 필요", result.reason)
    }

    @Test
    fun relevantNoticeWithoutDateIsFailed() {
        val result = parse(
            title = "하이패스 카드 내역 알림",
            body = "미지정-인천 450원"
        )

        assertFalse(result.createsCandidate)
        assertEquals("failed", result.status)
        assertEquals("필수 필드 누락: entry_date", result.reason)
    }

    @Test
    fun emptyAggregateNotificationIsIgnored() {
        val result = parse(title = "", body = "")

        assertFalse(result.isTollCandidate)
        assertEquals("ignored", result.status)
    }

    @Test
    fun semanticIdIsStableForTheSameTollEvent() {
        val parsed = ParsedHighwayToll(
            entryDate = "2026-08-04",
            eventTime = "16:53:57",
            amount = 450,
            route = "미지정-인천"
        )

        assertEquals(
            HighwayTollNotificationParser.semanticCandidateId(parsed),
            HighwayTollNotificationParser.semanticCandidateId(parsed)
        )
    }

    private fun parse(title: String, body: String): HighwayTollParseResult =
        HighwayTollNotificationParser.parse(
            title = title,
            text = body,
            bigText = body,
            rawText = listOf(title, body).filter(String::isNotBlank).joinToString("\n")
        )
}
