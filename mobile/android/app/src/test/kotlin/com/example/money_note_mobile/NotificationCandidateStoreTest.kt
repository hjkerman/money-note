package com.example.money_note_mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationCandidateStoreTest {
    @Test
    fun classifiesSupportedNotificationPackages() {
        assertEquals(
            NotificationSource.WOORI_CARD,
            NotificationSource.fromPackageName("com.wooricard.smartapp")
        )
        assertEquals(
            NotificationSource.HIGHWAY_TOLL,
            NotificationSource.fromPackageName("com.ex.hipass_app")
        )
        assertEquals(
            NotificationSource.MOBILE_TMONEY,
            NotificationSource.fromPackageName("com.lgt.tmoney")
        )
        assertEquals(null, NotificationSource.fromPackageName("com.example.other"))
    }

    @Test
    fun createsCandidatesOnlyForWooriCardNotifications() {
        assertTrue(NotificationSource.WOORI_CARD.createsCandidate)
        assertFalse(NotificationSource.HIGHWAY_TOLL.createsCandidate)
        assertFalse(NotificationSource.MOBILE_TMONEY.createsCandidate)
    }

    @Test
    fun extractsMerchantContainingWonCharacterFromMultilineApproval() {
        val raw = """
            승인내역
            [일시불.승인(9452)]06/18 15:44
            700원 / 누적:626,622원
            법원행정처
        """.trimIndent()

        assertEquals("법원행정처", NotificationCandidateStore.extractMerchant(raw))
    }

    @Test
    fun extractsMerchantFromExistingSingleLineApprovalFormat() {
        val raw = """
            승인내역
            [일시불.승인(9452)]06/14 17:08 5,000원 / 누적:542,899원
            사랑방
        """.trimIndent()

        assertEquals("사랑방", NotificationCandidateStore.extractMerchant(raw))
    }

    @Test
    fun doesNotTreatStandaloneAmountLineAsMerchant() {
        val raw = """
            승인내역
            [일시불.승인(9452)]06/18 15:44
            700원
            수원지방법원
        """.trimIndent()

        assertEquals("수원지방법원", NotificationCandidateStore.extractMerchant(raw))
    }

    @Test
    fun ignoresLumpSumCancellationAsApprovalCandidate() {
        val raw = """
            승인내역
            [일시불.취소(9452)]07/05 11:22
            5,000원 / 누적:100,000원
            취소가맹점
        """.trimIndent()

        assertFalse(
            NotificationCandidateStore.isApprovalNotificationCandidate(
                title = "승인내역",
                text = "[일시불.취소(9452)]07/05 11:22\n5,000원 / 누적:100,000원\n취소가맹점",
                bigText = raw,
                raw = raw
            )
        )
    }

    @Test
    fun keepsLumpSumApprovalAsApprovalCandidate() {
        val raw = """
            승인내역
            [일시불.승인(9452)]07/05 11:22
            5,000원 / 누적:100,000원
            승인가맹점
        """.trimIndent()

        assertTrue(
            NotificationCandidateStore.isApprovalNotificationCandidate(
                title = "승인내역",
                text = "[일시불.승인(9452)]07/05 11:22\n5,000원 / 누적:100,000원\n승인가맹점",
                bigText = raw,
                raw = raw
            )
        )
    }
}
