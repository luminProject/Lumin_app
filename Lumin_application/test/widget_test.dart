import 'package:flutter_test/flutter_test.dart';
import 'package:lumin_application/main.dart';

void main() {
  testWidgets('shows device tester interface', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('Device Classes Tester'), findsOneWidget);
    expect(find.text('Create Consumption Device'), findsOneWidget);
    expect(find.text('Create Production Device'), findsOneWidget);
    expect(find.text('Collect Sensor Data'), findsOneWidget);
  });
}
