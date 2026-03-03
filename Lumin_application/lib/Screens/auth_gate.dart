import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/splash/splash_page.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:lumin_application/Screens/home/home_page.dart';

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        // ✅ أول ما يفتح التطبيق: نعرض loading بسيط لين Supabase يرجع لنا الجلسة
        if (!snapshot.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final session = Supabase.instance.client.auth.currentSession;

        // ✅ إذا فيه Session => المستخدم مسجل دخول
        if (session != null) {
          return const HomePage();
        }

        // ✅ إذا ما فيه Session => Login
        return const SplashPage();
      },
    );
  }
}