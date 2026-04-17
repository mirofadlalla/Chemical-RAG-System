# Flutter Integration Guide

## 📱 Connecting Flutter App to Chemical RAG System

Complete guide for integrating the Chemical RAG API with a Flutter mobile application.

---

## 🔌 REST Client Setup

### Step 1: Add Dependencies

Update your `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  dio: ^5.3.0           # Alternative HTTP client
  freezed_annotation: ^2.4.0
  json_serializable: ^6.7.0

dev_dependencies:
  build_runner: ^2.4.0
  freezed: ^2.4.0
  json_serializable: ^6.7.0
```

Run: `flutter pub get`

---

## 🎯 Data Models

### models/compound.dart

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'compound.freezed.dart';
part 'compound.g.dart';

@freezed
class SearchRequest with _$SearchRequest {
  const factory SearchRequest({
    required String smiles,
    @Default(3) int topK,
  }) = _SearchRequest;

  factory SearchRequest.fromJson(Map<String, dynamic> json) =>
      _$SearchRequestFromJson(json);
}

@freezed
class CompoundResult with _$CompoundResult {
  const factory CompoundResult({
    required String smiles,
    required double distance,
    String? image,
  }) = _CompoundResult;

  factory CompoundResult.fromJson(Map<String, dynamic> json) =>
      _$CompoundResultFromJson(json);
}

@freezed
class SearchResponse with _$SearchResponse {
  const factory SearchResponse({
    required List<CompoundResult> results,
  }) = _SearchResponse;

  factory SearchResponse.fromJson(Map<String, dynamic> json) =>
      _$SearchResponseFromJson(json);
}

@freezed
class ApiStats with _$ApiStats {
  const factory ApiStats({
    required int compounds,
    @JsonKey(name: 'index_size') required int indexSize,
    @JsonKey(name: 'bit_size') required int bitSize,
  }) = _ApiStats;

  factory ApiStats.fromJson(Map<String, dynamic> json) =>
      _$ApiStatsFromJson(json);
}

@freezed
class HealthStatus with _$HealthStatus {
  const factory HealthStatus({
    required String status,
    required String service,
    required String version,
  }) = _HealthStatus;

  factory HealthStatus.fromJson(Map<String, dynamic> json) =>
      _$HealthStatusFromJson(json);
}
```

---

## 🔌 API Service

### services/chemical_api_service.dart

```dart
import 'package:dio/dio.dart';
import '../models/compound.dart';

class ChemicalApiService {
  late final Dio _dio;
  final String baseUrl;

