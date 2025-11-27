"""
Android Utilities
Các tiện ích để tương tác với Android native features
"""

import logging
from kivy.logger import Logger

try:
    from android.permissions import request_permissions, Permission, check_permission
    from jnius import autoclass, cast
    ANDROID_AVAILABLE = True
except ImportError:
    ANDROID_AVAILABLE = False
    Logger.info("AndroidUtils: Running on desktop, Android features disabled")

class AndroidUtils:
    """Utility class cho các tính năng Android"""
    
    def __init__(self):
        self.android_available = ANDROID_AVAILABLE
        
        if self.android_available:
            try:
                # Android classes
                self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
                self.Intent = autoclass('android.content.Intent')
                self.Uri = autoclass('android.net.Uri')
                self.Context = autoclass('android.content.Context')
                self.NotificationManager = autoclass('android.app.NotificationManager')
                self.NotificationCompat = autoclass('androidx.core.app.NotificationCompat')
                self.WifiManager = autoclass('android.net.wifi.WifiManager')
                
                # Get current activity
                self.current_activity = cast('android.app.Activity', self.PythonActivity.mActivity)
                
                Logger.info("AndroidUtils: Android classes loaded successfully")
            except Exception as e:
                Logger.error(f"AndroidUtils: Failed to load Android classes: {e}")
                self.android_available = False
    
    def request_permissions(self):
        """Request các permissions cần thiết"""
        if not self.android_available:
            Logger.info("AndroidUtils: Permissions not needed on desktop")
            return True
        
        try:
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.ACCESS_WIFI_STATE,
                Permission.WAKE_LOCK,
                Permission.FOREGROUND_SERVICE
            ]
            
            # Request permissions
            request_permissions(permissions)
            Logger.info("AndroidUtils: Permissions requested")
            return True
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to request permissions: {e}")
            return False
    
    def check_storage_permission(self):
        """Kiểm tra storage permission"""
        if not self.android_available:
            return True
        
        try:
            return check_permission(Permission.READ_EXTERNAL_STORAGE) and \
                   check_permission(Permission.WRITE_EXTERNAL_STORAGE)
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to check storage permission: {e}")
            return False
    
    def open_url(self, url):
        """Mở URL trong browser"""
        if not self.android_available:
            # Fallback cho desktop
            import webbrowser
            webbrowser.open(url)
            return True
        
        try:
            intent = self.Intent()
            intent.setAction(self.Intent.ACTION_VIEW)
            intent.setData(self.Uri.parse(url))
            
            self.current_activity.startActivity(intent)
            Logger.info(f"AndroidUtils: Opened URL: {url}")
            return True
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to open URL: {e}")
            return False
    
    def show_notification(self, title, message, notification_id=1):
        """Hiển thị notification"""
        if not self.android_available:
            Logger.info(f"AndroidUtils: Notification (Desktop): {title} - {message}")
            return True
        
        try:
            # Get notification manager
            notification_service = self.Context.NOTIFICATION_SERVICE
            notification_manager = self.current_activity.getSystemService(notification_service)
            
            # Create notification
            builder = self.NotificationCompat.Builder(self.current_activity, "default")
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(android.R.drawable.ic_dialog_info)  # Default icon
            builder.setAutoCancel(True)
            
            notification = builder.build()
            notification_manager.notify(notification_id, notification)
            
            Logger.info(f"AndroidUtils: Notification shown: {title}")
            return True
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to show notification: {e}")
            return False
    
    def get_wifi_info(self):
        """Lấy thông tin WiFi"""
        if not self.android_available:
            return {"ssid": "Desktop", "ip": "127.0.0.1"}
        
        try:
            wifi_service = self.Context.WIFI_SERVICE
            wifi_manager = self.current_activity.getSystemService(wifi_service)
            
            wifi_info = wifi_manager.getConnectionInfo()
            
            # Get SSID (remove quotes)
            ssid = wifi_info.getSSID()
            if ssid.startswith('"') and ssid.endswith('"'):
                ssid = ssid[1:-1]
            
            # Get IP address
            ip_int = wifi_info.getIpAddress()
            ip = f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"
            
            return {
                "ssid": ssid,
                "ip": ip,
                "bssid": wifi_info.getBSSID(),
                "link_speed": wifi_info.getLinkSpeed(),
                "rssi": wifi_info.getRssi()
            }
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to get WiFi info: {e}")
            return {"ssid": "Unknown", "ip": "Unknown"}
    
    def keep_screen_on(self, keep_on=True):
        """Giữ màn hình sáng"""
        if not self.android_available:
            Logger.info(f"AndroidUtils: Keep screen on (Desktop): {keep_on}")
            return True
        
        try:
            from android import mActivity
            
            if keep_on:
                # Keep screen on
                mActivity.getWindow().addFlags(0x00000080)  # FLAG_KEEP_SCREEN_ON
            else:
                # Allow screen to turn off
                mActivity.getWindow().clearFlags(0x00000080)
            
            Logger.info(f"AndroidUtils: Screen keep on: {keep_on}")
            return True
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to set screen on: {e}")
            return False
    
    def share_text(self, text, title="Share"):
        """Chia sẻ text qua Android share intent"""
        if not self.android_available:
            Logger.info(f"AndroidUtils: Share (Desktop): {text}")
            return True
        
        try:
            intent = self.Intent()
            intent.setAction(self.Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(self.Intent.EXTRA_TEXT, text)
            intent.putExtra(self.Intent.EXTRA_SUBJECT, title)
            
            chooser = self.Intent.createChooser(intent, title)
            self.current_activity.startActivity(chooser)
            
            Logger.info(f"AndroidUtils: Shared text: {text}")
            return True
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to share text: {e}")
            return False
    
    def get_device_info(self):
        """Lấy thông tin thiết bị"""
        if not self.android_available:
            return {
                "model": "Desktop",
                "manufacturer": "PC",
                "android_version": "N/A",
                "api_level": "N/A"
            }
        
        try:
            Build = autoclass('android.os.Build')
            
            return {
                "model": Build.MODEL,
                "manufacturer": Build.MANUFACTURER,
                "android_version": Build.VERSION.RELEASE,
                "api_level": Build.VERSION.SDK_INT,
                "brand": Build.BRAND,
                "device": Build.DEVICE
            }
            
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to get device info: {e}")
            return {"error": str(e)}
    
    def vibrate(self, duration=100):
        """Rung thiết bị"""
        if not self.android_available:
            Logger.info(f"AndroidUtils: Vibrate (Desktop): {duration}ms")
            return True
        
        try:
            Vibrator = autoclass('android.os.Vibrator')
            vibrator_service = self.Context.VIBRATOR_SERVICE
            vibrator = self.current_activity.getSystemService(vibrator_service)
            
            if vibrator.hasVibrator():
                vibrator.vibrate(duration)
                Logger.info(f"AndroidUtils: Vibrated for {duration}ms")
                return True
            else:
                Logger.info("AndroidUtils: Device has no vibrator")
                return False
                
        except Exception as e:
            Logger.error(f"AndroidUtils: Failed to vibrate: {e}")
            return False

# Global instance
android_utils = AndroidUtils()
