import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:intl_phone_field/intl_phone_field.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:image_picker/image_picker.dart';

import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';

import 'package:lumin_application/Widgets/gradient_background.dart';
import 'package:lumin_application/Widgets/responsive_layout.dart';
import 'package:lumin_application/Widgets/home/bottom_nav.dart';
import 'package:lumin_application/Widgets/home/glass_card.dart';
import 'package:lumin_application/theme/app_colors.dart';

import 'package:lumin_application/services/api_service.dart';
import 'package:lumin_application/Classes/user_model.dart';

/// EditProfilePage allows the user to:
/// - Update full name
/// - Update phone number
/// - Update energy source
/// - Pick and save home location (lat/lng)
/// - Upload avatar to Supabase Storage and save its public URL via backend API
///
/// Architecture:.
/// - It calls ApiService methods for backend operations.
/// - Supabase is used for authentication + storage (avatars bucket).
class EditProfilePage extends StatefulWidget {
  const EditProfilePage({super.key});

  @override
  State<EditProfilePage> createState() => _EditProfilePageState();
}

class _EditProfilePageState extends State<EditProfilePage> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();

  /// API client for backend requests (FastAPI).
  final ApiService _api = ApiService();

  // ===== Phone state =====
  /// Full phone number including country code (+966...).
  String _fullPhone = '';

  /// Local digits only (used for validation).
  String _localPhoneDigits = '';

  /// Default country for IntlPhoneField.
  String _initialCountryCode = 'SA';

  /// Local phone digits used as initial value in IntlPhoneField.
  String _initialPhoneLocal = '';

  // ===== UI state =====
  bool _loading = true;
  bool _saving = false;

  // ===== Validation errors =====
  String? _phoneError;

  // ===== Avatar state =====
  final _picker = ImagePicker();
  bool _uploadingAvatar = false;

  /// Public avatar image URL (optional).
  String? _avatarUrl;

  // ===== Profile fields =====
  String _energySource = 'Grid only';
  double? _latitude;
  double? _longitude;

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

  /// Returns current user id (null if not logged in).
  String? _uid() => Supabase.instance.client.auth.currentUser?.id;

  /// Shows a styled toast/snackbar message.
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
          duration: const Duration(milliseconds: 1600),
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

  /// Prepares IntlPhoneField initial values based on saved backend phone.
  /// Currently handles Saudi (+966) only; can be extended later.
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

  /// Validator for name field.
  String? _validateName(String? v) {
    final s = (v ?? '').trim();
    if (s.isEmpty) return 'Name is required';
    if (s.length < 3) return 'Name is too short';
    return null;
  }

  /// Validator for phone digits only (local part).
  /// This ensures basic sanity before saving.
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

  /// Loads profile data from backend and fills UI controllers/state.
  Future<void> _loadProfile() async {
    final userId = _uid();
    final token = Supabase.instance.client.auth.currentSession?.accessToken;

    if (userId == null || token == null) {
      setState(() => _loading = false);
      _toast('Not logged in', success: false);
      return;
    }

    setState(() => _loading = true);

    try {
      final data = await _api.getProfile(userId);
      final user = UserModel.fromJson(data);

      _nameCtrl.text = user.username;
      _fullPhone = user.phoneNumber;

      final avatar = (user.avatarUrl ?? '').trim();
      _avatarUrl = avatar.isEmpty ? null : avatar;

      _energySource = user.energySource.trim().isEmpty
          ? 'Grid only'
          : user.energySource.trim();

      _latitude = user.latitude;
      _longitude = user.longitude;

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

  /// Saves profile changes to backend.
  ///
  /// This does NOT upload avatar. Avatar flow is handled separately.
  Future<void> _saveProfile() async {
    final ok = _formKey.currentState?.validate() ?? false;
    final phoneErr = _validatePhoneLocalDigits(_localPhoneDigits);
    setState(() => _phoneError = phoneErr);

    if (!ok || phoneErr != null) {
      _toast('Fix the highlighted fields', success: false);
      return;
    }

    final userId = _uid();
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (userId == null || token == null) {
      _toast('Not logged in', success: false);
      return;
    }

    setState(() => _saving = true);

    try {
      final model = UserModel(
        username: _nameCtrl.text.trim(),
        phoneNumber: _fullPhone.trim(),
        energySource: _energySource,
        latitude: _latitude,
        longitude: _longitude,
        avatarUrl: _avatarUrl,
      );

      await _api.updateProfile(userId, model.toUpdateJson());

      _toast('Saved');
      await _loadProfile();
    } catch (e) {
      _toast('Failed to save: $e', success: false);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// Picks a start location for map:
  /// - If user already saved lat/lng -> use it
  /// - Else use GPS if possible
  /// - Else fallback to a default coordinate
  Future<LatLng> _getStartLocation() async {
    if (_latitude != null && _longitude != null) {
      return LatLng(_latitude!, _longitude!);
    }

    // Web usually can provide location if browser permission is granted
    if (kIsWeb) {
      return const LatLng(21.4858, 39.1925);
    }

    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return const LatLng(21.4858, 39.1925);

    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }

    if (perm == LocationPermission.denied ||
        perm == LocationPermission.deniedForever) {
      return const LatLng(21.4858, 39.1925);
    }

    final pos = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
      timeLimit: const Duration(seconds: 8),
    );

    return LatLng(pos.latitude, pos.longitude);
  }

  /// Shows bottom sheet map picker.
  /// Updates _latitude/_longitude when user taps Save.
  Future<void> _pickOnMapInline() async {
    final start = await _getStartLocation();
    LatLng selected = start;

    final result = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (ctx) {
        final height = MediaQuery.of(ctx).size.height * 0.82;

        return Container(
          height: height,
          decoration: const BoxDecoration(
            color: Color(0xFF0F1713),
            borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
          ),
          child: Column(
            children: [
              const SizedBox(height: 10),
              Container(
                width: 42,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.25),
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Pick Home Location',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 16,
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, selected),
                      child: const Text(
                        'Save',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: StatefulBuilder(
                  builder: (ctx2, setLocal) {
                    return FlutterMap(
                      options: MapOptions(
                        initialCenter: start,
                        initialZoom: 14,
                        onTap: (_, point) => setLocal(() => selected = point),
                      ),
                      children: [
                        TileLayer(
                          urlTemplate:
                              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                          userAgentPackageName: 'com.example.lumin_application',
                        ),
                        MarkerLayer(
                          markers: [
                            Marker(
                              point: selected,
                              width: 54,
                              height: 54,
                              child: const Icon(
                                Icons.location_pin,
                                size: 44,
                                color: Colors.redAccent,
                              ),
                            ),
                          ],
                        ),
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        );
      },
    );

    if (result != null) {
      setState(() {
        _latitude = result.latitude;
        _longitude = result.longitude;
      });
      _toast('Location selected');
    }
  }

  /// Preview map (non-interactive).
  Widget _homeMapPreview() {
    final hasLoc = _latitude != null && _longitude != null;
    final center = hasLoc
        ? LatLng(_latitude!, _longitude!)
        : const LatLng(21.4858, 39.1925);

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        height: 140,
        width: double.infinity,
        child: Stack(
          children: [
            FlutterMap(
              options: MapOptions(
                initialCenter: center,
                initialZoom: hasLoc ? 15 : 11,
                interactionOptions: const InteractionOptions(
                  flags: InteractiveFlag.none,
                ),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.example.lumin_application',
                ),
                if (hasLoc)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: center,
                        width: 54,
                        height: 54,
                        child: const Icon(
                          Icons.location_pin,
                          size: 44,
                          color: Colors.redAccent,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
            if (!hasLoc)
              Positioned.fill(
                child: Container(
                  alignment: Alignment.center,
                  color: Colors.black.withOpacity(0.18),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.28),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: Colors.white.withOpacity(0.12)),
                    ),
                    child: const Text(
                      'No location selected',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Avatar flow:
  /// 1) Pick image from gallery
  /// 2) Upload to Supabase Storage bucket: "avatars"
  /// 3) Get public URL
  /// 4) Save public URL in backend profile via ApiService.updateAvatarUrl()
  Future<void> _pickAndUploadAvatar() async {
    if (_uploadingAvatar) return;

    final user = Supabase.instance.client.auth.currentUser;
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (user == null || token == null) {
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
      final ext = picked.path.split('.').last.toLowerCase();
      final filePath = '${user.id}/avatar.$ext';

      await Supabase.instance.client.storage
          .from('avatars')
          .uploadBinary(
            filePath,
            bytes,
            fileOptions: const FileOptions(upsert: true),
          );

      final publicUrl = Supabase.instance.client.storage
          .from('avatars')
          .getPublicUrl(filePath);

      await _api.updateAvatarUrl(user.id, publicUrl);

      setState(() => _avatarUrl = publicUrl);
      _toast('Photo updated');
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
          icon: const Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
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
                          _label('Energy Source'),
                          const SizedBox(height: 8),
                          DropdownButtonFormField<String>(
                            initialValue: _energySource,
                            dropdownColor: const Color(0xFF0F1713),
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                            ),
                            iconEnabledColor: Colors.white70,
                            decoration: InputDecoration(
                              isDense: true,
                              enabledBorder: UnderlineInputBorder(
                                borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.18),
                                ),
                              ),
                              focusedBorder: const UnderlineInputBorder(
                                borderSide: BorderSide(
                                  color: AppColors.mint,
                                  width: 1.4,
                                ),
                              ),
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'Grid only',
                                child: Text('Grid only'),
                              ),
                              DropdownMenuItem(
                                value: 'Grid + Solar',
                                child: Text('Grid + Solar'),
                              ),
                            ],
                            onChanged: (v) {
                              if (v == null) return;
                              setState(() => _energySource = v);
                            },
                          ),

                          const SizedBox(height: 18),
                          _label('Home Location'),
                          const SizedBox(height: 10),

                          Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.06),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.10),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      width: 42,
                                      height: 42,
                                      decoration: BoxDecoration(
                                        color: AppColors.mint.withOpacity(0.16),
                                        borderRadius: BorderRadius.circular(14),
                                        border: Border.all(
                                          color: AppColors.mint.withOpacity(
                                            0.35,
                                          ),
                                        ),
                                      ),
                                      child: const Icon(
                                        Icons.my_location_rounded,
                                        color: AppColors.mint,
                                        size: 20,
                                      ),
                                    ),
                                    const Spacer(),
                                    SizedBox(
                                      height: 46,
                                      child: ElevatedButton(
                                        onPressed: _pickOnMapInline,
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(
                                            0xFF3F8E6B,
                                          ),
                                          foregroundColor: Colors.white,
                                          elevation: 0,
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 14,
                                          ),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              18,
                                            ),
                                          ),
                                        ),
                                        child: const FittedBox(
                                          fit: BoxFit.scaleDown,
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Icon(Icons.map_rounded, size: 18),
                                              SizedBox(width: 8),
                                              Text(
                                                'Pick on Map',
                                                style: TextStyle(
                                                  fontSize: 14,
                                                  fontWeight: FontWeight.w900,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                _homeMapPreview(),
                                const SizedBox(height: 8),
                                Text(
                                  'Tap "Pick" to choose location on map.',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.55),
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),

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

  Widget _avatarSection() {
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
              child: ClipOval(child: _avatarImage()),
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

  /// Avatar image widget:
  /// - If url is empty -> show nothing
  /// - If network fails -> show nothing (no error UI)
  Widget _avatarImage() {
    final url = (_avatarUrl ?? '').trim();
    if (url.isEmpty) return const SizedBox.shrink();

    return Image.network(
      url,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
      loadingBuilder: (_, child, progress) =>
          progress == null ? child : const SizedBox.shrink(),
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
