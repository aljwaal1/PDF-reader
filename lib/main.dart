import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:google_mlkit_translation/google_mlkit_translation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfrx/pdfrx.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  pdfrxFlutterInitialize();
  runApp(const PdfReaderApp());
}

class PdfReaderApp extends StatelessWidget {
  const PdfReaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PDF Reader',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5B5FEF)),
        scaffoldBackgroundColor: const Color(0xFFF5F6FA),
        cardTheme: const CardThemeData(margin: EdgeInsets.zero),
      ),
      home: const LaunchGate(),
    );
  }
}

class LaunchGate extends StatelessWidget {
  const LaunchGate({super.key});

  Future<bool> _hasSeenIntro() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('onboardingSeen') ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _hasSeenIntro(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return snapshot.data! ? const LibraryScreen() : const OnboardingScreen();
      },
    );
  }
}

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _page = 0;

  static const _cards = [
    (Icons.menu_book_rounded, 'كتبك معك دائمًا', 'أضف ملفات PDF وسيحفظ التطبيق نسخة منها لتعود إليها بسهولة.'),
    (Icons.record_voice_over_rounded, 'استمع وتابع القراءة', 'تابع الجملة الحالية مع تمييز الكلمة المنطوقة داخلها بوضوح.'),
    (Icons.translate_rounded, 'ترجمة عربية مرنة', 'ترجم الصفحة الحالية واختر طريقة عرض الترجمة التي تناسبك.'),
    (Icons.speed_rounded, 'تحكم كامل بالسرعة', 'اختر من 0.5x حتى 2.0x وغيّر السرعة أثناء القراءة مباشرة.'),
  ];

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboardingSeen', true);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const LibraryScreen()));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final last = _page == _cards.length - 1;
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: AlignmentDirectional.centerEnd,
              child: TextButton(onPressed: _finish, child: const Text('تخطي')),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _cards.length,
                onPageChanged: (value) => setState(() => _page = value),
                itemBuilder: (context, index) {
                  final card = _cards[index];
                  return Padding(
                    padding: const EdgeInsets.all(28),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 116,
                          height: 116,
                          decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(32)),
                          child: Icon(card.$1, size: 56, color: scheme.primary),
                        ),
                        const SizedBox(height: 30),
                        Text(card.$2, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 14),
                        Text(card.$3, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.7)),
                      ],
                    ),
                  );
                },
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _cards.length,
                (index) => AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  width: index == _page ? 26 : 8,
                  height: 8,
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    color: index == _page ? scheme.primary : scheme.outlineVariant,
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(22),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: last ? _finish : () => _controller.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                  child: Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text(last ? 'ابدأ الآن' : 'التالي')),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  String? _lastBook;
  int _lastPage = 1;
  bool _importing = false;

  String get _bookName {
    if (_lastBook == null) return '';
    final raw = _lastBook!.split(Platform.pathSeparator).last;
    return raw.replaceFirst(RegExp(r'^\d+_'), '');
  }

  @override
  void initState() {
    super.initState();
    _loadState();
  }

  Future<void> _loadState() async {
    final prefs = await SharedPreferences.getInstance();
    final savedBook = prefs.getString('lastBook');
    final exists = savedBook != null && await File(savedBook).exists();
    if (!exists && savedBook != null) {
      await prefs.remove('lastBook');
      await prefs.remove('lastPage');
    }
    if (!mounted) return;
    setState(() {
      _lastBook = exists ? savedBook : null;
      _lastPage = exists ? (prefs.getInt('lastPage') ?? 1) : 1;
    });
  }

  Future<String?> _importPdf(PlatformFile picked) async {
    final docs = await getApplicationDocumentsDirectory();
    final booksDir = Directory('${docs.path}${Platform.pathSeparator}books');
    await booksDir.create(recursive: true);
    final safeName = picked.name.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
    final target = File('${booksDir.path}${Platform.pathSeparator}${DateTime.now().millisecondsSinceEpoch}_$safeName');
    if (picked.path != null) {
      final source = File(picked.path!);
      if (await source.exists()) {
        await source.copy(target.path);
        return target.path;
      }
    }
    final stream = picked.readStream;
    if (stream != null) {
      final sink = target.openWrite();
      await sink.addStream(stream);
      await sink.close();
      return target.path;
    }
    return null;
  }

  Future<void> _pickPdf() async {
    setState(() => _importing = true);
    try {
      final result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['pdf'], withReadStream: true);
      if (result == null || result.files.isEmpty) return;
      final path = await _importPdf(result.files.single);
      if (path == null) {
        _message('تعذر استيراد ملف PDF. جرّب اختيار الملف من تطبيق الملفات في الهاتف.');
        return;
      }
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('lastBook', path);
      await prefs.setInt('lastPage', 1);
      if (!mounted) return;
      setState(() {
        _lastBook = path;
        _lastPage = 1;
      });
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReaderScreen(filePath: path, initialPage: 1)));
      await _loadState();
    } catch (_) {
      _message('لم نتمكن من فتح الكتاب. تأكد أن الملف PDF صالح ثم حاول مرة أخرى.');
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  Future<void> _continueReading() async {
    if (_lastBook == null) return;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReaderScreen(filePath: _lastBook!, initialPage: _lastPage)));
    await _loadState();
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Widget _featureChip(IconData icon, String label) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: scheme.outlineVariant)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(icon, size: 17, color: scheme.primary), const SizedBox(width: 6), Text(label, style: const TextStyle(fontWeight: FontWeight.w600))]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadState,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 26),
            children: [
              Row(
                children: [
                  Container(width: 46, height: 46, decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(15)), child: Icon(Icons.auto_stories_rounded, color: scheme.primary)),
                  const SizedBox(width: 11),
                  const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('قارئ الكتب', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w900)), SizedBox(height: 2), Text('اقرأ • استمع • ترجم', style: TextStyle(color: Colors.black54, fontWeight: FontWeight.w500))])),
                  IconButton.filledTonal(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add_rounded), tooltip: 'إضافة كتاب'),
                ],
              ),
              const SizedBox(height: 22),
              if (_lastBook != null) ...[
                Text('تابع القراءة', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 10),
                InkWell(
                  borderRadius: BorderRadius.circular(24),
                  onTap: _continueReading,
                  child: Ink(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(gradient: LinearGradient(colors: [scheme.primaryContainer, scheme.secondaryContainer]), borderRadius: BorderRadius.circular(24)),
                    child: Row(
                      children: [
                        Container(width: 68, height: 92, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(15)), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.picture_as_pdf_rounded, size: 34, color: scheme.primary), const SizedBox(height: 5), const Text('PDF', style: TextStyle(fontWeight: FontWeight.w900))])),
                        const SizedBox(width: 14),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(_bookName, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)), const SizedBox(height: 8), Text('الصفحة $_lastPage', style: const TextStyle(fontWeight: FontWeight.w600)), const SizedBox(height: 12), FilledButton.icon(onPressed: _continueReading, icon: const Icon(Icons.play_arrow_rounded), label: const Text('متابعة'))])),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],
              Row(children: [Expanded(child: Text('مكتبتي', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))), TextButton.icon(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add), label: const Text('إضافة كتاب'))]),
              const SizedBox(height: 9),
              if (_lastBook == null)
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24), border: Border.all(color: scheme.outlineVariant)),
                  child: Column(children: [Container(width: 78, height: 78, decoration: BoxDecoration(color: scheme.primaryContainer.withValues(alpha: .55), shape: BoxShape.circle), child: Icon(Icons.library_books_rounded, size: 39, color: scheme.primary)), const SizedBox(height: 16), const Text('مكتبتك جاهزة للكتاب الأول', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800), textAlign: TextAlign.center), const SizedBox(height: 8), const Text('أضف أي كتاب PDF وابدأ القراءة والاستماع والترجمة من مكان واحد.', textAlign: TextAlign.center, style: TextStyle(height: 1.5, color: Colors.black54)), const SizedBox(height: 18), SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: _importing ? null : _pickPdf, icon: _importing ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.upload_file_rounded), label: Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text(_importing ? 'جاري إضافة الكتاب...' : 'اختر كتاب PDF'))))]),
                )
              else
                Card(
                  elevation: 0,
                  color: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: scheme.outlineVariant)),
                  child: ListTile(contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), leading: Container(width: 46, height: 56, decoration: BoxDecoration(color: scheme.errorContainer, borderRadius: BorderRadius.circular(11)), child: Icon(Icons.picture_as_pdf_rounded, color: scheme.onErrorContainer)), title: Text(_bookName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)), subtitle: Text('آخر وصول: الصفحة $_lastPage'), trailing: const Icon(Icons.chevron_right_rounded), onTap: _continueReading),
                ),
              const SizedBox(height: 24),
              Text('كل ما تحتاجه أثناء القراءة', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              Wrap(spacing: 7, runSpacing: 7, children: [_featureChip(Icons.volume_up_rounded, 'قراءة صوتية'), _featureChip(Icons.translate_rounded, 'ترجمة عربية'), _featureChip(Icons.speed_rounded, 'سرعة مرنة'), _featureChip(Icons.visibility_rounded, 'متابعة الكلمة')]),
            ],
          ),
        ),
      ),
      floatingActionButton: _lastBook == null ? null : FloatingActionButton.extended(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add_rounded), label: const Text('كتاب جديد')),
    );
  }
}

