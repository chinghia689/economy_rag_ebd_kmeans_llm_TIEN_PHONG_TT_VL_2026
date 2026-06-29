# 📱 Hướng dẫn Tích hợp Flutter — Cloud-Sync Polling Login

Tài liệu hướng dẫn tích hợp luồng đăng nhập Google OAuth 2.0 từ Flutter WebView App.

## Tổng quan

Flutter App đóng vai trò **trung gian** mở Chrome Custom Tab để đăng nhập Google. Toàn bộ logic xác thực được thực hiện qua Backend ↔ Frontend polling, không cần deep link.

## Kiến trúc

```
Flutter WebView → Load Frontend (HTML/JS)
      ↓
Frontend gửi message qua JavascriptChannel: "GOOGLE_LOGIN:<sessionId>"
      ↓
Flutter nhận message → Mở Chrome Custom Tab (Google OAuth)
      ↓
User đăng nhập Google → Server callback → Lưu token vào DB
      ↓
Frontend polling nhận token → Tự động đăng nhập
```

## 1. Dependencies

Thêm vào `pubspec.yaml`:

```yaml
dependencies:
  flutter_web_auth_2: ^3.0.0
  webview_flutter: ^4.0.0
```

## 2. Cấu hình WebView với JavascriptChannel

Trong file `main.dart` hoặc widget WebView:

```dart
import 'package:webview_flutter/webview_flutter.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

class ChatbotWebView extends StatefulWidget {
  @override
  _ChatbotWebViewState createState() => _ChatbotWebViewState();
}

class _ChatbotWebViewState extends State<ChatbotWebView> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel(
        'FlutterBridge',  // ← Tên channel PHẢI khớp với Frontend
        onMessageReceived: _handleWebMessage,
      )
      ..loadRequest(Uri.parse(AppConfig.webUrl));  // URL của Frontend
  }

  /// Xử lý message từ Frontend
  void _handleWebMessage(JavaScriptMessage message) {
    final data = message.message;
    
    if (data.startsWith('GOOGLE_LOGIN:')) {
      final sessionId = data.split(':')[1];
      _triggerNativeGoogleLogin(sessionId);
    }
  }

  /// Mở Chrome Custom Tab đến trang đăng nhập Google
  Future<void> _triggerNativeGoogleLogin(String sessionId) async {
    final url = "${AppConfig.apiBaseUrl}/api/v1/auth/google/login/flutter?session_id=$sessionId";
    
    try {
      // Mở Chrome Custom Tab
      // callbackUrlScheme: 'none' vì không cần bắt deep link
      // Kết quả đăng nhập được đồng bộ qua Database (polling)
      await FlutterWebAuth2.authenticate(
        url: url,
        callbackUrlScheme: 'none',
        options: const FlutterWebAuth2Options(
          intentFlags: ephemeralIntentFlags, // Không lưu session
        ),
      );
    } catch (e) {
      // User đóng tab trước khi đăng nhập xong → Không cần xử lý
      debugPrint('Auth tab closed: $e');
    }
    
    // Không cần làm gì ở đây.
    // Frontend đang polling và sẽ tự động nhận token khi server cập nhật DB.
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: WebViewWidget(controller: _controller),
      ),
    );
  }
}
```

## 3. Cấu hình AppConfig

```dart
class AppConfig {
  // URL của Frontend (được serve bởi FastAPI server)
  static const String webUrl = "https://yourdomain.com";
  
  // URL của API Backend  
  static const String apiBaseUrl = "https://yourdomain.com";
}
```

## 4. Google Cloud Console

### 4.1. Tạo OAuth 2.0 Client ID

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Tạo **OAuth 2.0 Client ID** loại **Web Application**
3. Thêm **Authorized redirect URIs**:
   - Development: `http://localhost:8001/api/v1/auth/google/callback/flutter`
   - Production: `https://yourdomain.com/api/v1/auth/google/callback/flutter`
4. Copy **Client ID** và **Client Secret** vào file `.env` của Backend

### 4.2. Bật APIs

Đảm bảo đã bật các API:
- **Google+ API** (hoặc People API)
- **Google Identity Services**

## 5. Test trên Thiết bị

### Android
- Chrome Custom Tab mở tự động
- Sau khi đăng nhập, user thấy trang "Thành công, đóng Tab"
- User đóng tab → Quay lại app → Frontend đã polling xong → Tự động vào chat

### iOS
- Tương tự Android, dùng Safari In-App Browser
- FlutterWebAuth2 tự động xử lý

## 6. Lưu ý Quan trọng

| Mục | Chi tiết |
|-----|---------|
| **Channel Name** | `FlutterBridge` — phải khớp giữa Dart và JS |
| **callbackUrlScheme** | `'none'` — không cần deep link |
| **Session TTL** | 10 phút — nếu user không đăng nhập trong 10 phút, session hết hạn |
| **One-time Use** | Token chỉ được polling lấy 1 lần, sau đó session bị xóa |
| **No Deep Link** | Không cần cấu hình intent-filter hay URL scheme |
