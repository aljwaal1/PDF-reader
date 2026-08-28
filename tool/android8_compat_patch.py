from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Do not prepare/download translation models while merely opening the reader.
s = s.replace('    _prepareTranslationModels();\n', '    _initTts();\n', 1)

# Track TTS readiness.
s = s.replace('  bool _showTranscript = false;\n', '  bool _showTranscript = false;\n  bool _ttsReady = false;\n', 1)

# Add robust Android TTS initialization before translation-model helper.
needle = '  Future<void> _prepareTranslationModels() async {\n'
insert = '''  Future<void> _initTts() async {
    try {
      final engine = await _tts.getDefaultEngine;
      if (engine is String && engine.isNotEmpty) {
        await _tts.setEngine(engine);
      }
      var languageResult = await _tts.setLanguage('en-US');
      if (languageResult != 1) {
        languageResult = await _tts.setLanguage('en-GB');
      }
      if (languageResult != 1) {
        await _tts.setLanguage('en');
      }
      await _tts.setSpeechRate(_speechRate);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);
      await _tts.setQueueMode(0);
      _ttsReady = true;
    } catch (_) {
      _ttsReady = false;
    }
  }

'''
if needle not in s:
    raise SystemExit('prepareTranslationModels marker not found')
s = s.replace(needle, insert + needle, 1)

# Translation models are now prepared lazily, only after the user asks for translation.
needle = "      final text = await _extractCurrentPage();\n      if (text.isEmpty) {\n        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');"
repl = "      final text = await _extractCurrentPage();\n      if (text.isEmpty) {\n        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');"
if needle not in s:
    raise SystemExit('translation extraction marker not found')
# Insert after the empty-text guard block instead of before it.
needle2 = "        return;\n      }\n      final translated = await _translator.translateText(text);"
repl2 = "        return;\n      }\n      await _prepareTranslationModels();\n      final translated = await _translator.translateText(text);"
if needle2 not in s:
    raise SystemExit('translation call marker not found')
s = s.replace(needle2, repl2, 1)

# Before speaking, ensure the engine is actually initialized on older Android devices.
needle = "  Future<void> _toggleSpeech() async {\n    if (_speaking) {"
repl = "  Future<void> _toggleSpeech() async {\n    if (!_ttsReady) await _initTts();\n    if (_speaking) {"
if needle not in s:
    raise SystemExit('toggleSpeech marker not found')
s = s.replace(needle, repl, 1)

# Verify speak() result and request Android audio focus.
needle = "    await _tts.setSpeechRate(_speechRate);\n    await _tts.speak(text);"
repl = "    await _tts.setSpeechRate(_speechRate);\n    final result = await _tts.speak(text, focus: true);\n    if (result != 1 && mounted) {\n      setState(() => _speaking = false);\n      _showMessage('تعذر تشغيل الصوت. تأكد من وجود محرك تحويل النص إلى كلام (TTS) وتفعيل صوت إنجليزي في إعدادات الهاتف.');\n    }"
if needle not in s:
    raise SystemExit('speak marker not found')
s = s.replace(needle, repl, 1)

# Same audio-focus behavior after changing speed while speaking.
s = s.replace('    await _tts.speak(remaining);\n', '    await _tts.speak(remaining, focus: true);\n', 1)

p.write_text(s, encoding='utf-8')
print('Applied Android 8 startup/TTS compatibility patch')