enum TranslationLayout { pdfOnly, translationOnly, below, sideBySide, bottomSheet }

class ReaderScreen extends StatefulWidget {
  const ReaderScreen({super.key, required this.filePath, required this.initialPage});
  final String filePath;
  final int initialPage;

  @override
  State<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends State<ReaderScreen> {
  final PdfViewerController _pdfController = PdfViewerController();
  final FlutterTts _tts = FlutterTts();
  final OnDeviceTranslator _translator = OnDeviceTranslator(sourceLanguage: TranslateLanguage.english, targetLanguage: TranslateLanguage.arabic);
  final OnDeviceTranslatorModelManager _modelManager = OnDeviceTranslatorModelManager();
  final Map<int, String> _pageText = {};
  final Map<int, String> _translations = {};

  int _page = 1;
  int _pageCount = 0;
  bool _busy = false;
  bool _speaking = false;
  bool _showTranscript = false;
  double _speechRate = .50;
  String _spokenText = '';
  String _spokenWord = '';
  int _spokenStart = 0;
  int _spokenEnd = 0;
  int _speechOffset = 0;
  int _resumeOffset = 0;
  int _lastSentenceStart = -1;
  bool _autoNext = true;
  bool _translatingSentence = false;
  String _currentSentenceTranslation = '';
  final Map<int, Map<int, String>> _sentenceTranslations = {};
  TranslationLayout _layout = TranslationLayout.pdfOnly;

  @override
  void initState() {
    super.initState();
    _page = widget.initialPage;
    _tts.setLanguage('en-US');
    _tts.setSpeechRate(_speechRate);
    _tts.setCompletionHandler(() {
      _handleSpeechComplete();
    });
    _tts.setProgressHandler((text, start, end, word) {
      if (!mounted) return;
      final absoluteStart = (_speechOffset + start).clamp(0, _spokenText.length);
      final absoluteEnd = (_speechOffset + end).clamp(0, _spokenText.length);
      setState(() {
        _spokenWord = word;
        _spokenStart = absoluteStart;
        _spokenEnd = absoluteEnd;
        _resumeOffset = absoluteStart;
      });
      _saveReadingOffset(_page, absoluteStart);
      _translateSentenceAt(absoluteStart);
    });
    _prepareTranslationModels();
  }

  Future<void> _prepareTranslationModels() async {
    try {
      for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {
        final code = language.bcpCode;
        if (!await _modelManager.isModelDownloaded(code)) {
          await _modelManager.downloadModel(code, isWifiRequired: false);
        }
      }
    } catch (_) {}
  }

  String _cleanText(String value) => value.replaceAll(RegExp(r'\s+'), ' ').replaceAll(RegExp(r'(^|\s)(W\d+|Page\s*\d+)(?=\s|$)', caseSensitive: false), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();

  Future<String> _extractCurrentPage() async {
    if (_pageText.containsKey(_page)) return _pageText[_page]!;
    if (!_pdfController.isReady || _page < 1 || _page > _pdfController.pages.length) return '';
    final pageText = await _pdfController.pages[_page - 1].loadText();
    final text = _cleanText(pageText?.fullText ?? '');
    _pageText[_page] = text;
    return text;
  }

  String _positionKey(int page) => 'readingOffset:${widget.filePath}:$page';
  String _translationKey(int page) => 'pageTranslation:${widget.filePath}:$page';

  Future<void> _saveReadingOffset(int page, int offset) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_positionKey(page), offset);
  }

