import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:intl_phone_field/intl_phone_field.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:image_picker/image_picker.dart';

import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

class EditProfilePage extends StatefulWidget {
  const EditProfilePage({super.key});

  @override
  State<EditProfilePage> createState() => _EditProfilePageState();
}

class _EditProfilePageState extends State<EditProfilePage> {
  static const String apiBaseUrl = 'http://localhost:8000';

  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();

  // Phone
  String _fullPhone = '';
  String _localPhoneDigits = '';

  bool _loading = true;
  bool _saving = false;

  String _initialCountryCode = 'SA';
  String _initialPhoneLocal = '';

  // Errors
  String? _phoneError;

  // Avatar
  final _picker = ImagePicker();
  bool _uploadingAvatar = false;
  String? _avatarUrl;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  String? _uid() => Supabase.instance.client.auth.currentUser?.id;

  // Toast أنيق
  void _toast(String msg, {bool success = true}) {
    if (!mounted) return;

    final bg = success
        ? AppColors.mint.withOpacity(0.18)
        : Colors.red.withOpacity(0.18);

    final border = success ? AppColors.mint : Colors.redAccent;

    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          backgroundColor: Colors.transparent,
          elevation: 0,
          duration: const Duration(milliseconds: 1400),
          margin: const EdgeInsets.fromLTRB(18, 0, 18, 18),
          content: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: border.withOpacity(0.55)),
            ),
            child: Row(
              children: [
                Icon(
                  success ? Icons.check_circle : Icons.error,
                  color: border,
                  size: 18,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    msg,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
  }

  void _preparePhoneInitial(String phone) {
    final p = phone.trim();
    if (p.startsWith('+966')) {
      _initialCountryCode = 'SA';
      _initialPhoneLocal = p.replaceFirst('+966', '').trim();
    } else {
      _initialCountryCode = 'SA';
      _initialPhoneLocal = '';
    }
  }

  // Validation
  String? _validateName(String? v) {
    final s = (v ?? '').trim();
    if (s.isEmpty) return 'Name is required';
    if (s.length < 3) return 'Name is too short';
    return null;
  }

  String? _validatePhoneLocalDigits(String digits) {
    final d = digits.trim();

    if (d.isEmpty) return 'Phone number is required';
    if (!RegExp(r'^\d+$').hasMatch(d)) return 'Phone must contain numbers only';

    final allSame = d.split('').every((c) => c == d[0]);
    if (allSame) return 'Phone number looks invalid';
    if (RegExp(r'^123456').hasMatch(d)) return 'Phone number looks invalid';

    if (d.length < 8 || d.length > 12) return 'Phone length is invalid';
    return null;
  }

  Future<void> _loadProfile() async {
    final userId = _uid();
    if (userId == null) {
      setState(() => _loading = false);
      _toast('Not logged in', success: false);
      return;
    }

    setState(() => _loading = true);

    try {
      final res = await http.get(Uri.parse('$apiBaseUrl/profiles/$userId'));
      if (res.statusCode >= 400) {
        throw Exception('GET ${res.statusCode}: ${res.body}');
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;

      _nameCtrl.text = (data['username'] ?? '').toString().trim();
      _fullPhone = (data['phone_number'] ?? '').toString().trim();

      _avatarUrl = (data['avatar_url'] ?? '').toString().trim();
      if (_avatarUrl != null && _avatarUrl!.isEmpty) _avatarUrl = null;

      _preparePhoneInitial(_fullPhone);

      if (_fullPhone.startsWith('+966')) {
        _localPhoneDigits = _fullPhone.replaceFirst('+966', '').trim();
      } else {
        _localPhoneDigits = '';
      }

      _phoneError = null;
    } catch (e) {
      _toast('Failed to load profile: $e', success: false);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _saveProfile() async {
    final ok = _formKey.currentState?.validate() ?? false;
    final phoneErr = _validatePhoneLocalDigits(_localPhoneDigits);
    setState(() => _phoneError = phoneErr);

    if (!ok || phoneErr != null) {
      _toast('Fix the highlighted fields', success: false);
      return;
    }

    final userId = _uid();
    if (userId == null) {
      _toast('Not logged in', success: false);
      return;
    }

    setState(() => _saving = true);

    try {
      final body = jsonEncode({
        'username': _nameCtrl.text.trim(),
        'phone_number': _fullPhone.trim(),
      });

      final res = await http.patch(
        Uri.parse('$apiBaseUrl/profiles/$userId'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      if (res.statusCode >= 400) {
        throw Exception('PATCH ${res.statusCode}: ${res.body}');
      }

      _toast('Saved');
      await _loadProfile();
    } catch (e) {
      _toast('Failed to save: $e', success: false);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  // ✅ Avatar upload + update DB
  Future<void> _pickAndUploadAvatar() async {
    if (_uploadingAvatar) return;

    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) {
      _toast('Not logged in', success: false);
      return;
    }

    final picked = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
      maxWidth: 1024,
    );

    if (picked == null) return;

    setState(() => _uploadingAvatar = true);

    try {
      final bytes = await picked.readAsBytes();

      // ✅ bucket اسمه avatars، لا تحطي "avatars/" داخل المسار
      final ext = picked.path.split('.').last.toLowerCase();
      final filePath = '${user.id}/avatar.$ext';

      // ✅ لا نحدد contentType (كان سبب الخطأ)
      await Supabase.instance.client.storage.from('avatars').uploadBinary(
            filePath,
            bytes,
            fileOptions: const FileOptions(
              upsert: true,
            ),
          );

      // لو bucket public
      final publicUrl = Supabase.instance.client.storage
          .from('avatars')
          .getPublicUrl(filePath);

      // تحديث DB عبر FastAPI
      final res = await http.patch(
        Uri.parse('$apiBaseUrl/profiles/${user.id}'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'avatar_url': publicUrl}),
      );

      if (res.statusCode >= 400) {
        throw Exception('PATCH ${res.statusCode}: ${res.body}');
      }

      setState(() => _avatarUrl = publicUrl);
      _toast('Photo updated ✅');
    } on StorageException catch (e) {
      _toast('Storage: ${e.message}', success: false);
    } catch (e) {
      _toast('Upload error: $e', success: false);
    } finally {
      if (mounted) setState(() => _uploadingAvatar = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return GradientBackground(
      child: ResponsiveLayout(
        showAppBar: true,
        title: 'Edit Profile',
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
        ),
        actions: const [],
        bottomNavigationBar: const HomeBottomNav(currentIndex: 4),
        child: _loading
            ? Center(
                child: SizedBox(
                  width: 44,
                  height: 44,
                  child: CircularProgressIndicator(
                    strokeWidth: 4,
                    valueColor: const AlwaysStoppedAnimation(AppColors.mint),
                  ),
                ),
              )
            : Form(
                key: _formKey,
                child: Column(
                  children: [
                    const SizedBox(height: 125),
                    _avatarSection(),
                    const SizedBox(height: 14),
                    GlassCard(
                      radius: 20,
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _label('Full Name'),
                          const SizedBox(height: 8),
                          _nameField(),
                          const SizedBox(height: 16),
                          _label('Phone Number'),
                          const SizedBox(height: 8),
                          _phoneIntlField(),
                          if (_phoneError != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              _phoneError!,
                              style: const TextStyle(
                                color: Colors.redAccent,
                                fontSize: 12,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: ElevatedButton(
                              onPressed: _saving ? null : _saveProfile,
                              child: _saving
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white,
                                      ),
                                    )
                                  : const Text(
                                      'Save Changes',
                                      style: TextStyle(
                                        fontSize: 14.5,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
      ),
    );
  }

  // Avatar UI (network + tap)
  Widget _avatarSection() {
    final imageProvider = (_avatarUrl != null && _avatarUrl!.isNotEmpty)
        ? NetworkImage(_avatarUrl!)
        : const NetworkImage(
            'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400',
          );

    return Column(
      children: [
        Stack(
          clipBehavior: Clip.none,
          children: [
            Container(
              width: 86,
              height: 86,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.mint, width: 2),
              ),
              child: ClipOval(
                child: Image(
                  image: imageProvider,
                  fit: BoxFit.cover,
                ),
              ),
            ),
            Positioned(
              bottom: -2,
              right: -2,
              child: GestureDetector(
                onTap: _uploadingAvatar ? null : _pickAndUploadAvatar,
                child: Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: AppColors.mint,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.black.withOpacity(0.15),
                      width: 2,
                    ),
                  ),
                  child: _uploadingAvatar
                      ? const Padding(
                          padding: EdgeInsets.all(6),
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(
                          Icons.photo_camera_rounded,
                          size: 16,
                          color: Colors.white,
                        ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Change profile photo',
          style: TextStyle(
            color: Colors.white.withOpacity(0.65),
            fontSize: 11.5,
          ),
        ),
      ],
    );
  }

  Widget _label(String text) {
    return Text(
      text,
      style: TextStyle(
        color: Colors.white.withOpacity(0.72),
        fontSize: 16,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  Widget _nameField() {
    return TextFormField(
      controller: _nameCtrl,
      keyboardType: TextInputType.name,
      validator: _validateName,
      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
      cursorColor: AppColors.mint,
      decoration: InputDecoration(
        hintText: 'Full Name',
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: AppColors.mint, width: 1.4),
        ),
        errorStyle: const TextStyle(
          color: Colors.redAccent,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _phoneIntlField() {
    return IntlPhoneField(
      initialCountryCode: _initialCountryCode,
      initialValue: _initialPhoneLocal.isEmpty ? null : _initialPhoneLocal,
      disableLengthCheck: true,
      cursorColor: AppColors.mint,
      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
      dropdownTextStyle: TextStyle(
        color: Colors.white.withOpacity(0.88),
        fontWeight: FontWeight.w800,
      ),
      dropdownIcon: Icon(
        Icons.keyboard_arrow_down_rounded,
        color: Colors.white.withOpacity(0.65),
      ),
      decoration: InputDecoration(
        hintText: 'Phone Number',
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: AppColors.mint, width: 1.4),
        ),
      ),
      onChanged: (phone) {
        _fullPhone = phone.completeNumber;
        _localPhoneDigits = phone.number.replaceAll(RegExp(r'\D'), '');

        final err = _validatePhoneLocalDigits(_localPhoneDigits);
        setState(() => _phoneError = err);
      },
    );
  }
}