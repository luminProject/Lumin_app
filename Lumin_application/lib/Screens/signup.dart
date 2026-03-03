import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lumin_application/Screens/login.dart';
import '../theme/app_colors.dart';
import '../Widgets/gradient_background.dart';

import 'package:intl_phone_field/intl_phone_field.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:geolocator/geolocator.dart';

class SignupPage extends StatefulWidget {
  const SignupPage({super.key});

  @override
  State<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends State<SignupPage> {
  final _usernameC = TextEditingController();
  final _emailC = TextEditingController();
  final _passwordC = TextEditingController();
  final _confirmPasswordC = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  String _energySource = 'Grid + Solar';
  bool _hasSolarPanels = true;

  String _fullPhone = '';
  bool _isPhoneValid = false; // ✅ phone validity (per selected country)
  bool _loading = false;

  // ✅ Password live rules
  bool _pwMin8 = false;
  bool _pwHasNumber = false;
  bool _pwHasSymbol = false;
  bool _showPasswordRules = false;

  static const double _gap12 = 12;
  static const double _gap16 = 20;
  static const double _gap18 = 18;

  static const String _defaultAvatarUrl =
      'https://www.pinterest.com/29bribri29/basic-pfp/';

  @override
  void initState() {
    super.initState();
    _passwordC.addListener(_updatePasswordRules);
  }

  @override
  void dispose() {
    _passwordC.removeListener(_updatePasswordRules);
    _usernameC.dispose();
    _emailC.dispose();
    _passwordC.dispose();
    _confirmPasswordC.dispose();
    super.dispose();
  }

  void _showMessage(String message, {bool isError = true}) {
    final snackBar = SnackBar(
      behavior: SnackBarBehavior.floating,
      elevation: 8,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      backgroundColor: const Color(0xFF0F2A33),
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

  bool _isValidEmail(String email) {
    final regex = RegExp(r'^[^@]+@[^@]+\.[^@]+$');
    return regex.hasMatch(email);
  }

  void _updatePasswordRules() {
    final p = _passwordC.text;

    final min8 = p.length >= 8;
    final hasNumber = RegExp(r'\d').hasMatch(p);
    final hasSymbol =
        RegExp(r'[!@#$%^&*(),.?":{}|<>_\-\\/\[\]=+;`~]').hasMatch(p);

    if (min8 != _pwMin8 || hasNumber != _pwHasNumber || hasSymbol != _pwHasSymbol) {
      setState(() {
        _pwMin8 = min8;
        _pwHasNumber = hasNumber;
        _pwHasSymbol = hasSymbol;
      });
    }
  }

  bool get _isPasswordStrong => _pwMin8 && _pwHasNumber && _pwHasSymbol;

  Future<Position> _requireLocationAndGet() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) {
      throw Exception('Please enable Location Services to continue.');
    }

    var permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied) {
      throw Exception('Location is required to create an account.');
    }

    if (permission == LocationPermission.deniedForever) {
      throw Exception(
        'Location permission is permanently denied. Enable it from Settings.',
      );
    }

    return Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  Future<void> _createAccount() async {
    final username = _usernameC.text.trim();
    final email = _emailC.text.trim();
    final password = _passwordC.text;
    final confirm = _confirmPasswordC.text;

    if (username.isEmpty) {
      _showMessage('Please enter username');
      return;
    }
    if (email.isEmpty) {
      _showMessage('Please enter email');
      return;
    }
    if (!_isValidEmail(email)) {
      _showMessage('Please enter a valid email');
      return;
    }

    if (_fullPhone.trim().isEmpty) {
      _showMessage('Please enter phone number');
      return;
    }

    if (!_isPhoneValid) {
      _showMessage('Please enter a valid phone number for the selected country.');
      return;
    }

    final cleaned = _fullPhone.replaceAll('+', '').replaceAll(' ', '');
    if (!RegExp(r'^\d+$').hasMatch(cleaned)) {
      _showMessage('Phone number must contain digits only.');
      return;
    }

    if (password.isEmpty) {
      _showMessage('Please enter password');
      return;
    }

    if (!_isPasswordStrong) {
      setState(() => _showPasswordRules = true);
      _showMessage('Please use a stronger password (see requirements below).');
      return;
    }

    if (confirm.isEmpty) {
      _showMessage('Please confirm password');
      return;
    }
    if (password != confirm) {
      _showMessage("Passwords don't match");
      return;
    }

    setState(() => _loading = true);

    try {
      final pos = await _requireLocationAndGet();

      final res = await Supabase.instance.client.auth.signUp(
        email: email,
        password: password,
      );

      final user = res.user;

      if (user == null) {
        _showMessage(
          'Check your email to confirm your account, then log in.',
          isError: false,
        );
        return;
      }

      await Supabase.instance.client.from('users').upsert({
        'user_id': user.id,
        'username': username,
        'phone_number': _fullPhone,
        'location': null,
        'avatar_url': _defaultAvatarUrl,
        'latitude': pos.latitude,
        'longitude': pos.longitude,
        'energy_source': _energySource,
        'has_solar_panels': _hasSolarPanels,
      });

      if (!mounted) return;

      _showMessage('Account created ✅', isError: false);

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginPage()),
      );
    } on AuthException catch (e) {
      final msg = e.message.toLowerCase();
      if (msg.contains('already') || msg.contains('registered') || msg.contains('exists')) {
        _showMessage('This email is already registered. Please use another email.');
      } else {
        _showMessage(e.message);
      }
    } on PostgrestException catch (e) {
      _showMessage(e.message);
    } catch (e) {
      _showMessage(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: GradientBackground(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: IntrinsicHeight(
                    child: Column(
                      children: [
                        const SizedBox(height: 20),

                        Center(
                          child: Image.asset(
                            'assets/images/Lumin_logo.png',
                            height: 105,
                            fit: BoxFit.contain,
                          ),
                        ),

                        const SizedBox(height: 18),

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

                              _field(
                                IntlPhoneField(
                                  initialCountryCode: 'SA',
                                  keyboardType: TextInputType.phone,
                                  // ✅ NEW: prevent letters/symbols (digits only)
                                  inputFormatters:  [
                                    FilteringTextInputFormatter.digitsOnly,
                                  ],
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
                                    _isPhoneValid = phone.isValidNumber();
                                  },
                                ),
                              ),
                              const SizedBox(height: _gap16),

                              _field(
                                Focus(
                                  onFocusChange: (hasFocus) {
                                    if (hasFocus) {
                                      setState(() => _showPasswordRules = true);
                                    }
                                  },
                                  child: TextField(
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
                                          color: _obscurePassword
                                              ? Colors.white54
                                              : AppColors.button,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),

                              AnimatedCrossFade(
                                firstChild: const SizedBox(height: 0),
                                secondChild: Padding(
                                  padding: const EdgeInsets.only(top: 10),
                                  child: _PasswordRules(
                                    min8: _pwMin8,
                                    hasNumber: _pwHasNumber,
                                    hasSymbol: _pwHasSymbol,
                                  ),
                                ),
                                crossFadeState: _showPasswordRules
                                    ? CrossFadeState.showSecond
                                    : CrossFadeState.showFirst,
                                duration: const Duration(milliseconds: 180),
                              ),

                              const SizedBox(height: _gap16),

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
                                      onPressed: () => setState(() =>
                                          _obscureConfirmPassword = !_obscureConfirmPassword),
                                      icon: Icon(
                                        _obscureConfirmPassword
                                            ? Icons.visibility_off_outlined
                                            : Icons.visibility_outlined,
                                        color: _obscureConfirmPassword
                                            ? Colors.white54
                                            : AppColors.button,
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
                        const Spacer(),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _field(Widget child) => ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 50),
        child: child,
      );

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

class _PasswordRules extends StatelessWidget {
  const _PasswordRules({
    required this.min8,
    required this.hasNumber,
    required this.hasSymbol,
  });

  final bool min8;
  final bool hasNumber;
  final bool hasSymbol;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _ruleRow(min8, 'At least 8 characters'),
        const SizedBox(height: 6),
        _ruleRow(hasNumber, 'Contains a number (0-9)'),
        const SizedBox(height: 6),
        _ruleRow(hasSymbol, 'Contains a special character (!@#...)'),
      ],
    );
  }

  Widget _ruleRow(bool ok, String text) {
    return Row(
      children: [
        Icon(
          ok ? Icons.check_circle : Icons.cancel,
          size: 18,
          color: ok ? Colors.greenAccent : Colors.redAccent,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: Colors.white.withOpacity(0.8),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}