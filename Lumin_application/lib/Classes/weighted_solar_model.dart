import 'forcast_model.dart';
import 'weather_data.dart';

class WeightedSolarModel implements ForcastModel {
 
  Map<String, double> weights = {};
  double bias = 0.0;
  DateTime lastTrainingDate = DateTime.now();

  
  String method(String type) {
 
    return "Method type: $type";
  }


  @override
  void train(List history, List weatherHistory) {
 
    lastTrainingDate = DateTime.now();
  }

  
  @override
  double predict(WeatherData weather) {

    return 0.0;
  }
}