package com.example.money_note_mobile

import org.junit.Assert.assertEquals
import org.junit.Test

class NotificationCandidateStoreTest {
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
}
