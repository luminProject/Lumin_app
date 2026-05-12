import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/splash/splash_page.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:lumin_application/Screens/home/home_page.dart';

/// AuthGate decides which screen to show based on the user's auth state.
///
/// - Logged in  → HomePage
/// - Logged out → SplashPage
///
/// Also saves the FCM token to Supabase once after each sign-in,
/// so the backend can send push notifications to this device.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  // Prevents saving the FCM token more than once per session.
  bool _tokenSaved = false;

  @override
  void initState() {
    super.initState();

    // Listen for auth events once.
    // On sign-in: save the FCM token to Supabase.
    // On sign-out: reset the flag so the token saves again on the next login.
    Supabase.instance.client.auth.onAuthStateChange.listen((data) {
      final event   = data.event;
      final session = data.session;

      if (event == AuthChangeEvent.signedIn && session != null && !_tokenSaved) {
        _tokenSaved = true;
        _saveFcmToken(session.user.id);
      }

      if (event == AuthChangeEvent.signedOut) {
        _tokenSaved = false;
      }
    });
  }

  /// Gets the device FCM token from Firebase and saves it to the users table.
  /// Called once after sign-in to enable push notifications for this device.
  Future<void> _saveFcmToken(String userId) async {
    try {
      final token = await FirebaseMessaging.instance.getToken();

      if (token == null) return;

      await Supabase.instance.client
          .from('users')
          .update({'fcm_token': token})
          .eq('user_id', userId);

    } catch (e) {
      debugPrint('FCM token save error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        // Show loading indicator while waiting for auth state.
        if (!snapshot.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final session = Supabase.instance.client.auth.currentSession;

        // Route based on session.
        if (session != null) return const HomePage();
        return const SplashPage();
      },
    );
  }
}