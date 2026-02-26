import 'package:flutter/material.dart';
import 'package:lumin_application/Screens/login.dart';
import '../theme/app_colors.dart';
import '../Widgets/gradient_background.dart';

// ✅ NEW
import 'package:intl_phone_field/intl_phone_field.dart';

// ✅ Supabase
import 'package:supabase_flutter/supabase_flutter.dart';

class SignupPage extends StatefulWidget {
  const SignupPage({super.key});

  @override
  State<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage> {
  // 🔤 Controllers
  final _usernameC = TextEditingController();
  final _emailC = TextEditingController();
  final _passwordC = TextEditingController();
  final _confirmPasswordC = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  String _energySource = 'Grid + Solar';
  bool _hasSolarPanels = true;

  // ✅ نخزن الرقم النهائي هنا
  String _fullPhone = '';

  bool _loading = false;

  static const double _gap12 = 12;
  static const double _gap16 = 20; // ✅ كانت 16
  static const double _gap18 = 18;

  @override
  void dispose() {
    _usernameC.dispose();
    _emailC.dispose();
    _passwordC.dispose();
    _confirmPasswordC.dispose();
    super.dispose();
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg)),
    );
  }

  bool _isValidEmail(String email) {
    // بسيط وعملي للمشروع
    final regex = RegExp(r'^[^@]+@[^@]+\.[^@]+$');
    return regex.hasMatch(email);
  }

  Future<void> _createAccount() async {
    final username = _usernameC.text.trim();
    final email = _emailC.text.trim();
    final password = _passwordC.text;
    final confirm = _confirmPasswordC.text;

    if (username.isEmpty) return _snack('Please enter username');
    if (email.isEmpty) return _snack('Please enter email');
    if (!_isValidEmail(email)) return _snack('Please enter a valid email');
    if (_fullPhone.trim().isEmpty) return _snack('Please enter phone number');
    if (password.isEmpty) return _snack('Please enter password');
    if (password.length < 6) return _snack('Password must be at least 6 characters');
    if (confirm.isEmpty) return _snack('Please confirm password');
    if (password != confirm) return _snack("Passwords don't match");

    setState(() => _loading = true);
    try {
      await Supabase.instance.client.auth.signUp(
        email: email,
        password: password,
        data: {
          'username': username,
          'phone': _fullPhone,
          'energy_source': _energySource,
          'has_solar_panels': _hasSolarPanels,
        },
      );

      if (!mounted) return;

      _snack('Account created ✅ Please check your email if verification is enabled.');

      // يرجع للـ Login
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginPage()),
      );
    } on AuthException catch (e) {
      // رسائل Supabase واضحة غالبًا
      _snack(e.message);
    } catch (_) {
      _snack('Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GradientBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                const SizedBox(height: 20),

                /// ✅ Logo
                Center(
                  child: Image.asset(
                    'assets/images/Lumin_logo.png',
                    height: 105,
                    fit: BoxFit.contain,
                  ),
                ),

                const SizedBox(height: 18),

                /// Card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: Colors.white.withOpacity(0.06)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Create account',
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 6),

                      Row(
                        children: [
                          const Text(
                            'Already have an account? ',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                          GestureDetector(
                            onTap: () {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(builder: (_) => const LoginPage()),
                              );
                            },
                            child: const Text(
                              'Login',
                              style: TextStyle(
                                color: AppColors.button,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: _gap18),

                      // Username
                      _field(
                        TextField(
                          controller: _usernameC,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                          cursorColor: Colors.white,
                          decoration: InputDecoration(
                            hintText: 'Username',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                            prefixIcon: const Icon(Icons.person_outline),
                          ),
                        ),
                      ),
                      const SizedBox(height: _gap16),

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
                          decoration: InputDecoration(
                            hintText: 'Email address',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                            prefixIcon: const Icon(Icons.email_outlined),
                          ),
                        ),
                      ),
                      const SizedBox(height: _gap16),

                      // ✅ Phone field
                      _field(
                        IntlPhoneField(
                          initialCountryCode: 'SA',
                          disableLengthCheck: true,
                          cursorColor: Colors.white,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                          dropdownTextStyle: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                          dropdownIcon: Icon(
                            Icons.keyboard_arrow_down,
                            color: Colors.white.withOpacity(0.6),
                          ),
                          decoration: InputDecoration(
                            hintText: 'Phone number',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                            prefixIcon: const Icon(Icons.phone_outlined),
                          ),
                          onChanged: (phone) {
                            _fullPhone = phone.completeNumber;
                          },
                        ),
                      ),
                      const SizedBox(height: _gap16),

                      /// 🔐 Password
                      _field(
                        TextField(
                          controller: _passwordC,
                          obscureText: _obscurePassword,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                          cursorColor: Colors.white,
                          decoration: InputDecoration(
                            hintText: 'Password',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: IconButton(
                              onPressed: () =>
                                  setState(() => _obscurePassword = !_obscurePassword),
                              icon: Icon(
                                _obscurePassword
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                                color: _obscurePassword ? Colors.white54 : AppColors.button,
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: _gap16),

                      /// 🔐 Confirm Password
                      _field(
                        TextField(
                          controller: _confirmPasswordC,
                          obscureText: _obscureConfirmPassword,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                          cursorColor: Colors.white,
                          decoration: InputDecoration(
                            hintText: 'Confirm password',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: IconButton(
                              onPressed: () => setState(
                                  () => _obscureConfirmPassword = !_obscureConfirmPassword),
                              icon: Icon(
                                _obscureConfirmPassword
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                                color:
                                    _obscureConfirmPassword ? Colors.white54 : AppColors.button,
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: _gap18),

                      const Text(
                        'Energy Source Type',
                        style: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: _gap12),

                      _buildEnergyOption('Grid only'),
                      const SizedBox(height: 10),
                      _buildEnergyOption('Grid + Solar'),

                      const SizedBox(height: _gap18),

                      if (_energySource == 'Grid + Solar') ...[
                        _buildSolarPanelSelection(),
                        const SizedBox(height: _gap18),
                      ],

                      /// ✅ Button
                      SizedBox(
                        width: double.infinity,
                        height: 55,
                        child: ElevatedButton(
                          onPressed: _loading ? null : _createAccount,
                          child: _loading
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text(
                                  'Create Account',
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

                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(Widget child) => SizedBox(height: 50, child: child);

  Widget _buildEnergyOption(String title) {
    final bool isSelected = _energySource == title;

    return GestureDetector(
      onTap: () => setState(() => _energySource = title),
      child: Container(
        height: 48,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.button.withOpacity(0.22)
              : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppColors.button : Colors.transparent,
          ),
        ),
        child: Row(
          children: [
            Icon(
              isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
              color: isSelected ? AppColors.button : Colors.white.withOpacity(0.45),
            ),
            const SizedBox(width: 12),
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSolarPanelSelection() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Do you have solar panels installed?',
            style: TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _hasSolarPanels = true),
                  child: Container(
                    height: 40,
                    decoration: BoxDecoration(
                      color: _hasSolarPanels
                          ? AppColors.button
                          : Colors.white.withOpacity(0.10),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: const Text(
                      'Yes',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _hasSolarPanels = false),
                  child: Container(
                    height: 40,
                    decoration: BoxDecoration(
                      color: !_hasSolarPanels
                          ? AppColors.button
                          : Colors.white.withOpacity(0.10),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: const Text(
                      'No',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Enables solar monitoring and predictions.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.45),
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}