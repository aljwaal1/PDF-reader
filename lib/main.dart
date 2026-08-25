import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:google_mlkit_translation/google_mlkit_translation.dart';
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
      home: const LibraryScreen(),
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

  @override
  void initState() {
    super.initState();
    _loadState();
  }

  Future<void> _loadState() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _lastBook = prefs.getString('lastBook');
      _lastPage = prefs.getInt('lastPage') ?? 1;
    });
  }

  Future<void> _pickPdf() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );
    final path = result?.files.single.path;
    if (path == null || !mounted) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lastBook', path);
    await prefs.setInt('lastPage', 1);
    if (!mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ReaderScreen(filePath: path, initialPage: 1)),
    );
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
              onPressed: _pickPdf,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Text('فتح كتاب PDF'),
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
                    MaterialPageRoute(
                      builder: (_) => ReaderScreen(filePath: _lastBook!, initialPage: _lastPage),
                    ),
                  ),
                ),
              ),
            ],
            const Spacer(),
            Text(
              'اقرأ الكتاب الإنجليزي، استمع إليه، واعرض الترجمة العربية بالطريقة التي تناسبك.',
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
    if (mounted) setState(() => _speaking = true);
    await _tts.speak(text);
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
    setState(() => _speaking = false);
    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);
  }

  Widget _pdfView() {
    return PdfViewer.file(
      widget.filePath,
      controller: _pdfController,
      initialPageNumber: widget.initialPage,
      params: PdfViewerParams(
        margin: 8,
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
            : SingleChildScrollView(
                child: SelectableText(text, style: const TextStyle(fontSize: 18, height: 1.8)),
              ),
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
                      const Padding(
                        padding: EdgeInsets.only(top: 8),
                        child: SizedBox(width: 42, child: Divider(thickness: 4)),
                      ),
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
            itemBuilder: (_) => TranslationLayout.values
                .map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value))))
                .toList(),
          ),
        ],
      ),
      body: _body(),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
          child: Row(
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
        ),
      ),
      floatingActionButton: PopupMenuButton<double>(
        tooltip: 'سرعة القراءة',
        onSelected: (value) async {
          setState(() => _speechRate = value);
          await _tts.setSpeechRate(value);
        },
        itemBuilder: (_) => const [
          PopupMenuItem(value: .35, child: Text('0.7x')),
          PopupMenuItem(value: .5, child: Text('1.0x')),
          PopupMenuItem(value: .65, child: Text('1.3x')),
          PopupMenuItem(value: .8, child: Text('1.6x')),
        ],
        child: FloatingActionButton.small(onPressed: null, child: Text('${(_speechRate * 2).toStringAsFixed(1)}x')),
      ),
    );
  }
}
