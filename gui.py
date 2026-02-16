import os
import sv_ttk
import shutil
import datetime
import subprocess
import webbrowser
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, IntVar, Toplevel, Text
from hh_phone_search import HHParse
from Main_HH_files.async_runner import AsyncParserRunner


class HHParser(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("HHParser")
        self.parent.geometry("450x600")

        try:
            self.parent.iconbitmap("static/HHParse_logo.ico")
        except Exception as e:
            print(f"Cannot load icon: {e}")

        self.interface_style()
        self.pack(fill=tk.BOTH, expand=True)

        self.create_widgets()

        self.check_button_enabled = IntVar()
        self.is_parsing = False
        self.phone_excel_path = None  # Путь к Excel файлу для парсера телефонов
        self.is_decoding = False

        self.output_excel = "hh_parse_results/data.xlsx"

    def interface_style(self):
        sv_ttk.set_theme("light")

    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        self.top_level_menu()
        self.create_parser_controls()
        self.create_status_bar()

    def top_level_menu(self):
        """Верхнее меню"""
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)

        parse_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Парсинг", menu=parse_menu)
        parse_menu.add_command(
            label="Открыть Excel файл...", accelerator="Ctrl+O", command=self.btn_open
        )
        self.parent.bind("<Control-o>", lambda _: self.btn_open())  # Горячие клавиши
        self.parent.bind("<Control-l>", lambda _: self.clear_log())
        self.parent.bind("<Control-q>", lambda _: self.btn_exit())
        self.parent.bind("<Control-s>", lambda _: self.stop_parsing())
        self.parent.bind("<Control-g>", lambda _: self.on_continue_clicked())
        self.parent.bind("<Control-k>", lambda _: self.hotkeys_info())
        self.parent.bind("<F1>", lambda _: self.open_link())
        parse_menu.add_separator()
        parse_menu.add_command(label="Выход", command=self.btn_exit)

        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Экспорт", menu=export_menu)
        export_menu.add_command(label="Экспорт готового файла...", command=self.file_to_path)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Руководство пользователя", command=self.open_link)
        help_menu.add_command(label="Горячие клавиши", command=self.hotkeys_info)
        help_menu.add_separator()
        help_menu.add_command(label="О программе", command=self.btn_about)

    def create_parser_controls(self):
        """Создание элементов управления для парсера"""
        # Основной фрейм с grid для точного контроля
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Конфигурация grid - основной контейнер
        main_frame.grid_columnconfigure(0, weight=1)

        # Счетчик строк для grid
        row = 0

        # 2. Фрейм для темы парсера
        theme_frame = ttk.LabelFrame(main_frame, text="Тема парсера", padding=10)
        theme_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        theme_frame.config(height=70)

        self.parser_mode_t = tk.StringVar(value="tlight")

        ttk.Radiobutton(theme_frame, text="Светлая тема",
                        variable=self.parser_mode_t,
                        value="tlight",
                        command=self.theme_parser_mode).grid(row=0, column=0, sticky=tk.W, padx=15, pady=0)

        ttk.Radiobutton(theme_frame, text="Темная тема",
                        variable=self.parser_mode_t,
                        value="tdark",
                        command=self.theme_parser_mode).grid(row=0, column=1, sticky=tk.W, padx=15, pady=0)

        row += 1

        # 3. Фрейм для параметров парсинга
        self.params_frame = ttk.LabelFrame(main_frame, text="Параметры парсинга", padding=8)
        self.params_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        self.params_frame.config(height=90)

        self.create_phone_params()

        row += 1

        # 4. Дополнительные параметры
        common_frame = ttk.LabelFrame(main_frame, text="Дополнительные параметры", padding=10)
        common_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        common_frame.config(height=90)

        # Содержимое common_frame
        ttk.Label(common_frame, text="Количество фирм:").grid(
            row=0, column=0, sticky=tk.W, pady=0
        )
        self.firm_count_var = tk.IntVar(value=50)
        self.firm_count_spinbox = ttk.Spinbox(
            common_frame, from_=1, to=10000, textvariable=self.firm_count_var, width=15
        )
        self.firm_count_spinbox.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        row += 1

        # 5. Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, sticky=tk.W, padx=20, pady=4)
        button_frame.config(height=40)

        # Используем grid для всех кнопок внутри button_frame
        ttk.Button(button_frame, text="Начать парсинг", 
                   command=self.start_sorting, width=20).grid(row=0, column=0, padx=5, pady=0, sticky=tk.W)
        ttk.Button(button_frame, text="Вход выполнен", 
                   command=self.on_continue_clicked, width=20,).grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)
        ttk.Button(button_frame, text="Остановить парсинг", 
                   command=self.stop_parsing, width=20).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(button_frame, text="Очистить лог", 
                   command=self.clear_log, width=20).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        row += 1

        # Лог выполнения
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding=10)
        log_frame.grid(row=row, column=0, sticky=tk.NSEW, padx=10, pady=0)

        # Настраиваем вес строки для растягивания лога
        main_frame.grid_rowconfigure(row, weight=1)

        # Создаем текстовое поле для логов
        self.log_text = tk.Text(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Добавляем раскраску вывода текста в "Лог выполнения"
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="#cf7c00")
        self.log_text.tag_config("SUCCESS", foreground="#00a800")

        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def start_sorting(self):
        """Запуск парсинга"""
        if not self.phone_excel_path:
            self.log_message("Ошибка! Сначала выберите Excel файл")
            self.status_var.set("Сначала выберите Excel файл")
            return

        if not os.path.exists(self.phone_excel_path):
            self.log_message(f"Ошибка! Файл не найден: {self.phone_excel_path}")
            self.status_var.set(f"Файл не найден: {os.path.basename(self.phone_excel_path)}")
            return

        try:
            self.is_parsing = True
            self.parser_instance = HHParse(
                input_file=self.phone_excel_path,
                max_num_firm=self.firm_count_var.get(),
                gui_works=True  # GUI режим
            )
            
            print("Запуск парсинга в отдельном потоке...")
            self.log_message("Запуск парсинга...")
            
            # Создаем и запускаем runner
            runner = AsyncParserRunner(
                self.parser_instance,
                update_callback=self.update_gui_from_thread,
                completion_callback=self.on_parsing_complete,
            )
            runner.start()  # Запускаем ТОЛЬКО ОДИН раз
            
        except Exception as e:
            self.log_message(f"Ошибка при запуске парсинга: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка при запуске:\n{str(e)}")
            self.status_var.set("Ошибка запуска")
            self.is_parsing = False

    def theme_parser_mode(self):
        """Переключение между темой парсера"""
        current_geometry = self.parent.geometry()  # Сохраняем текущие размеры окна

        if self.parser_mode_t.get() == "tlight":
            sv_ttk.set_theme("light")
            self.log_text.tag_config("INFO", foreground="black")
            self.log_text.tag_config("WARNING", foreground="#cf7c00")
            self.log_text.tag_config("SUCCESS", foreground="#00a800")
        else:
            sv_ttk.set_theme("dark")
            self.log_text.tag_config("INFO", foreground="white")
            self.log_text.tag_config("WARNING", foreground="#ffc766")
            self.log_text.tag_config("SUCCESS", foreground="#00e600")

        # Принудительно обновляем интерфейс
        self.parent.update_idletasks()

        # Восстанавливаем размеры окна
        self.parent.geometry(current_geometry)

    def create_phone_params(self):
        """Создание элементов для парсера Email"""
        self.phone_frame = ttk.Frame(self.params_frame)
        self.phone_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Загрузить Excel файл
        ttk.Label(self.phone_frame, text="Выбрать файл:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)

        self.excel_file_btn = ttk.Button(self.phone_frame, text="Excel файл", command=self.btn_open, width=20)
        self.excel_file_btn.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        # Путь к файлу (необязательно, но полезно)
        self.excel_file_path = tk.StringVar()
        ttk.Label(
            self.phone_frame,
            textvariable=self.excel_file_path,
            foreground="gray",
            wraplength=300,
        ).grid(row=1, column=1, padx=5, pady=0, sticky=tk.W)

    def file_to_path(self):
        """Копирование конкретного файла в выбранную папку"""
        if not os.path.exists(self.output_excel):
            self.log_message("Ошибка экспорта объявлений! Исходный файл не найден.")
            self.status_var.set("Исходный файл не найден.")
            return

        target_folder = filedialog.askdirectory(title="Выберите папку для копирования файла")

        if not target_folder:
            return

        try:
            filename = os.path.basename(self.output_excel)
            target_path = os.path.join(target_folder, filename)

            # Проверка на существование
            if os.path.exists(target_path):
                overwrite = messagebox.askyesno("Подтверждение", f"Файл '{filename}' уже существует. Заменить?")
                if not overwrite:
                    return

            shutil.copy2(self.output_excel, target_path)

            self.log_message(f"Успех! Файл '{filename}' успешно скопирован в:\n{target_folder}")
            self.status_var.set(f"Файл '{filename}' успешно скопирован!")

        except Exception as e:
            self.log_message(f"Ошибка! Не удалось скопировать файл:\n{str(e)}")
            self.status_var.set("Не удалось скопировать файл.")

    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, padding=(10, 5))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_data(self, file_path):
        """Загружаю Excel файл с одним столбцом email"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext in [".xlsx", ".xls"]:
                # Читаем Excel без заголовков
                df = pd.read_excel(
                    file_path,
                    header=None,  # Не используем первую строку как заголовок
                )

                # Проверяем, что файл содержит хотя бы один столбец
                if df.empty or df.shape[1] == 0:
                    raise ValueError("Excel файл пуст или не содержит данных")

                # Берем только первый столбец
                df = df.iloc[:, 0:1]  # Только первый столбец

                return df

            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_ext}. Нужен .xlsx или .xls")

        except Exception as e:
            raise ValueError(f"Ошибка загрузки файла: {str(e)}")

    def on_continue_clicked(self):
        """Обработчик нажатия кнопки 'Вход выполнен'"""
        try:
            if hasattr(self, "parser_instance") and self.parser_instance:
                # Отправляем подтверждение в парсер
                self.parser_instance.trigger_enter_from_gui()
                self.log_message("Подтверждение входа отправлено парсеру")
                self.status_var.set("Парсинг продолжается...")
            else:
                self.log_message("Ошибка: парсер не инициализирован")
        except Exception as e:
            self.log_message(f"Ошибка отправки подтверждения: {str(e)}")

    def btn_open(self):
        """Обработчик кнопки 'Excel файл'"""
        self.file_path = filedialog.askopenfilename(
            title="Выберите Excel файл с ссылками на объявления",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if self.file_path:
            # Сохраняем путь для парсера телефонов
            self.phone_excel_path = self.file_path

            # Отображаем имя файла в интерфейсе
            file_name = os.path.basename(self.file_path)
            if len(file_name) > 30:
                # Обрезаем первые 20 символов, добавляем "...", затем пробел и расширение
                file_basename = file_name[:25] + "... " + file_name[file_name.rfind(".") :]
            else:
                file_basename = file_name
            self.excel_file_path.set(f"Выбран: {file_basename}")

            self.update_idletasks()
            try:
                # Загружаем для проверки
                self.df = self.load_data(self.file_path)

                self.log_message(f"Excel файл успешно загружен!")
                self.log_message(f"Количество строк: {len(self.df)}")
                self.log_message(f"Теперь можете запустить парсинг объявлений.")
                self.status_var.set(f"Количество строк в Excel: {len(self.df)}")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")
                self.status_var.set("Ошибка загрузки файла")
                self.phone_excel_path = None

    def on_parsing_complete(self, flag=True):
        """Вызывается при завершении парсинга (успешном или с ошибкой)"""

        def update():
            self.is_parsing = False
            if flag:
                self.status_var.set("Парсинг завершен")
                self.log_message("Парсинг завершен")
            else:
                self.status_var.set("Парсинг остановлен")
                self.log_message("Парсинг остановлен")

        # Выполняем в основном потоке GUI
        self.after(0, update)

    def stop_parsing(self):
        """Остановка парсинга - просто закрываем Chrome"""
        if not self.is_parsing:
            self.log_message("Ничего не выполняется!")
            return

        self.is_parsing = False

        # Просто закрываем Chrome через taskkill
        try:
            if os.name == "nt":  # Windows
                # Команда для закрытия Chrome
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    self.log_message("Chrome успешно закрыт")
                else:
                    self.log_message(f"Chrome закрыт (код: {result.returncode})")

            else:  # Linux/Mac
                subprocess.run(["pkill", "chrome"], capture_output=True)
                self.log_message("Chrome закрыт")

        except Exception as e:
            self.log_message(f"При закрытии Chrome: {str(e)}")

        self.status_var.set("Парсинг остановлен")
        self.log_message("Парсинг остановлен пользователем")

    def log_message(self, message):
        """Добавление сообщения в лог с цветами"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Определяем уровень
        msg_lower = message.lower()
        error_words = ["ошибка", "error", "closed", "exception", "failed", "прервано"]
        warning_words = ["предупреждение", "warning", "внимание", "остановлен"]
        success_words = ["успешно", "success", "завершен", "готово", "успешн"]

        if any(word in msg_lower for word in error_words):
            level = "ERROR"
        elif any(word in msg_lower for word in warning_words):
            level = "WARNING"
        elif any(word in msg_lower for word in success_words):
            level = "SUCCESS"
        else:
            level = "INFO"

        formatted_message = f"[{timestamp}] [{level}] {message}\n"

        # Вставляем с тегом
        self.log_text.insert(tk.END, formatted_message, (level,))
        self.log_text.see(tk.END)

    def clear_log(self):
        """Очистка лога"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Лог очищен")
        self.status_var.set("Лог очищен")

    def update_gui_from_thread(self, message):
        """Обновление GUI из потока"""

        def update():
            self.log_message(message)
            self.status_var.set(message[:50] + "..." if len(message) > 50 else message)

        self.after(0, update)

    def open_link(self):
        webbrowser.open("https://github.com/itrickon/HHParser")

    def hotkeys_info(self):
        """Обработчик кнопки 'Горячие клавиши'"""
        # Создаем собственное окно вместо messagebox
        top = Toplevel()
        top.title("Горячие клавиши")
        
        # Создаем Frame для размещения текстового виджета и скроллбара
        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Создаем текстовое поле
        text_widget = Text(frame, wrap=tk.WORD, width=60, height=12, 
                        font=("Arial", 10))
        
        
        top.resizable(False, False)
        
        # Добавляем остальной текст
        cities = [
        "       Горячие клавиши приложения:\n",
        "   Основные операции:\n",
        "     • Ctrl + O   - Открыть Excel файл...\n",
        "     • Ctrl + S   - Остановить парсинг\n",
        "     • Ctrl + L    - Очистить лог\n",
        "     • Ctrl + Q   - Выйти из приложения\n",
        "     • Ctrl + G   - Вход выполнен\n",
        "     • Ctrl + K   - Горячие клавиши\n",
        "   Дополнительные:\n",
        "     • F1         - Руководство пользователя\n",
        "   Сочетания клавиш работают в любом месте приложения.\n",
        ]
        
        for city_text in cities:
            text_widget.insert(tk.END, city_text)
        
        text_widget.configure(state='disabled')  # Только для чтения
        
        # Кнопка закрытия
        button = tk.Button(top, text="Закрыть", command=top.destroy)
        
        text_widget.pack()
        button.pack(pady=10)
        
        # Центрируем окно
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f'{width}x{height}+{x}+{y}')

    def btn_about(self):
        """Обработчик кнопки 'О программе'"""
        # Создаем собственное окно вместо messagebox
        top = Toplevel()
        top.title("О программе")

        # Создаем Frame для размещения текстового виджета и скроллбара
        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Создаем текстовое поле
        text_widget = Text(frame, wrap=tk.WORD, width=55, height=20, font=("Arial", 10))

        top.resizable(False, False)

        # Добавляем остальной текст
        about_text = [
            "       HHParser\n\n",
            "  Desktop-приложение для анализа данных, предназначенное для сбора информации из объявлений.\n\n",
            "  Данный инструмент предназначен для сбора открытой информации в образовательных и исследовательских целях.\n\n",
            "    Версия 0.1.5\n\n",
            "  Возможности:\n",
            "    • Поддержка светлой и темной темы\n\n",
            "  Используемые технологии:\n",
            "    • Python 3.13+\n",
            "    • tkinter для графического интерфейса\n",
            "    • sv_ttk для современных стилей\n\n",
            "    https://github.com/itrickon/HHParser",
        ]

        for city_text in about_text:
            text_widget.insert(tk.END, city_text)

        text_widget.configure(state="disabled")  # Только для чтения

        # Кнопка закрытия
        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        # Центрируем окно
        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def btn_exit(self):
        """Выход из приложения"""
        if self.is_parsing:
            if not messagebox.askyesno("Предупреждение", "Парсинг выполняется. Вы уверены, что хотите выйти?"):
                return

        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            if self.is_parsing:
                self.stop_parsing()
            self.parent.quit()


def main():
    """Точка входа в приложение"""
    root = tk.Tk()
    app = HHParser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