  ChemicalApiService({this.baseUrl = 'http://127.0.0.1:8000'}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
        persistentConnection: true,
      ),
    );

    // Add logging and error handling
    _dio.interceptors.add(
      LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (obj) => print(obj),
      ),
    );
  }

  /// Health check endpoint
  Future<HealthStatus> getHealth() async {
    try {
      final response = await _dio.get('/health');
      return HealthStatus.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  /// Get system statistics
  Future<ApiStats> getStats() async {
    try {
      final response = await _dio.get('/stats');
      return ApiStats.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  /// Search for similar compounds
  Future<SearchResponse> search({
    required String smiles,
    int topK = 3,
  }) async {
    try {
      final payload = SearchRequest(smiles: smiles, topK: topK);
      final response = await _dio.post(
        '/search',
        data: payload.toJson(),
      );
      return SearchResponse.fromJson(response.data);
    } on DioException catch (e) {
      // Handle specific errors
      if (e.response?.statusCode == 400) {
        final error = e.response?.data['detail'] ?? 'Invalid request';
        throw ArgumentError(error);
      }
      rethrow;
    }
  }

  /// Check if server is running
  Future<bool> isServerRunning() async {
    try {
      await getHealth();
      return true;
    } catch (e) {
      return false;
    }
  }
}
```

---

## 🏗️ State Management (Provider Pattern)

### providers/chemical_provider.dart

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/chemical_api_service.dart';
import '../models/compound.dart';

// Service provider
final chemicalApiProvider = Provider((ref) {
  return ChemicalApiService();
});

// Health status provider
final healthStatusProvider = FutureProvider((ref) async {
  final api = ref.watch(chemicalApiProvider);
  return api.getHealth();
});

// System stats provider
final systemStatsProvider = FutureProvider((ref) async {
  final api = ref.watch(chemicalApiProvider);
  return api.getStats();
});

// Search results provider with parameter
final searchResultsProvider = FutureProvider.family<SearchResponse, String>(
  (ref, smiles) async {
    final api = ref.watch(chemicalApiProvider);
    return api.search(smiles: smiles, topK: 5);
  },
);

// Server status provider
final serverStatusProvider = FutureProvider((ref) async {
  final api = ref.watch(chemicalApiProvider);
  return api.isServerRunning();
});

// Selected compound state
final selectedCompoundProvider = StateProvider<CompoundResult?>((ref) => null);

// Search history
final searchHistoryProvider = StateProvider<List<String>>((ref) => []);
```

---

## 🎨 UI Widgets

### screens/search_screen.dart

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/chemical_provider.dart';
import '../widgets/compound_card.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  late TextEditingController _smilesController;
  String? _selectedSmiles;

  @override
  void initState() {
    super.initState();
    _smilesController = TextEditingController();
  }

  @override
  void dispose() {
    _smilesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final searchResults = _selectedSmiles != null
        ? ref.watch(searchResultsProvider(_selectedSmiles!))
        : null;

    final serverStatus = ref.watch(serverStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chemical Similarity Search'),
        elevation: 0,
        actions: [
          Center(
            child: serverStatus.when(
              data: (isRunning) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Center(
                  child: Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isRunning ? Colors.green : Colors.red,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        isRunning ? 'Connected' : 'Disconnected',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
              loading: () => const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              error: (err, stack) => const Text('Error'),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Stats Card
          Padding(
            padding: const EdgeInsets.all(16),
            child: StatsCard(),
          ),

          // Search Input
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _smilesController,
                  decoration: InputDecoration(
                    hintText: 'Enter SMILES string (e.g., CCO, c1ccccc1)',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: _smilesController.clear,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _performSearch,
                    icon: const Icon(Icons.search),
                    label: const Text('Search'),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Common SMILES Presets
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _presetSmiles('Ethanol', 'CCO'),
                  const SizedBox(width: 8),
                  _presetSmiles('Benzene', 'c1ccccc1'),
                  const SizedBox(width: 8),
                  _presetSmiles('Acetic Acid', 'CC(=O)O'),
                  const SizedBox(width: 8),
                  _presetSmiles('Methanol', 'CO'),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Results
          Expanded(
            child: searchResults == null
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.search,
                          size: 64,
                          color: Colors.grey[300],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Enter a SMILES string to search',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ],
                    ),
                  )
                : searchResults.when(
                    data: (results) => ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: results.results.length,
                      itemBuilder: (context, index) {
                        final compound = results.results[index];
                        return CompoundCard(compound: compound);
                      },
                    ),
                    loading: () => const Center(
                      child: CircularProgressIndicator(),
                    ),
                    error: (error, stack) => Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 48,
                            color: Colors.red[300],
                          ),
                          const SizedBox(height: 16),
                          Text(
                            error.toString(),
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.red[300]),
                          ),
                        ],
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _presetSmiles(String label, String smiles) {
    return ActionChip(
      label: Text(label),
      onPressed: () {
        _smilesController.text = smiles;
        _performSearch();
      },
    );
  }

  void _performSearch() {
    final smiles = _smilesController.text.trim();
    if (smiles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a SMILES string')),
      );
      return;
    }
    setState(() => _selectedSmiles = smiles);
  }
}

// Stats Card Widget
class StatsCard extends ConsumerWidget {
  const StatsCard({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(systemStatsProvider);

    return stats.when(
      data: (stat) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _StatItem(label: 'Compounds', value: stat.compounds.toString()),
              _StatItem(label: 'Index Size', value: stat.indexSize.toString()),
              _StatItem(label: 'Fingerprints', value: '${stat.bitSize}-bit'),
            ],
          ),
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => const Card(child: Text('Failed to load stats')),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
```

### widgets/compound_card.dart

```dart
import 'package:flutter/material.dart';
import '../models/compound.dart';

class CompoundCard extends StatelessWidget {
  final CompoundResult compound;

  const CompoundCard({required this.compound, Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: compound.image != null
            ? Image.network(
                compound.image!,
                width: 56,
                height: 56,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  width: 56,
                  height: 56,
                  color: Colors.grey[300],
                  child: const Icon(Icons.image_not_supported),
                ),
              )
            : Container(
                width: 56,
                height: 56,
                color: Colors.grey[300],
                child: const Icon(Icons.molecular_weight),
              ),
        title: Text(
          compound.smiles,
          style: const TextStyle(fontFamily: 'monospace'),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          'Distance: ${compound.distance.toStringAsFixed(2)}',
          style: TextStyle(
            color: Colors.blue[600],
            fontWeight: FontWeight.w500,
          ),
        ),
        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
        onTap: () {
          // Handle compound selection
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Compound Details'),
              content: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  SelectableText('SMILES: ${compound.smiles}'),
                  const SizedBox(height: 8),
                  SelectableText(
                      'Distance: ${compound.distance.toStringAsFixed(4)}'),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Close'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
```

---

## 🔧 Configuration

### constants/api_config.dart

```dart
class ApiConfig {
  // Development
  static const String devBaseUrl = 'http://127.0.0.1:8000';
  
  // Production
  static const String prodBaseUrl = 'https://chemical-rag.example.com';
  
  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // API endpoints
  static const String healthEndpoint = '/health';
  static const String searchEndpoint = '/search';
  static const String statsEndpoint = '/stats';
  
  // Default search parameters
  static const int defaultTopK = 5;
}
```

---

## 🚀 Main App Setup

### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'screens/search_screen.dart';
import 'constants/api_config.dart';

void main() {
  runApp(const ProviderScope(child: MyApp()));
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Chemical Similarity Search',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const SearchScreen(),
    );
  }
}
```

---

## 📲 Testing the Integration

### Test Cases

1. **Server Connection**
   ```dart
   test('Server connection', () async {
     final api = ChemicalApiService();
     final health = await api.getHealth();
     expect(health.status, 'healthy');
   });
   ```

2. **Search Functionality**
   ```dart
   test('Search compounds', () async {
     final api = ChemicalApiService();
     final results = await api.search(smiles: 'CCO');
     expect(results.results, isNotEmpty);
   });
   ```

3. **Error Handling**
   ```dart
   test('Invalid SMILES error', () async {
     final api = ChemicalApiService();
     expect(
       () => api.search(smiles: 'INVALID'),
       throwsA(isA<ArgumentError>()),
     );
   });
   ```

---

## 🌐 Network Configuration

### android/app/src/main/AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

### ios/Runner/Info.plist

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>Allow connection to chemical RAG server</string>
<key>NSBonjourServiceTypes</key>
<array>
  <string>_http._tcp</string>
</array>
```

---

## 📦 Release Checklist

- [ ] Update baseUrl to production server
- [ ] Enable SSL/TLS for HTTPS
- [ ] Add request/response logging
- [ ] Implement error recovery
- [ ] Test on real device
- [ ] Cache API responses locally
- [ ] Add offline support (optional)

---

## 🎯 Advanced Features

### Client-Side Caching

```dart
final cachedSearchProvider = 
    StateNotifierProvider<SearchCache, Map<String, SearchResponse>>(
      (ref) => SearchCache(),
    );

class SearchCache extends StateNotifier<Map<String, SearchResponse>> {
  SearchCache() : super({});
  
  Future<SearchResponse> getOrFetch(
    String smiles,
    ChemicalApiService api,
  ) async {
    if (state.containsKey(smiles)) {
      return state[smiles]!;
    }
    
    final result = await api.search(smiles: smiles);
    state = {...state, smiles: result};
    return result;
  }
}
```

### Batch Search

```dart
Future<List<SearchResponse>> batchSearch(
  List<String> smilesList,
  ChemicalApiService api,
) async {
  return Future.wait(
    smilesList.map((smiles) => api.search(smiles: smiles)),
  );
}
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure API server is running on the correct host/port |
| CORS errors | Server should be on the same network or allow CORS |
| Timeout errors | Increase timeout in BaseOptions |
| Image loading fails | Check server is serving `/static/images` |
| Model generation fails | Run `flutter pub run build_runner build` |

---

**Ready to launch your Flutter app with Chemical RAG! 🚀**
