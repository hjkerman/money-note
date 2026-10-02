// Exact integer won transport/input validation, not a client financial engine.
const maxMoney = 9007199254740991;
const _moneyFields = {
  'amount_value',
  'aux_amount_value',
  'actual_amount',
  'discount_override_amount',
  'total_amount',
  'discount_amount',
  'automatic_discount_amount',
  'effective_discount_amount',
  'effective_amount_value',
  'confirmed_amount_value',
  'confirmed_effective_discount_amount',
  'confirmed_effective_amount_value',
  'original_amount',
  'immediate_paid_amount',
  'remaining_amount',
  'original_total',
  'immediate_paid_total',
  'discount_total',
  'recorded_remaining_total',
  'effective_remaining_total',
  'primary_income_total',
  'scheduled_income',
  'cash_flow_balance',
  'remaining_liquidity',
  'current_month_spendable',
  'current_spending_total',
  'current_discount_total',
  'card_total',
  'planned_recurring_total',
  'fixed_cash_total',
  'fixed_cash_processed_total',
  'transfer_or_deposit_total',
  'frozen_asset_total',
  'claim_original_total',
  'claim_net_total',
  'family_card_original_total',
  'family_card_net_total',
  'visible_cash_flow_total',
  'card_limit',
  'base_next_month_liquidity',
  'liquidity_status',
  'total',
  'minimum_total',
  'minimum_discount_total',
};

int exactMoney(Object? value) {
  num? amount;
  if (value is num) {
    amount = value;
  } else if (value is String &&
      RegExp(r'^[+-]?\d+(?:\.0+)?$').hasMatch(value.trim())) {
    // Parse integer digits without a floating intermediate.
    amount = int.tryParse(value.trim().split('.').first);
  }
  if (amount == null ||
      !amount.isFinite ||
      amount.abs() > maxMoney ||
      amount != amount.truncate()) {
    throw const FormatException('money must be an exact safe integer');
  }
  return amount.toInt();
}

void validateMoneyPayload(Object? value) {
  if (value is Map) {
    if (_moneyFields.contains(value['key']) && value.containsKey('value')) {
      exactMoney(value['value']);
    }
    for (final entry in value.entries) {
      if (_moneyFields.contains(entry.key) && entry.value != null) {
        exactMoney(entry.value);
      } else if (entry.value is Map || entry.value is List) {
        validateMoneyPayload(entry.value);
      }
    }
  } else if (value is List) {
    for (final child in value) {
      validateMoneyPayload(child);
    }
  }
}
