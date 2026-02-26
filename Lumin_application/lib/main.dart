import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:lumin_application/Screens/splash/splash_page.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://ldjnsziefmnckdtiqlmz.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxkam5zemllZm1uY2tkdGlxbG16Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwODk3ODgsImV4cCI6MjA4NjY2NTc4OH0.9s0p2VKyS7fuhd9DrDlTj7_BQDb2wjdUR1_Ay9qLuyo',
  );

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const SplashPage(),
    );
  }
}