import 'weather_data.dart'; // لكي يتعرف على كلاس WeatherData

abstract class ForcastModel {
  void train(List history, List weatherHistory);
  double predict(WeatherData weather);
}