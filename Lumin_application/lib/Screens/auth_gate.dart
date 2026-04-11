import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/splash/splash_page.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'package:lumin_application/Screens/home/home_page.dart';

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  Future<void> _saveFcmToken(String userId) async {
    try {
      debugPrint('FCM: Getting token for user $userId...');
      final token = await FirebaseMessaging.instance.getToken();
      debugPrint('FCM: Token = $token');

      if (token == null) {
        debugPrint('FCM: Token is null! Cannot save.');
        return;
      }

      await Supabase.instance.client
          .from('users')
          .update({'fcm_token': token})
          .eq('user_id', userId);

      debugPrint('FCM: Token saved successfully!');
    } catch (e) {
      debugPrint('FCM token save error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final session = Supabase.instance.client.auth.currentSession;

        if (session != null) {
          // حفظ الـ FCM token بعد تأكيد الـ session
          _saveFcmToken(session.user.id);
          return const HomePage();
        }

        return const SplashPage();
      },
    );
  }
}