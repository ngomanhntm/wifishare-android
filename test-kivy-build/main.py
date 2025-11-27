from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class TestApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Label chào mừng
        welcome_label = Label(
            text='Hello Kivy Test App!',
            size_hint=(1, 0.3),
            font_size='24sp'
        )
        
        # Button đơn giản
        test_button = Button(
            text='Click Me!',
            size_hint=(1, 0.3),
            font_size='18sp'
        )
        test_button.bind(on_press=self.on_button_click)
        
        # Label hiển thị kết quả
        self.result_label = Label(
            text='Press the button above',
            size_hint=(1, 0.4),
            font_size='16sp'
        )
        
        layout.add_widget(welcome_label)
        layout.add_widget(test_button)
        layout.add_widget(self.result_label)
        
        return layout
    
    def on_button_click(self, instance):
        self.result_label.text = 'Button clicked! App is working!'


if __name__ == '__main__':
    TestApp().run()
