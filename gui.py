import os
import re
import sv_ttk
import shutil
import datetime
import subprocess
import threading
import webbrowser
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, IntVar, Toplevel, Text
from hh_phone_search import HHParse
from hh_url_collector import HHVacancyCollector
from Main_HH_files.async_runner import AsyncParserRunner


class HHParser(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("HHParser")
        self.parent.geometry("550x700")

        try:
            self.parent.iconbitmap("static/HHParse_logo.ico")
        except Exception as e:
            print(f"Cannot load icon: {e}")

        self.interface_style()
        self.pack(fill=tk.BOTH, expand=True)

        self.create_widgets()

        self.is_parsing = False
        self.phone_excel_path = None  # Путь к Excel файлу для парсера телефонов

        self.output_excel = "hh_parse_results/data.xlsx"
        self.url_search_output = "hh_parse_results/hh_url_search_results.xlsx"

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
        self.parent.bind("<Control-o>", lambda _: self.btn_open())
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
        export_menu.add_command(label="Экспорт поиска по URL...", command=self.export_url_search_results)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Руководство пользователя", command=self.open_link)
        help_menu.add_command(label="Горячие клавиши", command=self.hotkeys_info)
        help_menu.add_separator()
        help_menu.add_command(label="О программе", command=self.btn_about)

    def create_parser_controls(self):
        """Создание элементов управления для парсера"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.grid_columnconfigure(0, weight=1)

        row = 0

        # 1. Фрейм для выбора режима парсинга
        mode_frame = ttk.LabelFrame(main_frame, text="Режим работы", padding=10)
        mode_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        mode_frame.config(height=70)

        self.parser_mode_key = tk.StringVar(value="phone")

        ttk.Radiobutton(
            mode_frame, text="Парсер телефонов",
            variable=self.parser_mode_key,
            value="phone",
            command=self.toggle_parser_mode
        ).grid(row=0, column=0, sticky=tk.W, padx=15, pady=0)

        ttk.Radiobutton(
            mode_frame, text="Поиск по URL",
            variable=self.parser_mode_key,
            value="url",
            command=self.toggle_parser_mode
        ).grid(row=0, column=1, sticky=tk.W, padx=15, pady=0)

        row += 1

        # 2. Фрейм для темы парсера
        theme_frame = ttk.LabelFrame(main_frame, text="Тема парсера", padding=10)
        theme_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        theme_frame.config(height=70)

        self.parser_mode_t = tk.StringVar(value="tlight")

        ttk.Radiobutton(
            theme_frame, text="Светлая тема",
            variable=self.parser_mode_t,
            value="tlight",
            command=self.theme_parser_mode
        ).grid(row=0, column=0, sticky=tk.W, padx=15, pady=0)

        ttk.Radiobutton(
            theme_frame, text="Темная тема",
            variable=self.parser_mode_t,
            value="tdark",
            command=self.theme_parser_mode
        ).grid(row=0, column=1, sticky=tk.W, padx=15, pady=0)

        row += 1

        # 3. Фрейм для параметров парсинга
        self.params_frame = ttk.LabelFrame(main_frame, text="Параметры парсинга", padding=8)
        self.params_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        self.params_frame.config(height=120)

        self.create_phone_params()
        self.create_url_params()

        row += 1

        # 4. Дополнительные параметры
        common_frame = ttk.LabelFrame(main_frame, text="Дополнительные параметры", padding=10)
        common_frame.grid(row=row, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        common_frame.config(height=70)

        ttk.Label(common_frame, text="Количество вакансий:").grid(
            row=0, column=0, sticky=tk.W, pady=0
        )
        self.firm_count_var = tk.IntVar(value=10)
        self.firm_count_spinbox = ttk.Spinbox(
            common_frame, from_=1, to=50000, textvariable=self.firm_count_var, width=15
        )
        self.firm_count_spinbox.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        row += 1

        # 5. Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, sticky=tk.W, padx=20, pady=4)
        button_frame.config(height=40)

        ttk.Button(
            button_frame, text="Начать парсинг",
            command=self.start_parsing, width=20
        ).grid(row=0, column=0, padx=5, pady=0, sticky=tk.W)
        
        self.continue_btn = ttk.Button(
            button_frame, text="Вход выполнен",
            command=self.on_continue_clicked, width=20
        )
        self.continue_btn.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)
        
        ttk.Button(
            button_frame, text="Остановить парсинг",
            command=self.stop_parsing, width=20
        ).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(
            button_frame, text="Очистить лог",
            command=self.clear_log, width=20
        ).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        row += 1

        # Лог выполнения
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding=10)
        log_frame.grid(row=row, column=0, sticky=tk.NSEW, padx=10, pady=0)

        main_frame.grid_rowconfigure(row, weight=1)

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="#cf7c00")
        self.log_text.tag_config("SUCCESS", foreground="#00a800")

        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

        # Инициализация видимости фреймов
        self.toggle_parser_mode()

    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, padding=(10, 5))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def theme_parser_mode(self):
        """Переключение между темой парсера"""
        current_geometry = self.parent.geometry()

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

        self.parent.update_idletasks()
        self.parent.geometry(current_geometry)

    def toggle_parser_mode(self):
        """Переключение между режимами парсинга"""
        mode = self.parser_mode_key.get()

        # Скрываем все фреймы
        self.phone_frame.place_forget()
        self.url_frame.place_forget()

        # Показываем нужный фрейм и настраиваем кнопки
        if mode == "phone":
            self.phone_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.firm_count_spinbox.config(state=tk.NORMAL)
            self.continue_btn.config(state=tk.NORMAL)
        elif mode == "url":
            self.url_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.firm_count_spinbox.config(state=tk.NORMAL)
            self.continue_btn.config(state=tk.DISABLED)

    def create_phone_params(self):
        """Создание элементов для парсера телефонов"""
        self.phone_frame = ttk.Frame(self.params_frame)

        ttk.Label(self.phone_frame, text="Выбрать файл:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)

        self.excel_file_btn = ttk.Button(
            self.phone_frame, text="Excel файл",
            command=self.btn_open, width=25
        )
        self.excel_file_btn.grid(row=0, column=1, padx=5, pady=0, sticky=tk.W)

        self.excel_file_path = tk.StringVar()
        ttk.Label(
            self.phone_frame, textvariable=self.excel_file_path,
            foreground="gray", wraplength=300,
        ).grid(row=1, column=1, padx=5, pady=0, sticky=tk.W)

    def create_url_params(self):
        """Создание элементов для поиска по URL"""
        self.url_frame = ttk.Frame(self.params_frame)

        ttk.Label(
            self.url_frame,
            text="Введите URL страницы поиска HH.ru (например: https://saratov.hh.ru/search/vacancy?area=1234)",
            wraplength=450, foreground="gray"
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        self.url_entry = ttk.Entry(self.url_frame, width=45)
        self.url_entry.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

    def start_parsing(self):
        """Запуск парсинга в зависимости от режима"""
        mode = self.parser_mode_key.get()

        if mode == "phone":
            self.start_phone_parsing()
        elif mode == "url":
            self.start_url_search()

    def start_phone_parsing(self):
        """Запуск парсера телефонов"""
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
                gui_works=True
            )

            self.log_message("Запуск парсинга...")

            runner = AsyncParserRunner(
                self.parser_instance,
                update_callback=self.update_gui_from_thread,
                completion_callback=self.on_parsing_complete,
            )
            runner.start()

        except Exception as e:
            self.log_message(f"Ошибка при запуске парсинга: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка при запуске:\n{str(e)}")
            self.status_var.set("Ошибка запуска")
            self.is_parsing = False

    def start_url_search(self):
        """Запуск поиска по URL страницы"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning("Внимание", "Введите URL страницы поиска")
            return

        # Проверяем, что это URL поиска hh.ru/search/vacancy
        if not re.search(r"hh\.ru/search/vacancy", url):
            messagebox.showwarning("Внимание", "Неверный формат URL.\nПример: https://saratov.hh.ru/search/vacancy?area=1234")
            return

        if self.is_parsing:
            messagebox.showwarning("Внимание", "Поиск уже выполняется")
            return

        self.is_parsing = True
        max_vacancies = self.firm_count_var.get()
        
        self.log_message(f"Начало сбора вакансий: {url}")
        self.log_message(f"Максимальное количество: {max_vacancies}")
        self.status_var.set(f"Сбор вакансий: {max_vacancies} шт.")

        self.parser_instance = HHVacancyCollector(search_url=url, max_vacancies=max_vacancies)

        runner = AsyncParserRunner(
            self.parser_instance,
            update_callback=self.update_gui_from_thread,
            completion_callback=self.on_url_search_complete,
        )
        runner.start()

    def on_url_search_complete(self, flag=True):
        """Завершение поиска по URL"""
        def update():
            self.is_parsing = False
            if flag:
                count = len(self.parser_instance.vacancies) if hasattr(self.parser_instance, 'vacancies') else 0
                self.status_var.set("Поиск завершен")
                self.log_message(f"SUCCESS: Найдено вакансий: {count}", "SUCCESS")
                messagebox.showinfo(
                    "Результат поиска",
                    f"Найдено вакансий: {count}\n\n"
                    f"Результаты сохранены в:\n{self.url_search_output}"
                )
            else:
                self.status_var.set("Поиск остановлен")
                self.log_message("Поиск остановлен")
        self.after(0, update)

    def on_parsing_complete(self, flag=True):
        """Вызывается при завершении парсинга"""
        def update():
            self.is_parsing = False
            if flag:
                self.status_var.set("Парсинг завершен")
                self.log_message("Парсинг завершен")
            else:
                self.status_var.set("Парсинг остановлен")
                self.log_message("Парсинг остановлен")
        self.after(0, update)

    def stop_parsing(self):
        """Остановка парсинга"""
        if not self.is_parsing:
            self.log_message("Ничего не выполняется!")
            return

        self.is_parsing = False

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    self.log_message("Chrome успешно закрыт")
                else:
                    self.log_message(f"Chrome закрыт (код: {result.returncode})")
            else:
                subprocess.run(["pkill", "chrome"], capture_output=True)
                self.log_message("Chrome закрыт")
        except Exception as e:
            self.log_message(f"При закрытии Chrome: {str(e)}")

        self.status_var.set("Парсинг остановлен")
        self.log_message("Парсинг остановлен пользователем")

    def log_message(self, message, level=None):
        """Добавление сообщения в лог с цветами"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        if level is None:
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
        """Информация о горячих клавишах"""
        top = Toplevel()
        top.title("Горячие клавиши")

        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        text_widget = Text(frame, wrap=tk.WORD, width=60, height=12, font=("Arial", 10))
        top.resizable(False, False)

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

        text_widget.configure(state='disabled')

        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f'{width}x{height}+{x}+{y}')

    def btn_about(self):
        """О программе"""
        top = Toplevel()
        top.title("О программе")

        frame = tk.Frame(top)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        text_widget = Text(frame, wrap=tk.WORD, width=55, height=20, font=("Arial", 10))
        top.resizable(False, False)

        about_text = [
            "       HHParser\n\n",
            "  Desktop-приложение для анализа данных, предназначенное для сбора информации из объявлений.\n\n",
            "  Данный инструмент предназначен для сбора открытой информации в образовательных и исследовательских целях.\n\n",
            "  Версия 0.2.0\n\n",
            "  Возможности:\n",
            "    • Парсер телефонов из Excel\n",
            "    • Поиск по URL вакансии\n",
            "    • Поиск вакансий на странице поиска\n",
            "    • Поддержка светлой и темной темы\n\n",
            "  Используемые технологии:\n",
            "    • Python 3.13+\n",
            "    • tkinter для графического интерфейса\n",
            "    • sv_ttk для современных стилей\n\n",
            "    https://github.com/itrickon/HHParser",
        ]

        for city_text in about_text:
            text_widget.insert(tk.END, city_text)

        text_widget.configure(state="disabled")

        button = tk.Button(top, text="Закрыть", command=top.destroy)

        text_widget.pack()
        button.pack(pady=10)

        top.update_idletasks()
        width = top.winfo_width()
        height = top.winfo_height()
        x = (top.winfo_screenwidth() // 2) - (width // 2)
        y = (top.winfo_screenheight() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def btn_open(self):
        """Выбор Excel файла"""
        self.file_path = filedialog.askopenfilename(
            title="Выберите Excel файл с ссылками на объявления",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if self.file_path:
            self.phone_excel_path = self.file_path

            file_name = os.path.basename(self.file_path)
            if len(file_name) > 30:
                file_basename = file_name[:25] + "... " + file_name[file_name.rfind(".") :]
            else:
                file_basename = file_name
            self.excel_file_path.set(f"Выбран: {file_basename}")

            self.update_idletasks()
            try:
                self.df = self.load_data(self.file_path)
                self.log_message(f"Excel файл успешно загружен!")
                self.log_message(f"Количество строк: {len(self.df)}")
                self.log_message(f"Теперь можете запустить парсинг объявлений.")
                self.status_var.set(f"Количество строк в Excel: {len(self.df)}")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")
                self.status_var.set("Ошибка загрузки файла")
                self.phone_excel_path = None

    def load_data(self, file_path):
        """Загрузка Excel файла"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path, header=None)

                if df.empty or df.shape[1] == 0:
                    raise ValueError("Excel файл пуст или не содержит данных")

                df = df.iloc[:, 0:1]

                return df
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_ext}. Нужен .xlsx или .xls")

        except Exception as e:
            raise ValueError(f"Ошибка загрузки файла: {str(e)}")

    def on_continue_clicked(self):
        """Обработчик кнопки 'Вход выполнен'"""
        try:
            if hasattr(self, "parser_instance") and self.parser_instance:
                self.parser_instance.trigger_enter_from_gui()
                self.log_message("Подтверждение входа отправлено парсеру")
                self.status_var.set("Парсинг продолжается...")
            else:
                self.log_message("Ошибка: парсер не инициализирован")
        except Exception as e:
            self.log_message(f"Ошибка отправки подтверждения: {str(e)}")

    def file_to_path(self):
        """Копирование файла в выбранную папку"""
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

    def export_url_search_results(self):
        """Экспорт результатов поиска по URL"""
        if not os.path.exists(self.url_search_output):
            self.log_message("Ошибка экспорта! Файл результатов поиска по URL не найден.")
            self.status_var.set("Файл результатов поиска не найден.")
            messagebox.showwarning("Внимание", "Сначала выполните поиск по URL")
            return

        target_folder = filedialog.askdirectory(title="Выберите папку для копирования файла")

        if not target_folder:
            return

        try:
            filename = os.path.basename(self.url_search_output)
            target_path = os.path.join(target_folder, filename)

            if os.path.exists(target_path):
                overwrite = messagebox.askyesno("Подтверждение", f"Файл '{filename}' уже существует. Заменить?")
                if not overwrite:
                    return

            shutil.copy2(self.url_search_output, target_path)

            self.log_message(f"Успех! Файл '{filename}' успешно скопирован в:\n{target_folder}")
            self.status_var.set(f"Файл '{filename}' успешно скопирован!")

        except Exception as e:
            self.log_message(f"Ошибка! Не удалось скопировать файл:\n{str(e)}")
            self.status_var.set("Не удалось скопировать файл.")

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
