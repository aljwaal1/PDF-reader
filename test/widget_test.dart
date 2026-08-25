import 'package:flutter_test/flutter_test.dart';
import 'package:pdf_reader/main.dart';

void main() {
  testWidgets('PDF Reader app starts', (WidgetTester tester) async {
    await tester.pumpWidget(const PdfReaderApp());
    expect(find.text('مكتبتي'), findsOneWidget);
    expect(find.text('فتح كتاب PDF'), findsOneWidget);
  });
}
