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
        scaffoldBackgroundColor: const Color(0xFFF7F7FB),
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
    (Icons.record_voice_over_rounded, 'استمع وتابع القراءة', 'استمع للنص الإنجليزي مع مؤشر للكلمة الحالية ونص متحرك.'),
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
                          width: 124,
                          height: 124,
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(36),
                          ),
                          child: Icon(card.$1, size: 60, color: Theme.of(context).colorScheme.primary),
                        ),
                        const SizedBox(height: 34),
                        Text(card.$2, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 16),
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
                    color: index == _page ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.outlineVariant,
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: last ? _finish : () => _controller.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Text(last ? 'ابدأ الآن' : 'التالي'),
                  ),
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
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf'],
        withReadStream: true,
      );
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 7),
          Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
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
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(16)),
                    child: Icon(Icons.auto_stories_rounded, color: scheme.primary),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('قارئ الكتب', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
                        SizedBox(height: 2),
                        Text('اقرأ • استمع • ترجم', style: TextStyle(color: Colors.black54, fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ),
                  IconButton.filledTonal(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add_rounded), tooltip: 'إضافة كتاب'),
                ],
              ),
              const SizedBox(height: 24),
              if (_lastBook != null) ...[
                Text('تابع القراءة', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 12),
                InkWell(
                  borderRadius: BorderRadius.circular(26),
                  onTap: _continueReading,
                  child: Ink(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(colors: [scheme.primaryContainer, scheme.secondaryContainer]),
                      borderRadius: BorderRadius.circular(26),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 76,
                          height: 102,
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.picture_as_pdf_rounded, size: 38, color: scheme.primary),
                              const SizedBox(height: 6),
                              const Text('PDF', style: TextStyle(fontWeight: FontWeight.w900)),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_bookName, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Icon(Icons.bookmark_rounded, size: 18, color: scheme.primary),
                                  const SizedBox(width: 6),
                                  Text('الصفحة $_lastPage', style: const TextStyle(fontWeight: FontWeight.w600)),
                                ],
                              ),
                              const SizedBox(height: 14),
                              FilledButton.icon(onPressed: _continueReading, icon: const Icon(Icons.play_arrow_rounded), label: const Text('متابعة')),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 26),
              ],
              Row(
                children: [
                  Expanded(child: Text('مكتبتي', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))),
                  TextButton.icon(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add), label: const Text('إضافة كتاب')),
                ],
              ),
              const SizedBox(height: 10),
              if (_lastBook == null)
                Container(
                  padding: const EdgeInsets.fromLTRB(22, 30, 22, 26),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(26), border: Border.all(color: scheme.outlineVariant)),
                  child: Column(
                    children: [
                      Container(
                        width: 84,
                        height: 84,
                        decoration: BoxDecoration(color: scheme.primaryContainer.withValues(alpha: .55), shape: BoxShape.circle),
                        child: Icon(Icons.library_books_rounded, size: 42, color: scheme.primary),
                      ),
                      const SizedBox(height: 18),
                      const Text('مكتبتك جاهزة للكتاب الأول', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800), textAlign: TextAlign.center),
                      const SizedBox(height: 8),
                      const Text('أضف أي كتاب PDF وابدأ القراءة والاستماع والترجمة من مكان واحد.', textAlign: TextAlign.center, style: TextStyle(height: 1.5, color: Colors.black54)),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _importing ? null : _pickPdf,
                          icon: _importing ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.upload_file_rounded),
                          label: Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text(_importing ? 'جاري إضافة الكتاب...' : 'اختر كتاب PDF')),
                        ),
                      ),
                    ],
                  ),
                )
              else
                Card(
                  elevation: 0,
                  color: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22), side: BorderSide(color: scheme.outlineVariant)),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    leading: Container(
                      width: 48,
                      height: 58,
                      decoration: BoxDecoration(color: scheme.errorContainer, borderRadius: BorderRadius.circular(12)),
                      child: Icon(Icons.picture_as_pdf_rounded, color: scheme.onErrorContainer),
                    ),
                    title: Text(_bookName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text('آخر وصول: الصفحة $_lastPage'),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: _continueReading,
                  ),
                ),
              const SizedBox(height: 26),
              Text('كل ما تحتاجه أثناء القراءة', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _featureChip(Icons.volume_up_rounded, 'قراءة صوتية'),
                  _featureChip(Icons.translate_rounded, 'ترجمة عربية'),
                  _featureChip(Icons.speed_rounded, 'سرعة مرنة'),
                  _featureChip(Icons.visibility_rounded, 'متابعة الكلمة'),
                ],
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: _lastBook == null
          ? null
          : FloatingActionButton.extended(
              onPressed: _importing ? null : _pickPdf,
              icon: const Icon(Icons.add_rounded),
              label: const Text('كتاب جديد'),
            ),
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
  double _speechRate = .50;
  String _spokenText = '';
  String _spokenWord = '';
  int _spokenEnd = 0;
  int _speechOffset = 0;
  TranslationLayout _layout = TranslationLayout.bottomSheet;

  @override
  void initState() {
    super.initState();
    _page = widget.initialPage;
    _tts.setLanguage('en-US');
    _tts.setSpeechRate(_speechRate);
    _tts.setCompletionHandler(() {
      if (mounted) setState(() => _speaking = false);
    });
    _tts.setProgressHandler((text, start, end, word) {
      if (!mounted) return;
      final absoluteEnd = (_speechOffset + end).clamp(0, _spokenText.length);
      setState(() {
        _spokenWord = word;
        _spokenEnd = absoluteEnd;
      });
    });
    _prepareTranslationModels();
  }

  Future<void> _prepareTranslationModels() async {
    for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {
      final code = language.bcpCode;
      if (!await _modelManager.isModelDownloaded(code)) {
        await _modelManager.downloadModel(code, isWifiRequired: false);
      }
    }
  }

  Future<String> _extractCurrentPage() async {
    if (_pageText.containsKey(_page)) return _pageText[_page]!;
    if (!_pdfController.isReady || _page < 1 || _page > _pdfController.pages.length) return '';
    final pageText = await _pdfController.pages[_page - 1].loadText();
    final text = pageText?.fullText.trim() ?? '';
    _pageText[_page] = text;
    return text;
  }

  Future<void> _translatePage() async {
    if (_translations.containsKey(_page)) return setState(() {});
    setState(() => _busy = true);
    try {
      final text = await _extractCurrentPage();
      if (text.isEmpty) {
        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');
        return;
      }
      final translated = await _translator.translateText(text);
      if (mounted) setState(() => _translations[_page] = translated);
    } catch (_) {
      _showMessage('تعذر ترجمة الصفحة. تحقق من الاتصال عند تنزيل نموذج الترجمة لأول مرة.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleSpeech() async {
    if (_speaking) {
      await _tts.stop();
      if (mounted) setState(() => _speaking = false);
      return;
    }
    final text = await _extractCurrentPage();
    if (text.isEmpty) {
      _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      return;
    }
    setState(() {
      _spokenText = text;
      _spokenEnd = 0;
      _spokenWord = '';
      _speechOffset = 0;
      _speaking = true;
    });
    await _tts.setSpeechRate(_speechRate);
    await _tts.speak(text);
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

  Future<void> _go(int nextPage) async {
    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;
    await _tts.stop();
    setState(() {
      _speaking = false;
      _spokenWord = '';
      _spokenEnd = 0;
      _speechOffset = 0;
    });
    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);
  }

  double get _readingProgress => _spokenText.isEmpty ? 0 : (_spokenEnd / _spokenText.length).clamp(0.0, 1.0);

  String get _typedText {
    if (_spokenText.isEmpty || _spokenEnd <= 0) return '';
    final end = _spokenEnd > _spokenText.length ? _spokenText.length : _spokenEnd;
    return _spokenText.substring(0, end).trim();
  }

  Widget _pdfView() {
    return PdfViewer.file(
      widget.filePath,
      controller: _pdfController,
      initialPageNumber: widget.initialPage,
      params: PdfViewerParams(
        margin: 8,
        pageOverlaysBuilder: (context, pageRect, pdfPage) {
          if (pdfPage.pageNumber != _page || (!_speaking && _spokenWord.isEmpty)) return const [];
          return [
            Positioned(
              left: pageRect.left + 12,
              right: pageRect.right > pageRect.left ? MediaQuery.sizeOf(context).width - pageRect.right + 12 : 12,
              top: pageRect.top + 12,
              child: IgnorePointer(
                child: Card(
                  elevation: 1,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [const Icon(Icons.graphic_eq_rounded, size: 18), const SizedBox(width: 8), Expanded(child: Text(_spokenWord.isEmpty ? 'بدء القراءة...' : _spokenWord, maxLines: 1, overflow: TextOverflow.ellipsis))]),
                        const SizedBox(height: 6),
                        LinearProgressIndicator(value: _readingProgress),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ];
        },
        onViewerReady: (document, controller) {
          if (mounted) setState(() => _pageCount = controller.pageCount);
        },
        onPageChanged: (pageNumber) {
          if (pageNumber == null) return;
          setState(() => _page = pageNumber);
          _savePage(pageNumber);
        },
      ),
    );
  }

  Widget _translationPane() {
    final text = _translations[_page];
    return Container(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      padding: const EdgeInsets.all(18),
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: text == null
            ? Center(child: _busy ? const CircularProgressIndicator() : FilledButton.icon(onPressed: _translatePage, icon: const Icon(Icons.translate), label: const Text('ترجمة الصفحة الحالية')))
            : SingleChildScrollView(child: SelectableText(text, style: const TextStyle(fontSize: 18, height: 1.8))),
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
        return Column(children: [Expanded(flex: 3, child: _pdfView()), Expanded(flex: 2, child: _translationPane())]);
      case TranslationLayout.sideBySide:
        return Row(children: [Expanded(child: _pdfView()), const VerticalDivider(width: 1), Expanded(child: _translationPane())]);
      case TranslationLayout.bottomSheet:
        return Stack(
          children: [
            Positioned.fill(child: _pdfView()),
            Align(
              alignment: Alignment.bottomCenter,
              child: DraggableScrollableSheet(
                initialChildSize: .20,
                minChildSize: .12,
                maxChildSize: .80,
                builder: (context, controller) => Material(
                  elevation: 8,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    children: [
                      const Padding(padding: EdgeInsets.only(top: 8), child: SizedBox(width: 42, child: Divider(thickness: 4))),
                      Expanded(child: SingleChildScrollView(controller: controller, child: SizedBox(height: MediaQuery.sizeOf(context).height * .65, child: _translationPane()))),
                    ],
                  ),
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
    final visibleRate = _speechRate * 2;
    return Scaffold(
      appBar: AppBar(
        title: Text(_pageCount == 0 ? 'PDF Reader' : 'Page $_page / $_pageCount'),
        actions: [
          PopupMenuButton<TranslationLayout>(
            tooltip: 'طريقة عرض الترجمة',
            icon: const Icon(Icons.view_quilt_outlined),
            initialValue: _layout,
            onSelected: (value) => setState(() => _layout = value),
            itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList(),
          ),
        ],
      ),
      body: _body(),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (_speaking || _typedText.isNotEmpty)
                Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(maxHeight: 82),
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(color: Theme.of(context).colorScheme.surfaceContainerHigh, borderRadius: BorderRadius.circular(14)),
                  child: SingleChildScrollView(reverse: true, child: Text(_typedText.isEmpty ? '...' : _typedText, textDirection: TextDirection.ltr, style: const TextStyle(fontSize: 16, height: 1.4))),
                ),
              Row(
                children: [
                  IconButton(onPressed: _speechRate > .25 ? () => _setRate(_speechRate - .05) : null, icon: const Icon(Icons.remove_circle_outline), tooltip: 'أبطأ'),
                  SizedBox(width: 46, child: Text('${visibleRate.toStringAsFixed(1)}x', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold))),
                  Expanded(child: Slider(min: .25, max: 1.0, divisions: 15, value: _speechRate, label: '${visibleRate.toStringAsFixed(1)}x', onChanged: (value) => setState(() => _speechRate = value), onChangeEnd: _setRate)),
                  IconButton(onPressed: _speechRate < 1.0 ? () => _setRate(_speechRate + .05) : null, icon: const Icon(Icons.add_circle_outline), tooltip: 'أسرع'),
                ],
              ),
              Wrap(
                spacing: 4,
                runSpacing: 2,
                alignment: WrapAlignment.center,
                children: [0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0].map((speed) => _SpeedPreset(speed: speed)).toList(),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  IconButton.filledTonal(onPressed: _page > 1 ? () => _go(_page - 1) : null, icon: const Icon(Icons.chevron_left)),
                  const SizedBox(width: 6),
                  Expanded(child: FilledButton.tonalIcon(onPressed: _toggleSpeech, icon: Icon(_speaking ? Icons.stop_circle_outlined : Icons.volume_up_outlined), label: Text(_speaking ? 'إيقاف القراءة' : 'قراءة الصفحة'))),
                  const SizedBox(width: 6),
                  Expanded(child: FilledButton.icon(onPressed: _busy ? null : _translatePage, icon: const Icon(Icons.translate), label: const Text('ترجمة'))),
                  const SizedBox(width: 6),
                  IconButton.filledTonal(onPressed: _page < _pageCount ? () => _go(_page + 1) : null, icon: const Icon(Icons.chevron_right)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SpeedPreset extends StatelessWidget {
  const _SpeedPreset({required this.speed});
  final double speed;

  @override
  Widget build(BuildContext context) {
    final reader = context.findAncestorStateOfType<_ReaderScreenState>();
    final selected = reader != null && ((reader._speechRate * 2) - speed).abs() < .01;
    return ChoiceChip(
      label: Text('${speed.toStringAsFixed(1)}x'),
      selected: selected,
      visualDensity: VisualDensity.compact,
      onSelected: reader == null ? null : (_) => reader._setRate(speed / 2),
    );
  }
}