  Future<int> _loadReadingOffset(int page) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_positionKey(page)) ?? 0;
  }

  Future<void> _clearReadingOffset(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_positionKey(page));
  }

  Future<void> _saveTranslation(int page, String text) async {
    if (text.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_translationKey(page), text);
  }

  Future<void> _restorePageState(int page) async {
    final prefs = await SharedPreferences.getInstance();
    final savedTranslation = prefs.getString(_translationKey(page));
    final offset = prefs.getInt(_positionKey(page)) ?? 0;
    if (!mounted || page != _page) return;
    setState(() {
      _resumeOffset = offset;
      _currentSentenceTranslation = '';
      _lastSentenceStart = -1;
      if (savedTranslation != null && savedTranslation.trim().isNotEmpty) {
        _translations[page] = savedTranslation;
      }
    });
  }

  Future<void> _translateSentenceAt(int position) async {
    if (_spokenText.isEmpty || _translatingSentence) return;
    final bounds = _sentenceBounds(position);
    final start = bounds.$1;
    final end = bounds.$2;
    if (end <= start || start == _lastSentenceStart) return;
    final sentence = _spokenText.substring(start, end).trim();
    if (sentence.isEmpty) return;
    _lastSentenceStart = start;
    _translatingSentence = true;
    try {
      final translated = await _translator.translateText(sentence);
      final pageMap = _sentenceTranslations.putIfAbsent(_page, () => <int, String>{});
      pageMap[start] = translated;
      final keys = pageMap.keys.toList()..sort();
      final full = keys.map((key) => pageMap[key]!).join('\n\n');
      if (!mounted) return;
      setState(() {
        _currentSentenceTranslation = translated;
        _translations[_page] = full;
      });
      await _saveTranslation(_page, full);
    } catch (_) {
      // Keep reading even if one sentence cannot be translated.
    } finally {
      _translatingSentence = false;
    }
  }

  Future<void> _startSpeechFrom(int offset) async {
    final text = await _extractCurrentPage();
    if (text.isEmpty) {
      _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      return;
    }
    final safeOffset = offset.clamp(0, text.length);
    final source = text.substring(safeOffset);
    final remaining = source.trimLeft();
    final actualOffset = safeOffset + (source.length - remaining.length);
    if (remaining.isEmpty) return;
    if (!mounted) return;
    setState(() {
      _spokenText = text;
      _speechOffset = actualOffset;
      _resumeOffset = actualOffset;
      _spokenStart = actualOffset;
      _spokenEnd = actualOffset;
      _spokenWord = '';
      _speaking = true;
      _lastSentenceStart = -1;
    });
    await _tts.setSpeechRate(_speechRate);
    await _translateSentenceAt(actualOffset);
    await _tts.speak(remaining);
  }

  Future<void> _handleSpeechComplete() async {
    if (!mounted) return;
    final completedPage = _page;
    await _clearReadingOffset(completedPage);
    setState(() {
      _speaking = false;
      _resumeOffset = 0;
    });
    if (_autoNext && completedPage < _pageCount) {
      await _go(completedPage + 1, keepAutoReading: true);
      await Future<void>.delayed(const Duration(milliseconds: 220));
      if (mounted && _page == completedPage + 1) await _startSpeechFrom(_resumeOffset);
    }
  }

  Future<void> _translatePage() async {
    if (_translations.containsKey(_page)) {
      setState(() {
        if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
      });
      return;
    }
    setState(() => _busy = true);
    try {
      final text = await _extractCurrentPage();
      if (text.isEmpty) {
        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');
        return;
      }
      final translated = await _translator.translateText(text);
      if (mounted) {
        setState(() {
          _translations[_page] = translated;
          if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
          _saveTranslation(_page, translated);
        });
      }
    } catch (_) {
      _showMessage('تعذر ترجمة الصفحة. تحقق من الاتصال عند تنزيل نموذج الترجمة لأول مرة.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleSpeech() async {
    if (_speaking) {
      final resume = _restartOffset();
      await _tts.stop();
      await _saveReadingOffset(_page, resume);
      if (mounted) setState(() {
        _speaking = false;
        _resumeOffset = resume;
      });
      return;
    }
    final saved = _resumeOffset > 0 ? _resumeOffset : await _loadReadingOffset(_page);
    await _startSpeechFrom(saved);
  }

  int _restartOffset() {
    if (_spokenText.isEmpty || _spokenEnd <= 0) return 0;
    var offset = (_spokenEnd - _spokenWord.length).clamp(0, _spokenText.length);
    while (offset > 0 && offset < _spokenText.length && _spokenText[offset - 1].trim().isNotEmpty) {
      offset--;
    }
    return offset;
  }

  Future<void> _setRate(double value) async {
    final rate = value.clamp(.25, 1.0).toDouble();
    final wasSpeaking = _speaking && _spokenText.isNotEmpty;
    final resumeAt = wasSpeaking ? _restartOffset() : 0;
    if (mounted) setState(() => _speechRate = rate);
    if (!wasSpeaking) {
      await _tts.setSpeechRate(rate);
      return;
    }
    await _tts.stop();
    await _tts.setSpeechRate(rate);
    if (!mounted || resumeAt >= _spokenText.length) return;
    final source = _spokenText.substring(resumeAt);
    final remaining = source.trimLeft();
    _speechOffset = resumeAt + (source.length - remaining.length);
    setState(() {
      _speaking = true;
      _spokenStart = _speechOffset;
      _spokenEnd = _speechOffset;
      _spokenWord = '';
    });
    await _tts.speak(remaining);
  }

  Future<void> _savePage(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lastBook', widget.filePath);
    await prefs.setInt('lastPage', page);
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _go(int nextPage, {bool keepAutoReading = false}) async {
    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;
    await _tts.stop();
    setState(() {
      _speaking = false;
      _spokenWord = '';
      _spokenStart = 0;
      _spokenEnd = 0;
      _speechOffset = 0;
      _resumeOffset = 0;
      _spokenText = '';
      _currentSentenceTranslation = '';
      _lastSentenceStart = -1;
      _showTranscript = false;
    });
    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);
    await _restorePageState(nextPage);
  }

  double get _readingProgress => _spokenText.isEmpty ? 0 : (_spokenEnd / _spokenText.length).clamp(0.0, 1.0);

  (int, int) _sentenceBounds(int position) {
    if (_spokenText.isEmpty) return (0, 0);
    var start = 0;
    var end = _spokenText.length;
    final pos = position.clamp(0, _spokenText.length);
    for (var i = pos - 1; i >= 0; i--) {
      if ('.!?'.contains(_spokenText[i])) {
        start = i + 1;
        break;
      }
    }
    while (start < end && _spokenText[start].trim().isEmpty) start++;
    for (var i = pos; i < _spokenText.length; i++) {
      if ('.!?'.contains(_spokenText[i])) {
        end = i + 1;
        break;
      }
    }
    return (start, end);
  }

  Widget _readingCard() {
    if (_spokenText.isEmpty || (!_speaking && _spokenWord.isEmpty)) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final bounds = _sentenceBounds(_spokenStart);
    final sentenceStart = bounds.$1;
    final sentenceEnd = bounds.$2;
    final wordStart = _spokenStart.clamp(sentenceStart, sentenceEnd);
    final wordEnd = _spokenEnd.clamp(wordStart, sentenceEnd);
    final before = _spokenText.substring(sentenceStart, wordStart);
    final current = wordEnd > wordStart ? _spokenText.substring(wordStart, wordEnd) : (_spokenWord.isEmpty ? '…' : _spokenWord);
    final after = _spokenText.substring(wordEnd, sentenceEnd);
    final words = _spokenText.substring(sentenceStart, sentenceEnd).trim().split(RegExp(r'\s+')).where((e) => e.isNotEmpty).toList();
    final currentNumber = _spokenText.substring(sentenceStart, wordStart).trim().isEmpty ? 1 : _spokenText.substring(sentenceStart, wordStart).trim().split(RegExp(r'\s+')).length + 1;

    return Container(
      margin: const EdgeInsets.fromLTRB(6, 5, 6, 4),
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(15), border: Border.all(color: scheme.outlineVariant)),
      child: Directionality(
        textDirection: TextDirection.ltr,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(children: [Container(width: 7, height: 7, decoration: BoxDecoration(color: scheme.primary, shape: BoxShape.circle)), const SizedBox(width: 7), const Expanded(child: Text('NOW READING', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Colors.black54, letterSpacing: .7))), Text(words.isEmpty ? '' : '${currentNumber.clamp(1, words.length)} / ${words.length}', style: const TextStyle(fontSize: 11, color: Colors.black45, fontWeight: FontWeight.w600))]),
            const SizedBox(height: 6),
            Text.rich(
              TextSpan(
                style: const TextStyle(fontSize: 17, height: 1.55, color: Color(0xFF252633)),
                children: [
                  TextSpan(text: before, style: const TextStyle(color: Color(0xFF888B98))),
                  TextSpan(text: current, style: TextStyle(fontWeight: FontWeight.w800, color: const Color(0xFF3033A8), backgroundColor: scheme.primaryContainer)),
                  TextSpan(text: after),
                ],
              ),
            ),
            if (_currentSentenceTranslation.isNotEmpty) ...[
              const SizedBox(height: 8),
              Directionality(
                textDirection: TextDirection.rtl,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(color: scheme.secondaryContainer.withValues(alpha: .55), borderRadius: BorderRadius.circular(10)),
                  child: Text(_currentSentenceTranslation, style: const TextStyle(fontSize: 15, height: 1.55, fontWeight: FontWeight.w600)),
                ),
              ),
            ],
            const SizedBox(height: 7),
            ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: _readingProgress, minHeight: 4, backgroundColor: scheme.surfaceContainerHighest)),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 2), minimumSize: Size.zero, tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                onPressed: () => setState(() => _showTranscript = !_showTranscript),
                child: Text(_showTranscript ? 'إخفاء النص الكامل' : 'إظهار النص الكامل', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
              ),
            ),
            if (_showTranscript)
              Container(
                constraints: const BoxConstraints(maxHeight: 92),
                width: double.infinity,
                padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(color: scheme.surfaceContainerHighest, borderRadius: BorderRadius.circular(10)),
                child: SingleChildScrollView(child: SelectableText(_spokenText, style: const TextStyle(fontSize: 13, height: 1.55))),
              ),
          ],
        ),
      ),
    );
  }

  Widget _pdfView() {
    return Container(
      color: const Color(0xFFE9ECF2),
      child: PdfViewer.file(
        widget.filePath,
        controller: _pdfController,
        initialPageNumber: widget.initialPage,
        params: PdfViewerParams(
          margin: 3,
          onViewerReady: (document, controller) {
            if (mounted) setState(() => _pageCount = controller.pageCount);
          },
          onPageChanged: (pageNumber) {
            if (pageNumber == null) return;
            setState(() {
              _page = pageNumber;
              _currentSentenceTranslation = '';
              _lastSentenceStart = -1;
            });
            _savePage(pageNumber);
            _restorePageState(pageNumber);
          },
        ),
      ),
    );
  }

  Widget _translationPane() {
    final text = _translations[_page];
    return Container(
      color: Theme.of(context).colorScheme.surface,
      padding: const EdgeInsets.all(14),
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: text == null
            ? Center(child: _busy ? const CircularProgressIndicator() : FilledButton.icon(onPressed: _translatePage, icon: const Icon(Icons.translate), label: const Text('ترجمة الصفحة الحالية')))
            : SingleChildScrollView(child: SelectableText(text, style: const TextStyle(fontSize: 17, height: 1.8))),
      ),
    );
  }

  Widget _body() {
    switch (_layout) {
      case TranslationLayout.pdfOnly:
        return _pdfView();
      case TranslationLayout.translationOnly:
        return _translationPane();
      case TranslationLayout.below:
        return Column(children: [Expanded(flex: 7, child: _pdfView()), Expanded(flex: 3, child: _translationPane())]);
      case TranslationLayout.sideBySide:
        return Row(children: [Expanded(child: _pdfView()), const VerticalDivider(width: 1), Expanded(child: _translationPane())]);
      case TranslationLayout.bottomSheet:
        return Stack(
          children: [
            Positioned.fill(child: _pdfView()),
            Align(
              alignment: Alignment.bottomCenter,
              child: DraggableScrollableSheet(
                initialChildSize: .18,
                minChildSize: .10,
                maxChildSize: .78,
                builder: (context, controller) => Material(
                  elevation: 8,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
                  clipBehavior: Clip.antiAlias,
                  child: Column(children: [const Padding(padding: EdgeInsets.only(top: 5), child: SizedBox(width: 36, child: Divider(thickness: 3))), Expanded(child: SingleChildScrollView(controller: controller, child: SizedBox(height: MediaQuery.sizeOf(context).height * .62, child: _translationPane())))]),
                ),
              ),
            ),
          ],
        );
    }
  }

  String _layoutName(TranslationLayout value) => switch (value) {
        TranslationLayout.pdfOnly => 'PDF فقط',
        TranslationLayout.translationOnly => 'الترجمة فقط',
        TranslationLayout.below => 'الترجمة أسفل الصفحة',
        TranslationLayout.sideBySide => 'جنبًا إلى جنب',
        TranslationLayout.bottomSheet => 'نافذة قابلة للسحب',
      };

  @override
  void dispose() {
    _tts.stop();
    _translator.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final visibleRate = _speechRate * 2;
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 48,
        titleSpacing: 0,
        title: Text(_pageCount == 0 ? 'PDF Reader' : 'الصفحة $_page / $_pageCount', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
        actions: [IconButton(tooltip: _autoNext ? 'الانتقال التلقائي مفعّل' : 'الانتقال التلقائي متوقف', onPressed: () => setState(() => _autoNext = !_autoNext), icon: Icon(_autoNext ? Icons.skip_next_rounded : Icons.skip_next_outlined, color: _autoNext ? scheme.primary : null)), PopupMenuButton<TranslationLayout>(tooltip: 'طريقة عرض الترجمة', icon: const Icon(Icons.view_quilt_outlined, size: 22), initialValue: _layout, onSelected: (value) => setState(() => _layout = value), itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList())],
      ),
      body: Column(children: [Expanded(child: _body()), _readingCard()]),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          decoration: BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: scheme.outlineVariant))),
          padding: const EdgeInsets.fromLTRB(7, 4, 7, 6),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  SizedBox(width: 36, height: 34, child: IconButton(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact, onPressed: _speechRate > .25 ? () => _setRate(_speechRate - .05) : null, icon: const Icon(Icons.remove_rounded, size: 20), tooltip: 'أبطأ')),
                  SizedBox(width: 43, child: Text('${visibleRate.toStringAsFixed(1)}x', textAlign: TextAlign.center, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800))),
                  Expanded(child: Slider(min: .25, max: 1.0, divisions: 15, value: _speechRate, onChanged: (value) => setState(() => _speechRate = value), onChangeEnd: _setRate)),
                  SizedBox(width: 36, height: 34, child: IconButton(padding: EdgeInsets.zero, visualDensity: VisualDensity.compact, onPressed: _speechRate < 1.0 ? () => _setRate(_speechRate + .05) : null, icon: const Icon(Icons.add_rounded, size: 20), tooltip: 'أسرع')),
                ],
              ),
              const SizedBox(height: 2),
              Directionality(
                textDirection: TextDirection.rtl,
                child: Row(
                  children: [
                    Expanded(child: OutlinedButton.icon(onPressed: _page > 1 ? () => _go(_page - 1) : null, icon: const Icon(Icons.chevron_right_rounded, size: 20), label: const Text('السابق'), style: OutlinedButton.styleFrom(minimumSize: const Size(0, 38), padding: const EdgeInsets.symmetric(horizontal: 6)))),
                    const SizedBox(width: 5),
                    Expanded(child: FilledButton.tonalIcon(onPressed: _toggleSpeech, icon: Icon(_speaking ? Icons.stop_circle_outlined : Icons.volume_up_outlined, size: 19), label: Text(_speaking ? 'إيقاف' : 'قراءة'), style: FilledButton.styleFrom(minimumSize: const Size(0, 38), padding: const EdgeInsets.symmetric(horizontal: 6)))),
                    const SizedBox(width: 5),
                    Expanded(child: FilledButton.icon(onPressed: _busy ? null : _translatePage, icon: _busy ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.translate_rounded, size: 18), label: const Text('ترجمة'), style: FilledButton.styleFrom(minimumSize: const Size(0, 38), padding: const EdgeInsets.symmetric(horizontal: 5)))),
                    const SizedBox(width: 5),
                    Expanded(child: FilledButton(onPressed: _page < _pageCount ? () => _go(_page + 1) : null, style: FilledButton.styleFrom(minimumSize: const Size(0, 38), padding: const EdgeInsets.symmetric(horizontal: 6)), child: const Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(Icons.chevron_left_rounded, size: 20), SizedBox(width: 2), Text('التالي')]))),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
