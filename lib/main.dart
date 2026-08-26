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
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5B5FEF)),
        useMaterial3: true,
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
    (Icons.menu_book_rounded, 'كتبك معك دائمًا', 'اختر ملف PDF وسيتم حفظ نسخة منه داخل التطبيق لتعود إليه بسهولة حتى على الأجهزة القديمة.'),
    (Icons.record_voice_over_rounded, 'استمع وتابع القراءة', 'استمع للنص الإنجليزي مع مؤشر للكلمة الحالية ونص متحرك يساعدك على متابعة مكان القراءة.'),
    (Icons.translate_rounded, 'ترجمة عربية مرنة', 'ترجم الصفحة الحالية واختر عرض الترجمة أسفل الصفحة أو بجانبها أو في نافذة قابلة للسحب.'),
    (Icons.speed_rounded, 'تحكم كامل بالسرعة', 'ارفع أو خفّض سرعة النطق مباشرة أثناء القراءة من شريط تحكم واضح وسريع.'),
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
                          width: 116,
                          height: 116,
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(32),
                          ),
                          child: Icon(card.$1, size: 58, color: Theme.of(context).colorScheme.primary),
                        ),
                        const SizedBox(height: 34),
                        Text(card.$2, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
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
                  width: index == _page ? 24 : 8,
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
                  onPressed: last
                      ? _finish
                      : () => _controller.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
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
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => ReaderScreen(filePath: path, initialPage: 1)));
    } catch (_) {
      _message('لم نتمكن من فتح الكتاب. تأكد أن الملف PDF صالح ثم حاول مرة أخرى.');
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('مكتبتي')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            FilledButton.icon(
              onPressed: _importing ? null : _pickPdf,
              icon: _importing
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.picture_as_pdf_outlined),
              label: Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: Text(_importing ? 'جاري إضافة الكتاب...' : 'إضافة كتاب PDF'),
              ),
            ),
            if (_lastBook != null) ...[
              const SizedBox(height: 24),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.menu_book_rounded),
                  title: const Text('متابعة آخر كتاب'),
                  subtitle: Text('الصفحة $_lastPage'),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => ReaderScreen(filePath: _lastBook!, initialPage: _lastPage)),
                  ),
                ),
              ),
            ],
            const Spacer(),
            Text(
              'الكتاب الذي تضيفه يُحفظ داخل التطبيق لقراءة أكثر استقرارًا على مختلف الأجهزة.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey.shade600),
            ),
          ],
        ),
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
  final OnDeviceTranslator _translator = OnDeviceTranslator(
    sourceLanguage: TranslateLanguage.english,
    targetLanguage: TranslateLanguage.arabic,
  );
  final OnDeviceTranslatorModelManager _modelManager = OnDeviceTranslatorModelManager();

  final Map<int, String> _pageText = {};
  final Map<int, String> _translations = {};

  int _page = 1;
  int _pageCount = 0;
  bool _busy = false;
  bool _speaking = false;
  double _speechRate = 0.5;
  String _spokenText = '';
  String _spokenWord = '';
  int _spokenEnd = 0;
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
      setState(() {
        _spokenText = text;
        _spokenWord = word;
        _spokenEnd = end;
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
    if (_translations.containsKey(_page)) {
      setState(() {});
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
      if (!mounted) return;
      setState(() => _translations[_page] = translated);
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
    await _tts.setSpeechRate(_speechRate);
    if (mounted) {
      setState(() {
        _speaking = true;
        _spokenText = text;
        _spokenEnd = 0;
        _spokenWord = '';
      });
    }
    await _tts.speak(text);
  }

  Future<void> _setRate(double value) async {
    final rate = value.clamp(0.30, 0.90).toDouble();
    setState(() => _speechRate = rate);
    await _tts.setSpeechRate(rate);
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
    });
    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);
  }

  double get _readingProgress {
    if (_spokenText.isEmpty) return 0;
    return (_spokenEnd / _spokenText.length).clamp(0.0, 1.0);
  }

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
                        Row(
                          children: [
                            const Icon(Icons.graphic_eq_rounded, size: 18),
                            const SizedBox(width: 8),
                            Expanded(child: Text(_spokenWord.isEmpty ? 'بدء القراءة...' : _spokenWord, maxLines: 1, overflow: TextOverflow.ellipsis)),
                          ],
                        ),
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
          if (!mounted) return;
          setState(() => _pageCount = controller.pageCount);
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
            ? Center(
                child: _busy
                    ? const CircularProgressIndicator()
                    : FilledButton.icon(
                        onPressed: _translatePage,
                        icon: const Icon(Icons.translate),
                        label: const Text('ترجمة الصفحة الحالية'),
                      ),
              )
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
                initialChildSize: 0.20,
                minChildSize: 0.12,
                maxChildSize: 0.80,
                builder: (context, controller) => Material(
                  elevation: 8,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    children: [
                      const Padding(padding: EdgeInsets.only(top: 8), child: SizedBox(width: 42, child: Divider(thickness: 4))),
                      Expanded(
                        child: SingleChildScrollView(
                          controller: controller,
                          child: SizedBox(height: MediaQuery.sizeOf(context).height * .65, child: _translationPane()),
                        ),
                      ),
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
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: SingleChildScrollView(
                    reverse: true,
                    child: Text(_typedText.isEmpty ? '...' : _typedText, textDirection: TextDirection.ltr, style: const TextStyle(fontSize: 16, height: 1.4)),
                  ),
                ),
              Row(
                children: [
                  IconButton(onPressed: () => _setRate(_speechRate - .05), icon: const Icon(Icons.remove_circle_outline), tooltip: 'أبطأ'),
                  Text('${(_speechRate * 2).toStringAsFixed(1)}x', style: const TextStyle(fontWeight: FontWeight.bold)),
                  Expanded(
                    child: Slider(
                      min: .30,
                      max: .90,
                      divisions: 12,
                      value: _speechRate,
                      onChanged: _setRate,
                    ),
                  ),
                  IconButton(onPressed: () => _setRate(_speechRate + .05), icon: const Icon(Icons.add_circle_outline), tooltip: 'أسرع'),
                ],
              ),
              Row(
                children: [
                  IconButton.filledTonal(onPressed: _page > 1 ? () => _go(_page - 1) : null, icon: const Icon(Icons.chevron_left)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: FilledButton.tonalIcon(
                      onPressed: _toggleSpeech,
                      icon: Icon(_speaking ? Icons.stop_circle_outlined : Icons.volume_up_outlined),
                      label: Text(_speaking ? 'إيقاف القراءة' : 'قراءة الصفحة'),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _busy ? null : _translatePage,
                      icon: const Icon(Icons.translate),
                      label: const Text('ترجمة'),
                    ),
                  ),
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
