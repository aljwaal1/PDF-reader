from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

s = s.replace(
    'class _ReaderScreenState extends State<ReaderScreen> {',
    'class _ReaderScreenState extends State<ReaderScreen> with WidgetsBindingObserver {'
)

s = s.replace(
    "  Future<void>? _translationSetup;\n  TranslationLayout _layout = TranslationLayout.pdfOnly;",
    "  Future<void>? _translationSetup;\n  String? _translationError;\n  TranslationLayout _layout = TranslationLayout.pdfOnly;"
)

s = s.replace(
    "  void initState() {\n    super.initState();\n    _page = widget.initialPage;",
    "  void initState() {\n    super.initState();\n    WidgetsBinding.instance.addObserver(this);\n    _page = widget.initialPage;"
)

marker = "  Future<void> _prepareTranslationModels() async {\n"
if marker not in s:
    raise SystemExit('prepareTranslationModels marker not found')

lifecycle = '''  @override\n  void didChangeAppLifecycleState(AppLifecycleState state) {\n    if (state == AppLifecycleState.paused ||\n        state == AppLifecycleState.inactive ||\n        state == AppLifecycleState.detached ||\n        state == AppLifecycleState.hidden) {\n      _stopSpeechForBackground();\n    }\n  }\n\n  void _stopSpeechForBackground() {\n    final resume = _restartOffset();\n    ++_speechRunToken;\n    _tts.stop();\n    if (resume > 0) _saveReadingOffset(_page, resume);\n    if (!mounted) return;\n    setState(() {\n      _speaking = false;\n      _resumeOffset = resume;\n      _spokenWord = '';\n    });\n  }\n\n'''
if 'void didChangeAppLifecycleState(AppLifecycleState state)' not in s:
    s = s.replace(marker, lifecycle + marker)

old_prepare = '''  Future<void> _prepareTranslationModels() async {\n    try {\n      for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {\n        final code = language.bcpCode;\n        if (!await _modelManager.isModelDownloaded(code)) {\n          await _modelManager.downloadModel(code, isWifiRequired: false);\n        }\n      }\n    } catch (_) {}\n  }'''
new_prepare = '''  Future<void> _prepareTranslationModels() async {\n    _translationError = null;\n    try {\n      for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {\n        final code = language.bcpCode;\n        if (!await _modelManager.isModelDownloaded(code)) {\n          final ok = await _modelManager.downloadModel(code, isWifiRequired: false);\n          if (!ok) throw StateError('تعذر تنزيل نموذج اللغة $code');\n        }\n      }\n    } catch (e) {\n      _translationError = 'تعذر تجهيز الترجمة. افتح الإنترنت وحاول مرة أخرى.';\n      rethrow;\n    }\n  }'''
if old_prepare not in s:
    raise SystemExit('old prepare block not found')
s = s.replace(old_prepare, new_prepare)

old_sentence_catch = '''      } catch (_) {\n        // Speech must never depend on translation availability.\n      }'''
new_sentence_catch = '''      } catch (_) {\n        _translationSetup = null;\n        _translationError = 'تعذرت ترجمة الجملة. اضغط ترجمة لإعادة المحاولة.';\n        if (mounted && page == _page && sourceText == _spokenText) {\n          setState(() => _currentSentenceTranslation = _translationError!);\n        }\n      }'''
if old_sentence_catch not in s:
    raise SystemExit('sentence catch marker not found')
s = s.replace(old_sentence_catch, new_sentence_catch, 1)

old_translate_start = '''      final text = await _extractCurrentPage(pageNumber: targetPage);\n      if (text.isEmpty) {\n        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');\n        return;\n      }\n      await (_translationSetup ??= _prepareTranslationModels());\n      final translated = await _translator.translateText(text);'''
new_translate_start = '''      var text = await _extractCurrentPage(pageNumber: targetPage);\n      if (text.isEmpty && targetPage == _page && _spokenText.trim().isNotEmpty) {\n        text = _spokenText;\n        _pageText[targetPage] = text;\n      }\n      if (text.isEmpty) {\n        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');\n        return;\n      }\n      try {\n        await (_translationSetup ??= _prepareTranslationModels());\n      } catch (_) {\n        _translationSetup = null;\n        _showMessage(_translationError ?? 'تعذر تجهيز الترجمة. تحقق من الإنترنت وحاول مجددًا.');\n        return;\n      }\n      final translated = await _translator.translateText(text);'''
if old_translate_start not in s:
    raise SystemExit('translate page start marker not found')
s = s.replace(old_translate_start, new_translate_start)

old_page_catch = "    } catch (_) {\n      _showMessage('تعذر ترجمة الصفحة. تحقق من الاتصال عند تنزيل نموذج الترجمة لأول مرة.');\n"
new_page_catch = "    } catch (_) {\n      _translationSetup = null;\n      _showMessage(_translationError ?? 'تعذر ترجمة الصفحة. تحقق من الإنترنت ثم حاول مرة أخرى.');\n"
if old_page_catch not in s:
    raise SystemExit('page catch marker not found')
s = s.replace(old_page_catch, new_page_catch)

old_dispose = '''  void dispose() {\n    ++_speechRunToken;\n    _tts.stop();\n    _translator.close();\n    super.dispose();\n  }'''
new_dispose = '''  void dispose() {\n    WidgetsBinding.instance.removeObserver(this);\n    ++_speechRunToken;\n    _tts.stop();\n    _translator.close();\n    super.dispose();\n  }'''
if old_dispose not in s:
    raise SystemExit('dispose marker not found')
s = s.replace(old_dispose, new_dispose)

p.write_text(s, encoding='utf-8')
print('Applied lifecycle stop and translation recovery fixes')
