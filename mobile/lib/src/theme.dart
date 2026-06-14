import 'package:flutter/material.dart';

const moneyBg = Color(0xFFF8F6EF);
const moneySurface = Color(0xFFFFFEFA);
const moneyLine = Color(0xFFD6D0C2);
const moneyText = Color(0xFF22211F);
const moneyMuted = Color(0xFF68645B);
const moneyGreen = Color(0xFF496B42);
const moneyGreenSoft = Color(0xFFDDE9D5);
const moneyRed = Color(0xFFB83A37);

ThemeData buildMoneyNoteTheme() {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: moneyGreen,
      primary: moneyGreen,
      surface: moneySurface,
    ),
    scaffoldBackgroundColor: moneyBg,
    fontFamily: 'Roboto',
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: moneySurface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: moneyLine),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: moneyLine),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: moneyGreen, width: 1.4),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: moneyGreen,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: moneyText,
        side: const BorderSide(color: moneyLine),
        minimumSize: const Size.fromHeight(44),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
  );
}
