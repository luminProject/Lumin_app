import 'device.dart';

abstract class DeviceUpdateHandler {
  Device? device;

  void update(Device device);
}
