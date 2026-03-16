import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter/foundation.dart';

/// ApiService handles all HTTP requests to the FastAPI backend.
///
/// Important:
/// - Backend baseUrl changes depending on platform:
///   - Web:        http://127.0.0.1:8000
///   - Android emu http://10.0.2.2:8000
///
/// Auth:
/// - Profile endpoints are protected.
/// - We send Supabase session access token in:
///     Authorization: Bearer <token>
class ApiService {


  /// Base URL for backend depending on current platform.
  static String get baseUrl => kIsWeb ? 'http://127.0.0.1:8000' : 'http://10.0.2.2:8000';

  // ===== Helpers =====

  /// Returns current Supabase user id.
  /// Throws if user is not logged in.
  String get _userId {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) throw Exception('User not logged in');
    return user.id;
  }

  /// Returns current Supabase access token.
  /// Throws if there is no active session.
  String get _accessToken {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    if (token == null) throw Exception('No access token');
    return token;
  }

  /// Returns headers including authorization.
  ///
  /// If [json] is true, it also sets Content-Type to application/json.
  Map<String, String> authHeaders({bool json = false}) {
    final headers = <String, String>{
      'Authorization': 'Bearer $_accessToken',
      'accept': 'application/json',
    };
    if (json) headers['Content-Type'] = 'application/json';
    return headers;
  }

  // ===== Existing endpoints (as in your file) =====

  /// GET /devices/{userId}
  Future<List<dynamic>> getDevices() async {
    final response = await http.get(Uri.parse('$baseUrl/devices/$_userId'));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] ?? [];
    } else {
      throw Exception('Failed to load devices');
    }
  }

  /// GET /bill/{userId}?bill_limit=...
Future<Map<String, dynamic>> getBill() async {
  final url = '$baseUrl/bill/$_userId';

  final response = await http.get(Uri.parse(url));

  debugPrint('GET BILL -> $url');
  debugPrint('GET BILL <- status=${response.statusCode}');
  debugPrint('GET BILL <- body=${response.body}');

  if (response.statusCode == 200) {
    final jsonResponse = json.decode(response.body);
    return jsonResponse['data'];
  } else {
    throw Exception('Failed to load bill prediction: ${response.body}');
  }
}

Future<Map<String, dynamic>> setBillLimit(double billLimit) async {
  final url = '$baseUrl/bill/$_userId';

  final response = await http.post(
    Uri.parse(url),
    headers: {'Content-Type': 'application/json'},
    body: json.encode({
      'limit_amount': billLimit,
    }),
  );

  debugPrint('POST BILL LIMIT -> $url');
  debugPrint('POST BILL LIMIT <- status=${response.statusCode}');
  debugPrint('POST BILL LIMIT <- body=${response.body}');

  if (response.statusCode == 200) {
    final jsonResponse = json.decode(response.body);
    return jsonResponse['data'];
  } else {
    throw Exception('Failed to save bill limit: ${response.body}');
  }
}/// GET /energy/{userId}
  Future<Map<String, dynamic>> getEnergyStats() async {
    final response = await http.get(Uri.parse('$baseUrl/energy/$_userId'));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else {
      throw Exception('Failed to load energy stats');
    }
  }

  /// GET /solar-forecast/{userId}
  Future<Map<String, dynamic>> getSolarForecast() async {

    final response = await http.get(
      Uri.parse('$baseUrl/solar-forecast/$_userId'),
    );

    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else {
      throw Exception('Failed to load solar forecast');
    }
  }

  /// GET /recommendations/{userId}
  Future<List<dynamic>> getRecommendations() async {

    final response = await http.get(
      Uri.parse('$baseUrl/recommendations/$_userId'),
    );

  
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] ?? [];
    } else {
      throw Exception('Failed to load recommendations');
    }
  }


  // 6. إضافة جهاز
  Future<void> addDevice({
    required String deviceName,
    required String deviceType,
    String? panelCapacity,
  }) async {
    debugPrint('ADD DEVICE -> userId=$_userId');
    debugPrint('ADD DEVICE -> name=$deviceName type=$deviceType');
    final body = {
      "name": deviceName,
      "device_type": deviceType,
      "panel_capacity": panelCapacity,
    };
    debugPrint(
      'ADD DEVICE -> url=$baseUrl/devices/$_userId body=${json.encode(body)}',
    );

    final response = await http.post(
      Uri.parse('$baseUrl/devices/$_userId'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );
    debugPrint('ADD DEVICE <- status=${response.statusCode}');
    debugPrint('ADD DEVICE <- body=${response.body}');

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to add device');
    }
  }

  // 7. حذف جهاز
  Future<void> deleteDevice(int deviceId) async {
    final response = await http.delete(Uri.parse('$baseUrl/devices/$deviceId'));

    if (response.statusCode != 200) {
      throw Exception('Failed to delete device');
    }
  }


  // ===== Profile endpoints (Protected) =====

/// GET /profiles/{userId}
///
/// Requires Authorization Bearer token.
Future<Map<String, dynamic>> getProfile(String userId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/profiles/$userId'),
      headers: authHeaders(),
    );

    if (res.statusCode >= 400) {
      throw Exception('GET ${res.statusCode}: ${res.body}');
    }

    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// PATCH /profiles/{userId}
  ///
  /// Requires Authorization Bearer token.
  /// [payload] must match backend accepted fields (username, phone_number, etc).
  Future<void> updateProfile(String userId, Map<String, dynamic> payload) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/profiles/$userId'),
      headers: authHeaders(json: true),
      body: jsonEncode(payload),
    );

    if (res.statusCode >= 400) {
      throw Exception('PATCH ${res.statusCode}: ${res.body}');
    }
  }

  /// Convenience wrapper to update only the avatar_url.
  ///
  /// Flow:
  /// 1) Upload image to Supabase Storage
  /// 2) Get public URL
  /// 3) Call this endpoint to save avatar_url in backend DB.
  Future<void> updateAvatarUrl(String userId, String avatarUrl) async {
    await updateProfile(userId, {'avatar_url': avatarUrl});
  }

}