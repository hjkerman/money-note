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

const _authoritativeMoneySettings = {
  'scheduled_income',
  'cash_flow_balance',
  'card_limit',
  'base_next_month_liquidity',
  'liquidity_status',
};

// Backend isolated_sync.raw.setting_money / audited E1 grammar. This is an
// authoritative SETTING read boundary, not the frozen local-input parser.
// The validation view is never written back into the original map or bytes.
int exactAuthoritativeSettingMoney(String value) {
  final text = _authoritativeSettingText(value);
  if (!RegExp(r'^[+-]?[0-9]+(?:\.0+)?$').hasMatch(text)) {
    throw const FormatException('money must be an exact safe integer');
  }
  final amount = BigInt.parse(text.split('.')[0]);
  if (amount.abs() > BigInt.from(maxMoney)) {
    throw const FormatException('money must be an exact safe integer');
  }
  return amount.toInt();
}

// Python str.strip()'s 29 whitespace codepoints. All are BMP. In particular
// U+001C..U+001F are whitespace, U+FEFF is NOT. No Unicode normalization.
String _authoritativeSettingText(String value) {
  bool whitespace(int c) =>
      (c >= 0x09 && c <= 0x0d) ||
      (c >= 0x1c && c <= 0x20) ||
      c == 0x85 ||
      c == 0xa0 ||
      c == 0x1680 ||
      (c >= 0x2000 && c <= 0x200a) ||
      c == 0x2028 ||
      c == 0x2029 ||
      c == 0x202f ||
      c == 0x205f ||
      c == 0x3000;
  var start = 0, end = value.length;
  while (start < end && whitespace(value.codeUnitAt(start))) {
    start++;
  }
  while (end > start && whitespace(value.codeUnitAt(end - 1))) {
    end--;
  }
  return value.substring(start, end);
}

// Only the five named monetary settings use the compatible string grammar.
// Other numeric fields keep exactMoney(), including its frozen input contract.
void validateAuthoritativeSettingsMoney(Object? value) {
  if (value is! Map) throw const FormatException('settings must be an object');
  if (_moneyFields.contains(value['key']) && value.containsKey('value')) {
    exactMoney(value['value']);
  }
  for (final entry in value.entries) {
    if (_authoritativeMoneySettings.contains(entry.key) &&
        entry.value is String) {
      exactAuthoritativeSettingMoney(entry.value as String);
    } else {
      validateMoneyPayload({entry.key: entry.value});
    }
  }
}

// Complete authoritative bundle/Snapshot/baseline reads only. This does not
// confer origin, completeness, lineage or installation authority. Those checks
// remain with their existing owners. Never use this for a J or POST payload.
void validateAuthoritativeMoneyPayload(Object? value) {
  if (value is Map) {
    if (_moneyFields.contains(value['key']) && value.containsKey('value')) {
      exactMoney(value['value']);
    }
    for (final entry in value.entries) {
      if (entry.key == 'settings' && entry.value is Map) {
        validateAuthoritativeSettingsMoney(entry.value);
      } else if (entry.key == 'app_settings' && entry.value is List) {
        for (final row in entry.value as List) {
          if (row is Map &&
              _authoritativeMoneySettings.contains(row['key']) &&
              row['value'] is String) {
            exactAuthoritativeSettingMoney(row['value'] as String);
            // Validate every other field as before; never mutate the row.
            validateMoneyPayload({
              for (final e in row.entries)
                if (e.key != 'value') e.key: e.value
            });
          } else {
            validateMoneyPayload(row);
          }
        }
      } else if (_moneyFields.contains(entry.key) && entry.value != null) {
        exactMoney(entry.value);
      } else if (entry.value is Map || entry.value is List) {
        validateAuthoritativeMoneyPayload(entry.value);
      }
    }
  } else if (value is List) {
    for (final child in value) {
      validateAuthoritativeMoneyPayload(child);
    }
  }
}
