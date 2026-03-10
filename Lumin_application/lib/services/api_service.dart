import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter/foundation.dart';

class ApiService {
  // 🔴 ملاحظة: إذا كنتِ تختبرين على محاكي أندرويد استخدمي 10.0.2.2 بدلاً من 127.0.0.1
  // وإذا كان iOS Simulator أو Web استخدمي 127.0.0.1
  static const String baseUrl = 'http://127.0.0.1:8000';

  // دالة مساعدة لجلب الـ ID الخاص بالمستخدم الحالي من Supabase
  String get _userId {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) throw Exception('User not logged in');
    return user.id;
  }

  // 1. جلب الأجهزة
  Future<List<dynamic>> getDevices() async {
    final response = await http.get(Uri.parse('$baseUrl/devices/$_userId'));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'] ?? [];
    } else {
      throw Exception('Failed to load devices');
    }
  }

  // 2. جلب الفاتورة
  Future<Map<String, dynamic>> getBill({double? billLimit}) async {
    // إذا كان هناك limit نمرره كـ Query Parameter
    String url = '$baseUrl/bill/$_userId';
    if (billLimit != null) {
      url += '?bill_limit=$billLimit';
    }

    final response = await http.get(Uri.parse(url));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else {
      throw Exception('Failed to load bill prediction');
    }
  }

  // 3. جلب بيانات الطاقة والإحصائيات
  Future<Map<String, dynamic>> getEnergyStats() async {
    final response = await http.get(Uri.parse('$baseUrl/energy/$_userId'));
    if (response.statusCode == 200) {
      final jsonResponse = json.decode(response.body);
      return jsonResponse['data'];
    } else {
      throw Exception('Failed to load energy stats');
    }
  }

  // 4. جلب توقعات الطاقة الشمسية
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

  // 5. جلب التوصيات
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
}
