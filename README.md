# WiFi File Share Android App

Ứng dụng Android để chia sẻ file qua WiFi với giao diện native, được phát triển từ script Python gốc.

## Tính năng

- 📱 Giao diện Android native với Kivy
- 🌐 Web server Flask tích hợp
- 📁 Duyệt và tải file từ storage
- 🔐 Xác thực đăng nhập
- 📶 Tự động phát hiện IP address
- ⚙️ Cấu hình port server
- 🚀 Auto-start server option

## Cài đặt môi trường phát triển

### 1. Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Cài đặt Buildozer (để build APK)

```bash
# Trên Ubuntu/Debian
sudo apt update
sudo apt install -y git zip unzip openjdk-8-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# Cài đặt Buildozer
pip install buildozer

# Cài đặt Cython (required)
pip install cython
```

### 3. Khởi tạo Buildozer

```bash
buildozer init
```

## Phát triển và Test

### Chạy trên desktop (để test)

```bash
python main.py
```

### Build APK

```bash
# Build debug APK
buildozer android debug

# Build release APK (cần signing key)
buildozer android release
```

APK sẽ được tạo trong thư mục `bin/`

## Cấu trúc Project

```
wifishare/
├── main.py              # Kivy app chính
├── wifi_server.py       # Flask server module
├── Wifi_share.py        # Script Python gốc
├── buildozer.spec       # Cấu hình build APK
├── requirements.txt     # Python dependencies
└── README.md           # Tài liệu này
```

## Sử dụng

1. **Khởi động app**: Mở ứng dụng trên Android
2. **Cấu hình**: Đặt port server (mặc định 8000)
3. **Khởi động server**: Nhấn "Khởi động Server"
4. **Truy cập web**: Nhấn "Mở trình duyệt" hoặc truy cập `http://IP:PORT` từ thiết bị khác
5. **Đăng nhập**: Username: `admin`, Password: `123456`

## Bảo mật

⚠️ **QUAN TRỌNG**: Đổi username/password trong `wifi_server.py` trước khi sử dụng:

```python
USERNAME = "your_username"
PASSWORD = "your_secure_password"
```

## Permissions Android

App yêu cầu các permissions:
- `INTERNET`: Để chạy web server
- `ACCESS_NETWORK_STATE`: Để kiểm tra kết nối mạng
- `ACCESS_WIFI_STATE`: Để lấy thông tin WiFi
- `READ_EXTERNAL_STORAGE`: Để đọc file
- `WRITE_EXTERNAL_STORAGE`: Để ghi file
- `MANAGE_EXTERNAL_STORAGE`: Để truy cập full storage (Android 11+)

## Mở rộng tính năng

### Thêm tính năng mới vào Kivy app:

1. Chỉnh sửa `main.py` để thêm UI components
2. Thêm methods xử lý trong class `WiFiShareApp`

### Thêm API endpoints mới:

1. Chỉnh sửa `wifi_server.py`
2. Thêm routes trong function `create_app()`

### Tùy chỉnh giao diện:

1. Tạo file `.kv` cho Kivy layouts
2. Thêm CSS/HTML templates cho web interface

## Troubleshooting

### Build APK thất bại:

```bash
# Clean build
buildozer android clean

# Update dependencies
buildozer android update

# Build lại
buildozer android debug
```

### Lỗi permissions:

- Kiểm tra `android.permissions` trong `buildozer.spec`
- Đảm bảo app request permissions trong code

### Server không khởi động:

- Kiểm tra port có bị sử dụng không
- Kiểm tra permissions network
- Xem logs trong Kivy console

## Phát triển tiếp

Các tính năng có thể thêm:
- Upload file từ web interface
- QR code để chia sẻ URL
- Notification khi có kết nối mới
- Dark mode
- Multi-language support
- File encryption
- User management
- Bandwidth limiting
