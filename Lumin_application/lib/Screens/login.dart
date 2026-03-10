import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/home/home_page.dart';
import 'package:lumin_application/Screens/signup.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../Widgets/gradient_background.dart';
import '../theme/app_colors.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailC = TextEditingController();
  final _passC = TextEditingController();

  bool _obscurePassword = true;
  bool _loading = false;

  static const double _gap12 = 12;
  static const double _gap20 = 20;

  @override
  void dispose() {
    _emailC.dispose();
    _passC.dispose();
    super.dispose();
  }

  // ✅ Your styled in-app message (SnackBar)
  void _showMessage(String message, {bool isError = true}) {
    final snackBar = SnackBar(
      behavior: SnackBarBehavior.floating,
      elevation: 8,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      backgroundColor: const Color(0xFF0F2A33), // dark teal
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: isError ? Colors.redAccent : AppColors.button,
          width: 1.4,
        ),
      ),
      duration: const Duration(seconds: 3),
      content: Row(
        children: [
          Icon(
            isError ? Icons.error_outline : Icons.check_circle_outline,
            color: isError ? Colors.redAccent : AppColors.button,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );

    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(snackBar);
  }

  // ✅ Simple email format check (optional but nice UX)
  bool _isValidEmail(String email) {
    final emailRegex = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');
    return emailRegex.hasMatch(email);
  }

  String _friendlyLoginError(AuthException e) {
    final m = e.message.toLowerCase();

    // Supabase often returns generic messages for security
    if (m.contains('invalid login credentials') ||
        m.contains('invalid') ||
        m.contains('credentials')) {
      return 'Email or password is incorrect.';
    }

    if (m.contains('email not confirmed')) {
      return 'Please verify your email address first (check your inbox/spam).';
    }

    if (m.contains('too many requests')) {
      return 'Too many attempts. Please wait a moment and try again.';
    }

    // fallback
    return 'Sign in failed. Please try again.';
  }

  Future<void> _login() async {
    final email = _emailC.text.trim();
    final pass = _passC.text;

    if (email.isEmpty || pass.isEmpty) {
      _showMessage('Please enter your email and password.');
      return;
    }

    if (!_isValidEmail(email)) {
      _showMessage('Please enter a valid email address.');
      return;
    }

    setState(() => _loading = true);

    try {
      await Supabase.instance.client.auth.signInWithPassword(
        email: email,
        password: pass,
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const HomePage()),
      );
    } on AuthException catch (e) {
      _showMessage(_friendlyLoginError(e));
    } catch (_) {
      _showMessage('Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resetPassword() async {
    final email = _emailC.text.trim();

    if (email.isEmpty) {
      _showMessage('Please enter your email first.');
      return;
    }

    if (!_isValidEmail(email)) {
      _showMessage('Please enter a valid email address.');
      return;
    }

    setState(() => _loading = true);

    try {
      await Supabase.instance.client.auth.resetPasswordForEmail(email);

      if (!mounted) return;

      // ✅ Safe & professional (prevents email enumeration)
      _showMessage(
        'If this email is registered, a password reset link has been sent.',
        isError: false,
      );
    } on AuthException catch (e) {
      final m = e.message.toLowerCase();

      if (m.contains('too many requests')) {
        _showMessage('Too many requests. Please wait and try again.');
      } else {
        _showMessage('Could not send reset email. Please try again.');
      }
    } catch (_) {
      _showMessage('Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Image.asset('assets/images/Lumin_logo.png', height: 120),

                  const SizedBox(height: 20),

                  const Text(
                    'Sign in to your\nAccount',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      height: 1.15,
                    ),
                  ),

                  const SizedBox(height: 10),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        "Don't have an account? ",
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                      GestureDetector(
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const SignupPage()),
                        ),
                        child: const Text(
                          'Sign up',
                          style: TextStyle(
                            color: AppColors.button,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: _gap20),

                  // Email
                  _field(
                    TextField(
                      controller: _emailC,
                      keyboardType: TextInputType.emailAddress,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                      cursorColor: Colors.white,
                      decoration: const InputDecoration(
                        hintText: 'Email address',
                        hintStyle: TextStyle(color: Colors.white54),
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                    ),
                  ),

                  const SizedBox(height: _gap12),

                  // Password
                  _field(
                    TextField(
                      controller: _passC,
                      obscureText: _obscurePassword,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                      cursorColor: Colors.white,
                      decoration: InputDecoration(
                        hintText: 'Password',
                        hintStyle: const TextStyle(color: Colors.white54),
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          onPressed: () =>
                              setState(() => _obscurePassword = !_obscurePassword),
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                            color: _obscurePassword
                                ? Colors.white54
                                : AppColors.button,
                          ),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: _gap12),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Forgot password? ',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      GestureDetector(
                        onTap: _loading ? null : _resetPassword,
                        child: const Text(
                          'Click here',
                          style: TextStyle(
                            color: AppColors.button,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: _gap20),

                  SizedBox(
                    width: double.infinity,
                    height: 55,
                    child: ElevatedButton(
                      onPressed: _loading ? null : _login,
                      child: _loading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(strokeWidth: 2,color: AppColors.mint,),
                            )
                          : const Text(
                              'Log In',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(Widget child) => SizedBox(height: 50, child: child);
}