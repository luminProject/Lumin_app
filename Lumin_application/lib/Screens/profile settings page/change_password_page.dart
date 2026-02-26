import 'package:flutter/material.dart';
import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/theme/app_colors.dart';

class ChangePasswordPage extends StatefulWidget {
  const ChangePasswordPage({super.key});

  @override
  State<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends State<ChangePasswordPage> {
  bool _oldObscure = true;
  bool _newObscure = true;
  bool _confirmObscure = true;

  static const double _gap12 = 12;
  static const double _gap16 = 16;
  static const double _gap18 = 18;

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Change Password',
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),
        actions: const [],
        child: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Column(
            children: [
              const SizedBox(height: 150),

              GlassCard(
                radius: 22,
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Update your password',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                      ),
                    ),

                    const SizedBox(height: _gap18),

                    // Current Password
                    _field(
                      TextField(
                        obscureText: _oldObscure,
                        style: const TextStyle(
                          color: Colors.white, // ✅ النص أبيض
                          fontWeight: FontWeight.w600,
                        ),
                        cursorColor: Colors.white, // ✅ المؤشر أبيض
                        decoration: InputDecoration(
                          hintText: 'Current password',
                          hintStyle: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                          ),
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            onPressed: () =>
                                setState(() => _oldObscure = !_oldObscure),
                            icon: Icon(
                              _oldObscure
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color:
                                  _oldObscure ? Colors.white54 : AppColors.button,
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: _gap16),

                    // New Password
                    _field(
                      TextField(
                        obscureText: _newObscure,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                        cursorColor: Colors.white,
                        decoration: InputDecoration(
                          hintText: 'New password',
                          hintStyle: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                          ),
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            onPressed: () =>
                                setState(() => _newObscure = !_newObscure),
                            icon: Icon(
                              _newObscure
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color:
                                  _newObscure ? Colors.white54 : AppColors.button,
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: _gap16),

                    // Confirm Password
                    _field(
                      TextField(
                        obscureText: _confirmObscure,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                        cursorColor: Colors.white,
                        decoration: InputDecoration(
                          hintText: 'Confirm new password',
                          hintStyle: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                          ),
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            onPressed: () =>
                                setState(() => _confirmObscure = !_confirmObscure),
                            icon: Icon(
                              _confirmObscure
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: _confirmObscure
                                  ? Colors.white54
                                  : AppColors.button,
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: _gap18),

                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: const Text('UI only for now ✨'),
                              backgroundColor: AppColors.button,
                            ),
                          );
                        },
                        child: const Text(
                          'Save Changes',
                          style: TextStyle(
                              fontSize: 15.5, fontWeight: FontWeight.w900),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(Widget child) => SizedBox(height: 52, child: child);
}