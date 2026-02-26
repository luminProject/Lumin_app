class SensorDataReading {
  final DateTime timestamp;
  final int deviceId;
  final double kwh;

  SensorDataReading({
    required this.timestamp,
    required this.deviceId,
    required this.kwh,
  });

  String readData() {
    return 'timestamp: $timestamp, deviceId: $deviceId, kwh: $kwh';
  }
}
