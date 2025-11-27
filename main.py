"""
WiFi Share Android App
Ứng dụng Android để chia sẻ file qua WiFi với giao diện native
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.logger import Logger

import threading
import socket
import webbrowser

# Import Flask server
from wifi_server import create_app, get_local_ip

# Import full-featured server
def create_full_app():
    """Import và return Flask app từ file gốc với full features"""
    import wifi_server_full
    return wifi_server_full.app

# Import Android utilities
from android_utils import android_utils

class WiFiShareApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_thread = None
        self.server_running = False
        self.flask_app = None
        self.server_port = 8000
        
    def build(self):
        """Tạo giao diện chính"""
        # Request permissions khi khởi động
        self.request_android_permissions()
        
        # Layout chính
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Tiêu đề
        title = Label(
            text='WiFi File Share',
            font_size='24sp',
            size_hint_y=None,
            height='60dp',
            bold=True
        )
        main_layout.add_widget(title)
        
        # Thông tin IP và WiFi
        self.ip_label = Label(
            text='IP Address: Đang tìm...',
            font_size='16sp',
            size_hint_y=None,
            height='40dp'
        )
        main_layout.add_widget(self.ip_label)
        
        self.wifi_label = Label(
            text='WiFi: Đang tìm...',
            font_size='14sp',
            size_hint_y=None,
            height='30dp',
            color=(0.7, 0.7, 0.7, 1)
        )
        main_layout.add_widget(self.wifi_label)
        
        # Cấu hình server
        config_layout = GridLayout(cols=2, size_hint_y=None, height='120dp', spacing=10)
        
        # Port setting
        config_layout.add_widget(Label(text='Port:', size_hint_x=0.3))
        self.port_input = TextInput(
            text=str(self.server_port),
            multiline=False,
            size_hint_x=0.7,
            input_filter='int'
        )
        config_layout.add_widget(self.port_input)
        
        # Auto-start setting
        config_layout.add_widget(Label(text='Auto Start:', size_hint_x=0.3))
        self.auto_start_switch = Switch(active=False, size_hint_x=0.7)
        config_layout.add_widget(self.auto_start_switch)
        
        main_layout.add_widget(config_layout)
        
        # Nút điều khiển
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
        
        self.start_button = Button(
            text='Khởi động Server',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.start_button.bind(on_press=self.toggle_server)
        
        self.open_browser_button = Button(
            text='Mở trình duyệt',
            background_color=(0.2, 0.6, 0.8, 1),
            disabled=True
        )
        self.open_browser_button.bind(on_press=self.open_browser)
        
        button_layout.add_widget(self.start_button)
        button_layout.add_widget(self.open_browser_button)
        
        main_layout.add_widget(button_layout)
        
        # Nút tiện ích
        utility_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=10)
        
        self.share_button = Button(
            text='Chia sẻ URL',
            background_color=(0.8, 0.6, 0.2, 1),
            disabled=True
        )
        self.share_button.bind(on_press=self.share_url)
        
        self.notification_button = Button(
            text='Thông báo',
            background_color=(0.6, 0.2, 0.8, 1),
            disabled=True
        )
        self.notification_button.bind(on_press=self.send_notification)
        
        utility_layout.add_widget(self.share_button)
        utility_layout.add_widget(self.notification_button)
        
        main_layout.add_widget(utility_layout)
        
        # Status log
        self.status_label = Label(
            text='Sẵn sàng khởi động server...',
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        main_layout.add_widget(self.status_label)
        
        # Cập nhật IP định kỳ
        Clock.schedule_interval(self.update_ip, 2.0)
        
        return main_layout
    
    def request_android_permissions(self):
        """Request các permissions cần thiết cho Android"""
        android_utils.request_permissions()
    
    def update_ip(self, dt):
        """Cập nhật địa chỉ IP và thông tin WiFi"""
        try:
            # Cập nhật IP
            ip = get_local_ip()
            if ip:
                self.ip_label.text = f'IP Address: {ip}:{self.server_port}'
            else:
                self.ip_label.text = 'IP Address: Không tìm thấy'
            
            # Cập nhật thông tin WiFi
            wifi_info = android_utils.get_wifi_info()
            if wifi_info.get('ssid'):
                ssid = wifi_info['ssid']
                if ssid != 'Unknown':
                    self.wifi_label.text = f'WiFi: {ssid}'
                else:
                    self.wifi_label.text = 'WiFi: Không kết nối'
            else:
                self.wifi_label.text = 'WiFi: Đang kiểm tra...'
                
        except Exception as e:
            self.ip_label.text = f'IP Address: Lỗi - {str(e)}'
            self.wifi_label.text = 'WiFi: Lỗi'
    
    def toggle_server(self, instance):
        """Bật/tắt server"""
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """Khởi động Flask server"""
        try:
            # Cập nhật port từ input
            try:
                self.server_port = int(self.port_input.text)
            except ValueError:
                self.server_port = 8000
                self.port_input.text = "8000"
            
            # Tạo Flask app với full features
            self.flask_app = create_full_app()
            
            # Khởi động server trong thread riêng
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            self.server_running = True
            self.start_button.text = 'Dừng Server'
            self.start_button.background_color = (0.8, 0.2, 0.2, 1)
            self.open_browser_button.disabled = False
            self.share_button.disabled = False
            self.notification_button.disabled = False
            
            # Giữ màn hình sáng khi server chạy
            android_utils.keep_screen_on(True)
            
            # Hiển thị notification
            ip = get_local_ip()
            if ip:
                android_utils.show_notification(
                    "WiFi Share Server",
                    f"Server đang chạy trên {ip}:{self.server_port}"
                )
            
            self.status_label.text = f'Server đang chạy trên port {self.server_port}'
            Logger.info(f"WiFiShare: Server started on port {self.server_port}")
            
        except Exception as e:
            self.show_error(f"Không thể khởi động server: {str(e)}")
            Logger.error(f"WiFiShare: Failed to start server: {e}")
    
    def _run_server(self):
        """Chạy Flask server (được gọi trong thread riêng)"""
        try:
            self.flask_app.run(
                host='0.0.0.0',
                port=self.server_port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            Logger.error(f"WiFiShare: Server error: {e}")
            Clock.schedule_once(lambda dt: self.server_error(str(e)), 0)
    
    def server_error(self, error_msg):
        """Xử lý lỗi server (được gọi từ main thread)"""
        self.server_running = False
        self.start_button.text = 'Khởi động Server'
        self.start_button.background_color = (0.2, 0.8, 0.2, 1)
        self.open_browser_button.disabled = True
        self.share_button.disabled = True
        self.notification_button.disabled = True
        
        # Cho phép màn hình tắt
        android_utils.keep_screen_on(False)
        
        self.status_label.text = f'Lỗi server: {error_msg}'
    
    def stop_server(self):
        """Dừng server"""
        try:
            self.server_running = False
            self.start_button.text = 'Khởi động Server'
            self.start_button.background_color = (0.2, 0.8, 0.2, 1)
            self.open_browser_button.disabled = True
            self.share_button.disabled = True
            self.notification_button.disabled = True
            
            # Cho phép màn hình tắt
            android_utils.keep_screen_on(False)
            
            # Hiển thị notification
            android_utils.show_notification(
                "WiFi Share Server",
                "Server đã dừng"
            )
            
            self.status_label.text = 'Server đã dừng'
            Logger.info("WiFiShare: Server stopped")
        except Exception as e:
            Logger.error(f"WiFiShare: Error stopping server: {e}")
    
    def open_browser(self, instance):
        """Mở trình duyệt với địa chỉ server"""
        try:
            ip = get_local_ip()
            if ip:
                url = f"http://{ip}:{self.server_port}"
                
                if android_utils.open_url(url):
                    self.status_label.text = f'Đã mở trình duyệt: {url}'
                    # Rung nhẹ để xác nhận
                    android_utils.vibrate(50)
                else:
                    self.show_error("Không thể mở trình duyệt")
            else:
                self.show_error("Không tìm thấy địa chỉ IP")
                
        except Exception as e:
            self.show_error(f"Không thể mở trình duyệt: {str(e)}")
    
    def share_url(self, instance):
        """Chia sẻ URL server"""
        try:
            ip = get_local_ip()
            if ip:
                url = f"http://{ip}:{self.server_port}"
                wifi_info = android_utils.get_wifi_info()
                ssid = wifi_info.get('ssid', 'Unknown')
                
                share_text = f"WiFi File Share\n"
                share_text += f"URL: {url}\n"
                share_text += f"WiFi: {ssid}\n"
                share_text += f"Username: admin\n"
                share_text += f"Password: 123456"
                
                if android_utils.share_text(share_text, "WiFi File Share"):
                    self.status_label.text = 'Đã chia sẻ URL'
                    android_utils.vibrate(50)
                else:
                    self.show_error("Không thể chia sẻ URL")
            else:
                self.show_error("Server chưa khởi động")
        except Exception as e:
            self.show_error(f"Lỗi chia sẻ: {str(e)}")
    
    def send_notification(self, instance):
        """Gửi notification test"""
        try:
            ip = get_local_ip()
            if ip and self.server_running:
                android_utils.show_notification(
                    "WiFi File Share",
                    f"Server đang hoạt động trên {ip}:{self.server_port}",
                    notification_id=2
                )
                self.status_label.text = 'Đã gửi thông báo'
                android_utils.vibrate(100)
            else:
                android_utils.show_notification(
                    "WiFi File Share",
                    "Server chưa được khởi động",
                    notification_id=2
                )
                self.status_label.text = 'Server chưa khởi động'
        except Exception as e:
            self.show_error(f"Lỗi thông báo: {str(e)}")
    
    def show_error(self, message):
        """Hiển thị popup lỗi"""
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_layout.add_widget(Label(text=message, text_size=(300, None), halign='center'))
        
        close_button = Button(text='Đóng', size_hint_y=None, height='40dp')
        popup_layout.add_widget(close_button)
        
        popup = Popup(
            title='Lỗi',
            content=popup_layout,
            size_hint=(0.8, 0.4)
        )
        close_button.bind(on_press=popup.dismiss)
        popup.open()
    
    def on_start(self):
        """Được gọi khi app khởi động"""
        Logger.info("WiFiShare: App started")
        
        # Auto-start nếu được bật
        if self.auto_start_switch.active:
            Clock.schedule_once(lambda dt: self.start_server(), 1.0)
    
    def on_stop(self):
        """Được gọi khi app đóng"""
        Logger.info("WiFiShare: App stopping")
        if self.server_running:
            self.stop_server()

if __name__ == '__main__':
    WiFiShareApp().run()
