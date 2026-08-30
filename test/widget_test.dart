import 'package:flutter_test/flutter_test.dart';
import 'package:pdf_reader/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('first launch shows onboarding', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.pumpWidget(const PdfReaderApp());
    await tester.pumpAndSettle();

    expect(find.text('كتبك معك دائمًا'), findsOneWidget);
    expect(find.text('التالي'), findsOneWidget);
  });

  testWidgets('returning user reaches library', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{'onboardingSeen': true});
    await tester.pumpWidget(const PdfReaderApp());
    await tester.pumpAndSettle();

    expect(find.text('قارئ الكتب'), findsOneWidget);
    expect(find.text('مكتبتي'), findsOneWidget);
    expect(find.text('اختر كتاب PDF'), findsOneWidget);
  });
}
