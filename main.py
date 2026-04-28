# Smart Study Tracker - by Janvi Gaikwad

import calendar
import random
import tkinter as tk
from datetime import date as dt_date
from tkinter import messagebox, ttk

import mysql.connector

from tracker_utils import (
    build_wellness_insights,
    get_daily_progress,
    get_focus_prediction,
    get_goal_status,
    get_dashboard_summary,
    get_recent_sessions,
    get_subject_breakdown,
    get_streak_status,
    get_study_streak,
    get_user_badges,
    get_user_preferences,
    initialize_database,
    log_study_session,
    login_user,
    mark_goal_popup_shown,
    mark_streak_popup_shown,
    register_user,
    update_daily_goal,
)

TIP_MESSAGES = [
    "Take a 5-minute break every 25 minutes.",
    "Short daily sessions beat irregular long sessions.",
    "Review difficult topics first while your energy is high.",
    "Write one clear goal before each study session.",
]

THEME = {
    "bg": "#f4efe6",
    "panel": "#fcfaf6",
    "card": "#fffdf9",
    "card_alt": "#f6efe4",
    "navy": "#17324d",
    "slate": "#56718c",
    "accent": "#d96c3f",
    "accent_dark": "#b9532b",
    "mint": "#3f8f7a",
    "line": "#dccfbe",
    "soft": "#efe6d7",
    "graph_bg": "#fff8ef",
}


class CalendarPopup:
    def __init__(self, parent, on_select, initial_date=None):
        self.parent = parent
        self.on_select = on_select
        self.selected_date = initial_date or dt_date.today()
        self.current_year = self.selected_date.year
        self.current_month = self.selected_date.month

        self.window = tk.Toplevel(parent)
        self.window.title("Choose Date")
        self.window.configure(bg=THEME["card"])
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        self.header_var = tk.StringVar()

        shell = tk.Frame(
            self.window,
            bg=THEME["card"],
            padx=16,
            pady=16,
            highlightthickness=1,
            highlightbackground=THEME["line"],
        )
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg=THEME["card"])
        header.pack(fill="x", pady=(0, 12))

        tk.Button(
            header,
            text="<",
            command=self.previous_month,
            relief="flat",
            bd=0,
            bg=THEME["soft"],
            fg=THEME["navy"],
            activebackground=THEME["card_alt"],
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            width=3,
        ).pack(side="left")
        tk.Label(
            header,
            textvariable=self.header_var,
            bg=THEME["card"],
            fg=THEME["navy"],
            font=("Georgia", 16, "bold"),
        ).pack(side="left", expand=True)
        tk.Button(
            header,
            text=">",
            command=self.next_month,
            relief="flat",
            bd=0,
            bg=THEME["soft"],
            fg=THEME["navy"],
            activebackground=THEME["card_alt"],
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            width=3,
        ).pack(side="right")

        self.days_frame = tk.Frame(shell, bg=THEME["card"])
        self.days_frame.pack()

        footer = tk.Frame(shell, bg=THEME["card"])
        footer.pack(fill="x", pady=(12, 0))
        tk.Button(
            footer,
            text="Today",
            command=self.pick_today,
            relief="flat",
            bd=0,
            bg=THEME["accent"],
            fg="white",
            activebackground=THEME["accent_dark"],
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=6,
        ).pack(side="left")
        tk.Button(
            footer,
            text="Cancel",
            command=self.window.destroy,
            relief="flat",
            bd=0,
            bg=THEME["soft"],
            fg=THEME["navy"],
            activebackground=THEME["card_alt"],
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=6,
        ).pack(side="right")

        self.render()
        self.center_on_parent()

    def center_on_parent(self):
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x_pos = parent_x + max((parent_w - width) // 2, 0)
        y_pos = parent_y + max((parent_h - height) // 2, 0)
        self.window.geometry(f"+{x_pos}+{y_pos}")

    def previous_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render()

    def pick_today(self):
        today = dt_date.today()
        self.on_select(today.strftime("%Y-%m-%d"))
        self.window.destroy()

    def pick_day(self, day_number):
        chosen = dt_date(self.current_year, self.current_month, day_number)
        self.on_select(chosen.strftime("%Y-%m-%d"))
        self.window.destroy()

    def render(self):
        self.header_var.set(f"{calendar.month_name[self.current_month]} {self.current_year}")

        for widget in self.days_frame.winfo_children():
            widget.destroy()

        for column, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            tk.Label(
                self.days_frame,
                text=day_name,
                bg=THEME["card"],
                fg=THEME["slate"],
                font=("Segoe UI Semibold", 9),
                width=5,
            ).grid(row=0, column=column, padx=2, pady=(0, 6))

        month_matrix = calendar.monthcalendar(self.current_year, self.current_month)
        today = dt_date.today()

        for row_index, week in enumerate(month_matrix, start=1):
            for column, day_number in enumerate(week):
                if day_number == 0:
                    tk.Label(self.days_frame, text="", bg=THEME["card"], width=5).grid(
                        row=row_index, column=column, padx=2, pady=2
                    )
                    continue

                chosen_day = dt_date(self.current_year, self.current_month, day_number)
                is_today = chosen_day == today
                bg_color = THEME["accent"] if is_today else THEME["soft"]
                fg_color = "white" if is_today else THEME["navy"]

                tk.Button(
                    self.days_frame,
                    text=str(day_number),
                    command=lambda value=day_number: self.pick_day(value),
                    relief="flat",
                    bd=0,
                    bg=bg_color,
                    fg=fg_color,
                    activebackground=THEME["card_alt"],
                    activeforeground=THEME["navy"],
                    cursor="hand2",
                    font=("Segoe UI", 10),
                    width=5,
                    pady=6,
                ).grid(row=row_index, column=column, padx=2, pady=2)


class StreakPopup:
    def __init__(self, parent, streak_days, new_badges):
        self.parent = parent
        self.streak_days = streak_days
        self.new_badges = new_badges
        self.current_value = 0
        self.pulse_step = 0

        self.window = tk.Toplevel(parent)
        self.window.title("Streak Celebration")
        self.window.configure(bg=THEME["navy"])
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        shell = tk.Frame(
            self.window,
            bg=THEME["navy"],
            padx=24,
            pady=24,
            highlightthickness=2,
            highlightbackground=THEME["accent"],
            bd=0,
        )
        shell.pack(fill="both", expand=True)

        tk.Label(
            shell,
            text="STREAK UP",
            bg=THEME["navy"],
            fg="#ffdcbf",
            font=("Segoe UI Semibold", 11),
        ).pack()
        tk.Label(
            shell,
            text="You showed up again.",
            bg=THEME["navy"],
            fg="white",
            font=("Georgia", 22, "bold"),
        ).pack(pady=(8, 8))

        self.day_value_var = tk.StringVar(value="0")
        self.day_label = tk.Label(
            shell,
            textvariable=self.day_value_var,
            bg=THEME["navy"],
            fg=THEME["accent"],
            font=("Georgia", 40, "bold"),
        )
        self.day_label.pack()
        tk.Label(
            shell,
            text="day streak",
            bg=THEME["navy"],
            fg="#d5e1ec",
            font=("Segoe UI", 12),
        ).pack(pady=(0, 14))

        if new_badges:
            badge_names = ", ".join(badge["badge_name"] for badge in new_badges)
            tk.Label(
                shell,
                text=f"Badge unlocked: {badge_names}",
                bg="#24486b",
                fg="#fff5e8",
                padx=14,
                pady=10,
                font=("Segoe UI Semibold", 11),
            ).pack(fill="x", pady=(0, 12))

        tk.Label(
            shell,
            text="Come back tomorrow and protect the streak.",
            bg=THEME["navy"],
            fg="#d5e1ec",
            font=("Segoe UI", 10),
        ).pack()

        tk.Button(
            shell,
            text="Keep Going",
            command=self.window.destroy,
            relief="flat",
            bd=0,
            bg=THEME["accent"],
            fg="white",
            activebackground=THEME["accent_dark"],
            activeforeground="white",
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            padx=18,
            pady=8,
        ).pack(pady=(18, 0))

        self.center_on_parent()
        self.animate_count()
        self.animate_pulse()

    def center_on_parent(self):
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x_pos = parent_x + max((parent_w - width) // 2, 0)
        y_pos = parent_y + max((parent_h - height) // 2, 0)
        self.window.geometry(f"+{x_pos}+{y_pos}")

    def animate_count(self):
        if self.current_value >= self.streak_days:
            self.day_value_var.set(str(self.streak_days))
            return
        self.current_value += 1
        self.day_value_var.set(str(self.current_value))
        self.window.after(90, self.animate_count)

    def animate_pulse(self):
        pulse_colors = [THEME["accent"], "#ffb17c", "#ffe0ca", "#ffb17c"]
        self.day_label.configure(fg=pulse_colors[self.pulse_step % len(pulse_colors)])
        self.pulse_step += 1
        if self.window.winfo_exists():
            self.window.after(180, self.animate_pulse)


class GoalCelebrationPopup:
    def __init__(self, parent, today_hours, goal_hours):
        self.parent = parent
        self.today_hours = today_hours
        self.goal_hours = goal_hours
        self.spark_step = 0

        self.window = tk.Toplevel(parent)
        self.window.title("Goal Complete")
        self.window.configure(bg=THEME["card"])
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        shell = tk.Frame(
            self.window,
            bg=THEME["card"],
            padx=24,
            pady=24,
            highlightthickness=2,
            highlightbackground=THEME["mint"],
            bd=0,
        )
        shell.pack(fill="both", expand=True)

        self.spark_var = tk.StringVar(value="*  *  *")
        tk.Label(
            shell,
            textvariable=self.spark_var,
            bg=THEME["card"],
            fg=THEME["accent"],
            font=("Georgia", 20, "bold"),
        ).pack()
        tk.Label(
            shell,
            text="Daily Goal Complete",
            bg=THEME["card"],
            fg=THEME["navy"],
            font=("Georgia", 24, "bold"),
        ).pack(pady=(8, 8))
        tk.Label(
            shell,
            text=f"You studied {today_hours:.2f} hours today and cleared your {goal_hours:.2f}-hour target.",
            bg=THEME["card"],
            fg=THEME["slate"],
            font=("Segoe UI", 11),
            wraplength=360,
            justify="center",
        ).pack()
        tk.Label(
            shell,
            text="Protect the streak and end the day with one short review.",
            bg=THEME["card_alt"],
            fg=THEME["navy"],
            padx=12,
            pady=10,
            font=("Segoe UI Semibold", 10),
        ).pack(fill="x", pady=(16, 0))
        tk.Button(
            shell,
            text="Nice",
            command=self.window.destroy,
            relief="flat",
            bd=0,
            bg=THEME["accent"],
            fg="white",
            activebackground=THEME["accent_dark"],
            activeforeground="white",
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            padx=18,
            pady=8,
        ).pack(pady=(18, 0))

        self.center_on_parent()
        self.animate_spark()

    def center_on_parent(self):
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x_pos = parent_x + max((parent_w - width) // 2, 0)
        y_pos = parent_y + max((parent_h - height) // 2, 0)
        self.window.geometry(f"+{x_pos}+{y_pos}")

    def animate_spark(self):
        frames = ["*  *  *", "o  *  o", "*  o  *", "o  o  o"]
        self.spark_var.set(frames[self.spark_step % len(frames)])
        self.spark_step += 1
        if self.window.winfo_exists():
            self.window.after(180, self.animate_spark)


class StudyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Study Tracker")
        self.root.geometry("1180x760")
        self.root.configure(bg=THEME["bg"])
        self.root.minsize(1080, 700)
        self.user = None
        self.summary_labels = {}
        self.breakdown_var = tk.StringVar(value="No data yet.")
        self.goal_progress_var = tk.StringVar(value="Today's goal progress: 0%")
        self.goal_entry = None
        self.goal_progress = None
        self.wellness_headline_var = tk.StringVar(value="Start with one focused session.")
        self.wellness_message_var = tk.StringVar(value="Small consistent effort beats burnout.")
        self.wellness_action_var = tk.StringVar(value="Set a realistic goal and protect one focus block.")
        self.badge_var = tk.StringVar(value="No badges unlocked yet.")
        self.ai_insight_var = tk.StringVar(
            value="AI Insights: log a few sessions with notes, then run `python -m ml.train --user-id <id>` to enable predictions."
        )
        self.timer_label_var = tk.StringVar(value="25:00")
        self.timer_status_var = tk.StringVar(value="Ready for a focus sprint")
        self.timer_mode = "focus"
        self.timer_running = False
        self.timer_after_id = None
        self.remaining_seconds = 25 * 60
        self.progress_canvas = None
        self.subject_canvas = None
        self.top_subjects_canvas = None
        self.top_subject_rows = []
        self.top_subject_hover_index = None
        self.hero_status_var = tk.StringVar(value="Track attention, avoid burnout, and build consistency.")
        self.hero_default_text = "Track attention, avoid burnout, and build consistency."
        self.date_var = tk.StringVar(value="")
        self.analytics_scroll_canvas = None
        self._cached_top_subjects = []
        self._cached_progress = []
        self._cached_subject_breakdown = []
        self.configure_styles()
        self.build_login_ui()
        self.center_window()
        self.root.after(150, self.bring_to_front)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def configure_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(
            "App.TNotebook",
            background=THEME["bg"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        self.style.configure(
            "App.TNotebook.Tab",
            background=THEME["soft"],
            foreground=THEME["navy"],
            padding=(18, 10),
            font=("Segoe UI Semibold", 10),
            borderwidth=0,
        )
        self.style.map(
            "App.TNotebook.Tab",
            background=[("selected", THEME["card"]), ("active", THEME["card_alt"])],
            foreground=[("selected", THEME["accent_dark"])],
        )
        self.style.configure(
            "App.Treeview",
            background=THEME["card"],
            fieldbackground=THEME["card"],
            foreground=THEME["navy"],
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "App.Treeview.Heading",
            background=THEME["soft"],
            foreground=THEME["navy"],
            font=("Segoe UI Semibold", 10),
            relief="flat",
            padding=(8, 8),
        )
        self.style.map("App.Treeview.Heading", background=[("active", THEME["card_alt"])])
        self.style.configure(
            "Goal.Horizontal.TProgressbar",
            troughcolor="#eadfce",
            background=THEME["mint"],
            bordercolor="#eadfce",
            lightcolor=THEME["mint"],
            darkcolor=THEME["mint"],
        )
        self.style.configure(
            "App.TCombobox",
            fieldbackground=THEME["card"],
            background=THEME["card"],
            foreground=THEME["navy"],
            bordercolor=THEME["line"],
            arrowcolor=THEME["navy"],
            padding=4,
        )

    def create_card(self, parent, bg=None, padx=18, pady=18):
        return tk.Frame(
            parent,
            bg=bg or THEME["card"],
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=THEME["line"],
            bd=0,
        )

    def create_button(self, parent, text, command, kind="primary", width=None):
        palette = {
            "primary": (THEME["accent"], "white", THEME["accent_dark"]),
            "secondary": (THEME["soft"], THEME["navy"], THEME["card_alt"]),
            "ghost": (THEME["card"], THEME["navy"], THEME["soft"]),
        }
        bg_color, fg_color, active_bg = palette[kind]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=fg_color,
            activebackground=active_bg,
            activeforeground=fg_color,
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            width=width,
        )

    def style_entry(self, entry):
        entry.configure(
            bg=THEME["card"],
            fg=THEME["navy"],
            insertbackground=THEME["navy"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["line"],
            highlightcolor=THEME["accent"],
            bd=0,
        )

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width() or 860
        height = self.root.winfo_height() or 620
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = max((screen_width - width) // 2, 0)
        y_pos = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def bring_to_front(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))

    def build_login_ui(self):
        self.user = None
        self.clear_window()

        container = tk.Frame(self.root, bg=THEME["bg"], padx=40, pady=36)
        container.pack(expand=True, fill="both")

        shell = self.create_card(container, bg=THEME["card"], padx=0, pady=0)
        shell.place(relx=0.5, rely=0.5, anchor="center", width=900, height=500)

        hero = tk.Frame(shell, bg=THEME["navy"], padx=34, pady=34)
        hero.pack(side="left", fill="both", expand=True)
        form = tk.Frame(shell, bg=THEME["card"], padx=38, pady=38)
        form.pack(side="left", fill="both", expand=True)

        tk.Label(
            hero,
            text="Study with\nmore clarity.",
            font=("Georgia", 28, "bold"),
            bg=THEME["navy"],
            fg="#f8f2e8",
            justify="left",
        ).pack(anchor="w", pady=(12, 14))
        tk.Label(
            hero,
            text="Track progress, protect focus, and notice burnout before it becomes your normal routine.",
            font=("Segoe UI", 11),
            bg=THEME["navy"],
            fg="#d5e1ec",
            justify="left",
            wraplength=320,
        ).pack(anchor="w")

        quote = tk.Frame(hero, bg="#22486c", padx=18, pady=16)
        quote.pack(anchor="w", fill="x", pady=(34, 0))
        tk.Label(
            quote,
            text="Daily progress beats panic studying.",
            font=("Segoe UI Semibold", 12),
            bg="#22486c",
            fg="#fff6eb",
        ).pack(anchor="w")
        tk.Label(
            quote,
            text="Use the tracker to spot distraction, low-energy sessions, and missed streaks early.",
            font=("Segoe UI", 10),
            bg="#22486c",
            fg="#d5e1ec",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        tk.Label(
            form,
            text="Smart Study Tracker",
            font=("Georgia", 24, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(16, 6))
        tk.Label(
            form,
            text="Log in to continue or register a new study account.",
            font=("Segoe UI", 10),
            bg=THEME["card"],
            fg=THEME["slate"],
        ).pack(anchor="w", pady=(0, 24))

        tk.Label(form, text="Username", anchor="w", bg=THEME["card"], fg=THEME["navy"]).pack(fill="x")
        self.username_entry = tk.Entry(form, font=("Segoe UI", 11))
        self.style_entry(self.username_entry)
        self.username_entry.pack(fill="x", pady=(6, 14), ipady=8)

        tk.Label(form, text="Password", anchor="w", bg=THEME["card"], fg=THEME["navy"]).pack(fill="x")
        self.password_entry = tk.Entry(form, show="*", font=("Segoe UI", 11))
        self.style_entry(self.password_entry)
        self.password_entry.pack(fill="x", pady=(6, 18), ipady=8)

        buttons = tk.Frame(form, bg=THEME["card"])
        buttons.pack(fill="x")
        self.create_button(buttons, "Login", self.login, kind="primary", width=12).pack(side="left")
        self.create_button(buttons, "Register", self.register, kind="secondary", width=12).pack(side="left", padx=(10, 0))

    def build_dashboard_ui(self):
        self.clear_window()
        self.reset_timer_ui()

        outer = tk.Frame(self.root, bg=THEME["bg"], padx=24, pady=22)
        outer.pack(fill="both", expand=True)

        header = self.create_card(outer, bg=THEME["navy"], padx=24, pady=16)
        header.pack(fill="x", pady=(0, 14))

        header_left = tk.Frame(header, bg=THEME["navy"])
        header_left.pack(side="left", fill="x", expand=True)
        tk.Label(
            header_left,
            text=f"{self.user['username']}'s Study Space",
            font=("Georgia", 24, "bold"),
            bg=THEME["navy"],
            fg="#fff5e8",
        ).pack(anchor="w")
        tk.Label(
            header_left,
            textvariable=self.hero_status_var,
            font=("Segoe UI", 10),
            bg=THEME["navy"],
            fg="#d5e1ec",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        header_actions = tk.Frame(header, bg=THEME["navy"])
        header_actions.pack(side="right", anchor="n")
        self.create_button(header_actions, "Refresh", self.refresh_dashboard, kind="secondary").pack(side="left")
        self.create_button(header_actions, "Logout", self.build_login_ui, kind="ghost").pack(side="left", padx=(10, 0))

        notebook = ttk.Notebook(outer, style="App.TNotebook")
        notebook.pack(fill="both", expand=True)

        dashboard_tab = tk.Frame(notebook, bg=THEME["bg"], padx=0, pady=12)
        analytics_tab = tk.Frame(notebook, bg=THEME["bg"], padx=0, pady=12)
        notebook.add(dashboard_tab, text="Dashboard")
        notebook.add(analytics_tab, text="Analytics")

        body = tk.Frame(dashboard_tab, bg=THEME["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=290)
        body.columnconfigure(1, weight=1, minsize=420)
        body.columnconfigure(2, weight=0, minsize=290)
        body.rowconfigure(0, weight=1)

        left = self.create_card(body, bg=THEME["card_alt"], padx=20, pady=20)
        left.grid(row=0, column=0, sticky="nsew")

        center = tk.Frame(body, bg=THEME["bg"])
        center.grid(row=0, column=1, sticky="nsew", padx=14)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(2, weight=1)

        side = tk.Frame(body, bg=THEME["bg"])
        side.grid(row=0, column=2, sticky="nsew")
        side.columnconfigure(0, weight=1)

        self.build_entry_panel(left)
        self.build_summary_panel(center)
        self.build_wellness_panel(center)
        self.build_history_panel(center)
        self.build_goal_and_timer_panel(side)
        self.build_analytics_tab(analytics_tab)
        self.refresh_dashboard()
        self.root.after(320, self.maybe_show_streak_popup)
        self.root.after(560, self.maybe_show_goal_popup)

    def build_entry_panel(self, parent):
        tk.Label(
            parent,
            text="New Study Session",
            font=("Georgia", 18, "bold"),
            bg=THEME["card_alt"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(0, 12))
        tk.Label(
            parent,
            text="Capture what you studied, how it felt, and what pulled your attention.",
            bg=THEME["card_alt"],
            fg=THEME["slate"],
            wraplength=240,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        tk.Label(parent, text="Subject", bg=THEME["card_alt"], fg=THEME["navy"]).pack(anchor="w")
        self.subject_entry = tk.Entry(parent, font=("Segoe UI", 11))
        self.style_entry(self.subject_entry)
        self.subject_entry.pack(fill="x", pady=(6, 12), ipady=7)

        tk.Label(parent, text="Hours Studied", bg=THEME["card_alt"], fg=THEME["navy"]).pack(anchor="w")
        self.hours_entry = tk.Entry(parent, font=("Segoe UI", 11))
        self.style_entry(self.hours_entry)
        self.hours_entry.pack(fill="x", pady=(6, 12), ipady=7)

        tk.Label(parent, text="Mood", bg=THEME["card_alt"], fg=THEME["navy"]).pack(anchor="w")
        self.mood_entry = tk.StringVar()
        ttk.Combobox(
            parent,
            textvariable=self.mood_entry,
            values=["Focused", "Happy", "Tired", "Stressed"],
            state="readonly",
            style="App.TCombobox",
            font=("Segoe UI", 10),
        ).pack(fill="x", pady=(6, 12))

        tk.Label(parent, text="Session Date", bg=THEME["card_alt"], fg=THEME["navy"]).pack(anchor="w")
        date_box = tk.Frame(
            parent,
            bg=THEME["card"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            bd=0,
        )
        date_box.pack(fill="x", pady=(6, 12))
        tk.Label(
            date_box,
            textvariable=self.date_var,
            bg=THEME["card"],
            fg=THEME["navy"],
            font=("Segoe UI", 10),
            anchor="w",
            width=18,
            padx=10,
            pady=9,
        ).pack(side="left", fill="x", expand=True)
        self.create_button(date_box, "Pick", self.open_date_picker, kind="secondary").pack(side="left", padx=(0, 6), pady=6)
        self.create_button(date_box, "Clear", self.clear_selected_date, kind="ghost").pack(side="left", padx=(0, 6), pady=6)

        tk.Label(parent, text="Notes", bg=THEME["card_alt"], fg=THEME["navy"]).pack(anchor="w")
        self.notes_text = tk.Text(
            parent,
            height=5,
            width=26,
            font=("Segoe UI", 10),
            bg=THEME["card"],
            fg=THEME["navy"],
            insertbackground=THEME["navy"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=THEME["line"],
            highlightcolor=THEME["accent"],
            bd=0,
        )
        self.notes_text.pack(fill="x", pady=(4, 12))

        self.create_button(parent, "Save Session", self.save_session, kind="primary", width=16).pack(anchor="w")

        tk.Label(
            parent,
            text="If you do not choose a date, the session uses today automatically.",
            bg=THEME["card_alt"],
            fg=THEME["slate"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(10, 0))

    def build_summary_panel(self, parent):
        summary_frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=18)
        summary_frame.grid(row=0, column=0, sticky="ew")

        tk.Label(
            summary_frame,
            text="Progress Snapshot",
            font=("Georgia", 18, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(0, 10))

        stats = tk.Frame(summary_frame, bg=THEME["card"])
        stats.pack(fill="x")

        self.summary_labels["today_hours"] = self._build_stat_card(stats, "Today", "0.00 h")
        self.summary_labels["total_hours"] = self._build_stat_card(stats, "Total Hours", "0.00 h")
        self.summary_labels["total_sessions"] = self._build_stat_card(stats, "Sessions", "0")
        self.summary_labels["last_session_date"] = self._build_stat_card(stats, "Last Session", "-")

        tk.Label(
            summary_frame,
            text="Top Subjects",
            font=("Georgia", 15, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(14, 4))
        summary_header = tk.Frame(summary_frame, bg=THEME["card"])
        summary_header.pack(fill="x", pady=(0, 10))
        tk.Label(
            summary_header,
            text="Hover over a lane to spotlight your strongest subject.",
            bg=THEME["card"],
            fg=THEME["slate"],
            font=("Segoe UI", 10),
        ).pack(side="left")
        tk.Label(
            summary_header,
            text="Live mix",
            bg=THEME["soft"],
            fg=THEME["accent_dark"],
            font=("Segoe UI Semibold", 9),
            padx=10,
            pady=4,
        ).pack(side="right")
        self.top_subjects_canvas = tk.Canvas(
            summary_frame,
            bg=THEME["graph_bg"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            height=150,
            cursor="hand2",
        )
        self.top_subjects_canvas.pack(fill="x")
        self.top_subjects_canvas.bind("<Leave>", self.clear_top_subject_hover)
        self.top_subjects_canvas.bind("<Configure>", self._on_top_subjects_resize)

    def build_goal_and_timer_panel(self, parent):
        goal_frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=18)
        goal_frame.grid(row=0, column=0, sticky="ew")

        tk.Label(
            goal_frame,
            text="Consistency System",
            font=("Georgia", 16, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w")
        tk.Label(
            goal_frame,
            text="Set a realistic daily target to avoid burnout and last-minute panic.",
            bg=THEME["card"],
            fg=THEME["slate"],
            wraplength=260,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))

        self.goal_entry = tk.Entry(goal_frame, font=("Segoe UI", 11), width=10)
        self.style_entry(self.goal_entry)
        self.goal_entry.pack(anchor="w", pady=(0, 8), ipady=3)
        self.create_button(goal_frame, "Update Goal", self.save_daily_goal, kind="secondary").pack(anchor="w")

        self.goal_progress = ttk.Progressbar(
            goal_frame,
            length=250,
            mode="determinate",
            maximum=100,
            style="Goal.Horizontal.TProgressbar",
        )
        self.goal_progress.pack(fill="x", pady=(14, 6))
        tk.Label(
            goal_frame,
            textvariable=self.goal_progress_var,
            bg=THEME["card"],
            fg=THEME["navy"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        timer_frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=18)
        timer_frame.grid(row=1, column=0, sticky="ew", pady=(14, 0))

        tk.Label(
            timer_frame,
            text="Focus Sprint",
            font=("Georgia", 16, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w")
        tk.Label(
            timer_frame,
            textvariable=self.timer_label_var,
            font=("Georgia", 26, "bold"),
            bg=THEME["card"],
            fg=THEME["accent_dark"],
        ).pack(anchor="w", pady=(10, 4))
        tk.Label(
            timer_frame,
            textvariable=self.timer_status_var,
            bg=THEME["card"],
            fg=THEME["slate"],
            wraplength=260,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        timer_buttons = tk.Frame(timer_frame, bg=THEME["card"])
        timer_buttons.pack(anchor="w")
        self.create_button(
            timer_buttons,
            "25 min Focus",
            lambda: self.start_timer("focus", 25 * 60),
            kind="primary",
        ).pack(side="left")
        self.create_button(
            timer_buttons,
            "5 min Break",
            lambda: self.start_timer("break", 5 * 60),
            kind="secondary",
        ).pack(side="left", padx=(8, 0))

        secondary_timer_buttons = tk.Frame(timer_frame, bg=THEME["card"])
        secondary_timer_buttons.pack(anchor="w", pady=(10, 0))
        self.create_button(
            secondary_timer_buttons,
            "Pause / Resume",
            self.toggle_timer_pause,
            kind="ghost",
        ).pack(side="left")
        self.create_button(
            secondary_timer_buttons,
            "Reset",
            self.reset_timer_ui,
            kind="ghost",
        ).pack(side="left", padx=(8, 0))

    def build_wellness_panel(self, parent):
        panel = self.create_card(parent, bg=THEME["card"], padx=20, pady=16)
        panel.grid(row=1, column=0, sticky="ew", pady=(14, 0))

        wrap_targets = []

        tk.Label(
            panel,
            text="Wellness Coach",
            font=("Georgia", 18, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w")
        subtitle = tk.Label(
            panel,
            text="Designed for distraction, doomscrolling, and burnout recovery.",
            bg=THEME["card"],
            fg=THEME["slate"],
            justify="left",
            wraplength=380,
        )
        subtitle.pack(anchor="w", fill="x", pady=(4, 10))
        wrap_targets.append(subtitle)

        headline = tk.Label(
            panel,
            textvariable=self.wellness_headline_var,
            font=("Segoe UI Semibold", 13),
            bg=THEME["card"],
            fg=THEME["navy"],
            justify="left",
            wraplength=380,
            anchor="w",
        )
        headline.pack(anchor="w", fill="x")
        wrap_targets.append(headline)

        message = tk.Label(
            panel,
            textvariable=self.wellness_message_var,
            bg=THEME["card"],
            fg=THEME["slate"],
            wraplength=380,
            justify="left",
            font=("Segoe UI", 10),
            anchor="w",
        )
        message.pack(anchor="w", fill="x", pady=(6, 6))
        wrap_targets.append(message)

        action = tk.Label(
            panel,
            textvariable=self.wellness_action_var,
            bg=THEME["card_alt"],
            fg=THEME["navy"],
            padx=10,
            pady=8,
            justify="left",
            wraplength=380,
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )
        action.pack(fill="x")
        wrap_targets.append(action)

        tk.Label(
            panel,
            text="AI Insights",
            font=("Segoe UI Semibold", 12),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(14, 4))
        ai_insight = tk.Label(
            panel,
            textvariable=self.ai_insight_var,
            bg=THEME["card"],
            fg=THEME["mint"],
            wraplength=380,
            justify="left",
            font=("Segoe UI", 10),
            anchor="w",
        )
        ai_insight.pack(anchor="w", fill="x")
        wrap_targets.append(ai_insight)

        tk.Label(
            panel,
            text="Badge Shelf",
            font=("Segoe UI Semibold", 12),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(14, 4))
        badges = tk.Label(
            panel,
            textvariable=self.badge_var,
            bg=THEME["card"],
            fg=THEME["slate"],
            wraplength=380,
            justify="left",
            font=("Segoe UI", 10),
            anchor="w",
        )
        badges.pack(anchor="w", fill="x")
        wrap_targets.append(badges)

        def _resize_wrap(event):
            if event.width <= 1:
                return
            new_wrap = max(event.width - 50, 220)
            for label in wrap_targets:
                label.config(wraplength=new_wrap)

        panel.bind("<Configure>", _resize_wrap)

    def build_history_panel(self, parent):
        history_frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=16)
        history_frame.grid(row=2, column=0, sticky="nsew", pady=(14, 0))

        inner = tk.Frame(history_frame, bg=THEME["card"])
        inner.pack(fill="both", expand=True)

        tk.Label(
            inner,
            text="Recent Sessions",
            font=("Georgia", 18, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(0, 10))

        columns = ("date", "subject", "hours", "mood", "notes")
        self.session_table = ttk.Treeview(inner, columns=columns, show="headings", height=6, style="App.Treeview")
        self.session_table.heading("date", text="Date")
        self.session_table.heading("subject", text="Subject")
        self.session_table.heading("hours", text="Hours")
        self.session_table.heading("mood", text="Mood")
        self.session_table.heading("notes", text="Notes")
        self.session_table.column("date", width=90, anchor="center")
        self.session_table.column("subject", width=140)
        self.session_table.column("hours", width=80, anchor="center")
        self.session_table.column("mood", width=110, anchor="center")
        self.session_table.column("notes", width=240)
        self.session_table.pack(fill="both", expand=True)

    def build_analytics_tab(self, parent):
        outer = tk.Frame(parent, bg=THEME["bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer,
            bg=THEME["bg"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        self.analytics_scroll_canvas = canvas

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        container = tk.Frame(canvas, bg=THEME["bg"])
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def _sync_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _fit_inner_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        container.bind("<Configure>", _sync_scroll_region)
        canvas.bind("<Configure>", _fit_inner_width)

        intro = self.create_card(container, bg=THEME["navy"], padx=20, pady=18)
        intro.pack(fill="x")
        tk.Label(
            intro,
            text="Analytics",
            font=("Georgia", 20, "bold"),
            bg=THEME["navy"],
            fg="#fff5e8",
        ).pack(anchor="w")
        tk.Label(
            intro,
            text="This page is dedicated to your graphs, so they are large and easy to read.",
            bg=THEME["navy"],
            fg="#d5e1ec",
        ).pack(anchor="w", pady=(4, 0))

        self.build_graph_panel(container)
        self.build_subject_graph_panel(container)

        for widget in (canvas, container, intro, self.progress_canvas, self.subject_canvas):
            if widget is not None:
                self.register_analytics_scroll_target(widget)

    def build_graph_panel(self, parent):
        graph_frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=20)
        graph_frame.pack(fill="x", pady=(14, 0))
        graph_frame.configure(height=430)
        graph_frame.pack_propagate(False)

        tk.Label(
            graph_frame,
            text="7-Day Progress Graph",
            font=("Georgia", 18, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(0, 6))
        tk.Label(
            graph_frame,
            text="Daily study hours for the last 7 days. Missed days stay visible so inconsistency stands out.",
            bg=THEME["card"],
            fg=THEME["slate"],
        ).pack(anchor="w", pady=(0, 10))

        self.progress_canvas = tk.Canvas(
            graph_frame,
            bg=THEME["graph_bg"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            height=320,
        )
        self.progress_canvas.pack(fill="both", expand=True)
        self.progress_canvas.bind("<Configure>", self._on_progress_resize)

    def build_subject_graph_panel(self, parent):
        frame = self.create_card(parent, bg=THEME["card"], padx=20, pady=20)
        frame.pack(fill="x", pady=(14, 0))
        frame.configure(height=330)
        frame.pack_propagate(False)

        tk.Label(
            frame,
            text="Subject Focus Graph",
            font=("Georgia", 18, "bold"),
            bg=THEME["card"],
            fg=THEME["navy"],
        ).pack(anchor="w", pady=(0, 6))
        tk.Label(
            frame,
            text="Compare where your study time is actually going.",
            bg=THEME["card"],
            fg=THEME["slate"],
        ).pack(anchor="w", pady=(0, 10))

        self.subject_canvas = tk.Canvas(
            frame,
            bg=THEME["graph_bg"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            height=260,
        )
        self.subject_canvas.pack(fill="both", expand=True)
        self.subject_canvas.bind("<Configure>", self._on_subject_resize)

    def _build_stat_card(self, parent, title, initial_value):
        card = self.create_card(parent, bg=THEME["soft"], padx=14, pady=12)
        card.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(card, text=title, bg=THEME["soft"], fg=THEME["slate"], font=("Segoe UI", 10)).pack(anchor="w")
        value_label = tk.Label(
            card,
            text=initial_value,
            bg=THEME["soft"],
            fg=THEME["navy"],
            font=("Georgia", 16, "bold"),
        )
        value_label.pack(anchor="w", pady=(6, 0))
        return value_label

    def open_date_picker(self):
        initial_date = None
        if self.date_var.get().strip():
            try:
                year, month, day = [int(part) for part in self.date_var.get().split("-")]
                initial_date = dt_date(year, month, day)
            except ValueError:
                initial_date = dt_date.today()
        CalendarPopup(self.root, self.set_selected_date, initial_date)

    def set_selected_date(self, value):
        self.date_var.set(value)

    def clear_selected_date(self):
        self.date_var.set("")

    def maybe_show_streak_popup(self):
        try:
            streak_status = get_streak_status(self.user["id"])
        except mysql.connector.Error:
            return

        if not streak_status["should_popup"] or not streak_status["latest_streak_date"]:
            return

        try:
            mark_streak_popup_shown(self.user["id"], streak_status["latest_streak_date"])
        except mysql.connector.Error:
            return

        StreakPopup(self.root, streak_status["streak_days"], streak_status["new_badges"])

    def maybe_show_goal_popup(self):
        try:
            goal_status = get_goal_status(self.user["id"])
        except mysql.connector.Error:
            return

        if not goal_status["should_popup"] or not goal_status["reached"]:
            return

        try:
            mark_goal_popup_shown(self.user["id"], goal_status["popup_date"])
        except mysql.connector.Error:
            return

        GoalCelebrationPopup(self.root, goal_status["today_hours"], goal_status["goal_hours"])

    def save_daily_goal(self):
        try:
            goal_hours = float(self.goal_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Goal", "Enter daily goal hours like 2 or 3.5.")
            return

        try:
            update_daily_goal(self.user["id"], goal_hours)
        except ValueError as exc:
            messagebox.showerror("Invalid Goal", str(exc))
            return
        except mysql.connector.Error as exc:
            messagebox.showerror("Database Error", exc.msg)
            return

        self.refresh_dashboard()
        self.root.after(180, self.maybe_show_goal_popup)
        messagebox.showinfo("Goal Updated", f"Daily goal set to {goal_hours:.2f} hours.")

    def start_timer(self, mode, seconds):
        if self.timer_after_id:
            self.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None

        self.timer_mode = mode
        self.remaining_seconds = seconds
        self.timer_running = True
        if mode == "focus":
            self.timer_status_var.set("Focus sprint active. Keep your phone away and finish one task.")
        else:
            self.timer_status_var.set("Break mode active. Stand up, breathe, and reset your brain.")
        self._update_timer_label()
        self._run_timer_tick()

    def toggle_timer_pause(self):
        if self.remaining_seconds <= 0:
            self.reset_timer_ui()
            return

        self.timer_running = not self.timer_running
        if self.timer_running:
            self.timer_status_var.set("Timer resumed.")
            self._run_timer_tick()
        else:
            if self.timer_after_id:
                self.root.after_cancel(self.timer_after_id)
                self.timer_after_id = None
            self.timer_status_var.set("Timer paused. Resume when you are ready.")

    def reset_timer_ui(self):
        if self.timer_after_id:
            self.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None
        self.timer_running = False
        self.timer_mode = "focus"
        self.remaining_seconds = 25 * 60
        self.timer_status_var.set("Ready for a focus sprint")
        self._update_timer_label()

    def _run_timer_tick(self):
        if not self.timer_running:
            return
        if self.remaining_seconds <= 0:
            self.timer_running = False
            self.timer_after_id = None
            if self.timer_mode == "focus":
                self.timer_status_var.set("Focus sprint complete. Log the session or take a short break.")
            else:
                self.timer_status_var.set("Break complete. Time to return to one clear task.")
            self.root.bell()
            return

        self.remaining_seconds -= 1
        self._update_timer_label()
        self.timer_after_id = self.root.after(1000, self._run_timer_tick)

    def _update_timer_label(self):
        minutes, seconds = divmod(max(self.remaining_seconds, 0), 60)
        self.timer_label_var.set(f"{minutes:02d}:{seconds:02d}")

    def register_analytics_scroll_target(self, widget):
        widget.bind("<Enter>", self.bind_analytics_mousewheel, add="+")
        widget.bind("<Leave>", self.unbind_analytics_mousewheel, add="+")

    def bind_analytics_mousewheel(self, _event=None):
        if self.analytics_scroll_canvas is None:
            return
        self.root.bind_all("<MouseWheel>", self.on_analytics_mousewheel)
        self.root.bind_all("<Button-4>", self.on_analytics_mousewheel)
        self.root.bind_all("<Button-5>", self.on_analytics_mousewheel)

    def widget_is_in_analytics(self, widget):
        while widget is not None:
            if widget == self.analytics_scroll_canvas:
                return True
            widget = getattr(widget, "master", None)
        return False

    def unbind_analytics_mousewheel(self, _event=None):
        current_widget = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
        if current_widget is not None and self.widget_is_in_analytics(current_widget):
            return
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def on_analytics_mousewheel(self, event):
        if self.analytics_scroll_canvas is None:
            return

        if getattr(event, "delta", 0):
            scroll_units = -int(event.delta / 120)
            if scroll_units == 0:
                scroll_units = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            scroll_units = -1
        else:
            scroll_units = 1

        self.analytics_scroll_canvas.yview_scroll(scroll_units, "units")

    def _on_top_subjects_resize(self, _event=None):
        self.draw_top_subjects_chart(self._cached_top_subjects, self.top_subject_hover_index)

    def _on_progress_resize(self, _event=None):
        self.draw_progress_graph(self._cached_progress)

    def _on_subject_resize(self, _event=None):
        self.draw_subject_graph(self._cached_subject_breakdown)

    def draw_progress_graph(self, progress_rows):
        if self.progress_canvas is None:
            return

        canvas = self.progress_canvas
        canvas.update_idletasks()
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        left_pad = 50
        right_pad = 20
        top_pad = 30
        bottom_pad = 45

        plot_width = width - left_pad - right_pad
        plot_height = height - top_pad - bottom_pad

        canvas.create_line(left_pad, top_pad, left_pad, top_pad + plot_height, fill=THEME["line"], width=2)
        canvas.create_line(
            left_pad,
            top_pad + plot_height,
            left_pad + plot_width,
            top_pad + plot_height,
            fill=THEME["line"],
            width=2,
        )

        if not progress_rows:
            canvas.create_text(
                width // 2,
                height // 2,
                text="No study data yet.",
                fill=THEME["slate"],
                font=("Segoe UI", 13),
                width=max(width - 40, 200),
                justify="center",
            )
            return

        max_hours = max(float(row["total_hours"] or 0) for row in progress_rows)
        max_hours = max(max_hours, 1.0)
        bar_count = len(progress_rows)
        step = plot_width / max(bar_count, 1)
        bar_width = min(42, step * 0.55)

        for level in range(5):
            y = top_pad + (plot_height / 4) * level
            label_value = max_hours - (max_hours / 4) * level
            canvas.create_line(left_pad, y, left_pad + plot_width, y, fill=THEME["soft"])
            canvas.create_text(24, y, text=f"{label_value:.1f}h", fill=THEME["slate"], font=("Segoe UI", 9))

        points = []
        for index, row in enumerate(progress_rows):
            hours = float(row["total_hours"] or 0)
            x_center = left_pad + step * index + step / 2
            bar_height = 0 if max_hours == 0 else (hours / max_hours) * plot_height
            y_top = top_pad + plot_height - bar_height
            x0 = x_center - bar_width / 2
            x1 = x_center + bar_width / 2

            color = THEME["accent"] if hours > 0 else "#ddd3c5"
            canvas.create_rectangle(x0, y_top, x1, top_pad + plot_height, fill=color, outline="")
            canvas.create_text(
                x_center,
                y_top - 10,
                text=f"{hours:.1f}",
                fill=THEME["navy"],
                font=("Segoe UI Semibold", 9),
            )

            date_label = row["session_date"].strftime("%d %b")
            canvas.create_text(
                x_center,
                top_pad + plot_height + 16,
                text=date_label,
                fill=THEME["slate"],
                font=("Segoe UI", 9),
            )
            points.append((x_center, y_top))

        if len(points) > 1:
            flattened = []
            for point in points:
                flattened.extend(point)
            canvas.create_line(*flattened, fill=THEME["mint"], width=3, smooth=True)
            for x_pos, y_pos in points:
                canvas.create_oval(x_pos - 4, y_pos - 4, x_pos + 4, y_pos + 4, fill=THEME["mint"], outline="")

    def draw_top_subjects_chart(self, breakdown_rows, active_index=None):
        if self.top_subjects_canvas is None:
            return

        canvas = self.top_subjects_canvas
        canvas.update_idletasks()
        canvas.delete("all")

        usable_rows = breakdown_rows[:4]
        self.top_subject_rows = usable_rows
        self.top_subject_hover_index = active_index

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        if not usable_rows:
            canvas.create_text(
                width // 2,
                height // 2,
                text="Your strongest subjects will appear here after a few study logs.",
                fill=THEME["slate"],
                font=("Segoe UI", 11),
                width=max(width - 40, 200),
                justify="center",
            )
            return

        left_pad = 18
        top_pad = 16
        row_gap = 38
        row_height = 26
        right_pad = 120
        max_hours = max(float(row["total_hours"] or 0) for row in usable_rows)
        max_hours = max(max_hours, 1.0)
        total_hours = sum(float(row["total_hours"] or 0) for row in usable_rows)
        bar_space = width - left_pad - right_pad
        colors = ["#d96c3f", "#3f8f7a", "#f0a74f", "#5f7ca8"]

        for index, row in enumerate(usable_rows):
            y0 = top_pad + index * row_gap
            y1 = y0 + row_height
            hours = float(row["total_hours"] or 0)
            percent = 0 if total_hours == 0 else (hours / total_hours) * 100
            bar_width = max(22, (hours / max_hours) * bar_space)
            color = colors[index % len(colors)]
            is_active = index == active_index
            tag = f"top_subject_{index}"

            canvas.create_rectangle(
                left_pad,
                y0,
                left_pad + bar_space,
                y1,
                fill="#f6efe4" if is_active else "#fbf5ec",
                outline=THEME["line"],
                width=1,
                tags=(tag,),
            )
            canvas.create_rectangle(
                left_pad,
                y0,
                left_pad + bar_width,
                y1,
                fill=color,
                outline="",
                tags=(tag,),
            )
            canvas.create_text(
                left_pad + 10,
                y0 + row_height / 2,
                text=row["subject"],
                anchor="w",
                fill="#fff8ef" if bar_width > 120 else THEME["navy"],
                font=("Segoe UI Semibold", 10),
                tags=(tag,),
            )
            canvas.create_text(
                width - 18,
                y0 + row_height / 2,
                text=f"{hours:.2f} h  |  {percent:.0f}%",
                anchor="e",
                fill=THEME["navy"] if is_active else THEME["slate"],
                font=("Segoe UI", 10),
                tags=(tag,),
            )

            badge_text = "Leader" if index == 0 else f"#{index + 1}"
            canvas.create_text(
                left_pad + bar_space + 14,
                y0 + row_height / 2,
                text=badge_text,
                anchor="w",
                fill=THEME["accent_dark"] if index == 0 else THEME["slate"],
                font=("Segoe UI Semibold", 9),
                tags=(tag,),
            )

            canvas.tag_bind(tag, "<Enter>", lambda _event, idx=index: self.on_top_subject_hover(idx))
            canvas.tag_bind(tag, "<Button-1>", lambda _event, idx=index: self.on_top_subject_hover(idx))

    def on_top_subject_hover(self, index):
        if not self.top_subject_rows or index >= len(self.top_subject_rows):
            return
        self.draw_top_subjects_chart(self.top_subject_rows, active_index=index)
        row = self.top_subject_rows[index]
        total_hours = sum(float(item["total_hours"] or 0) for item in self.top_subject_rows)
        share = 0 if total_hours == 0 else (float(row["total_hours"] or 0) / total_hours) * 100
        self.hero_status_var.set(
            f"Top subject spotlight: {row['subject']} | {float(row['total_hours']):.2f}h | {share:.0f}% of tracked top-subject time"
        )

    def clear_top_subject_hover(self, _event=None):
        if self.top_subject_hover_index is None or not self.top_subject_rows:
            return
        self.draw_top_subjects_chart(self.top_subject_rows, active_index=None)
        self.top_subject_hover_index = None
        self.hero_status_var.set(self.hero_default_text)

    def draw_subject_graph(self, breakdown_rows):
        if self.subject_canvas is None:
            return

        canvas = self.subject_canvas
        canvas.update_idletasks()
        canvas.delete("all")

        width = canvas.winfo_width()
        if width <= 1:
            return
        left_pad = 140
        right_pad = 30
        top_pad = 30
        row_height = 42
        usable_rows = breakdown_rows[:6]

        if not usable_rows:
            canvas.create_text(
                width // 2,
                120,
                text="Log a few sessions to see subject analytics.",
                fill=THEME["slate"],
                font=("Segoe UI", 13),
                width=max(width - 40, 200),
                justify="center",
            )
            return

        max_hours = max(float(row["total_hours"] or 0) for row in usable_rows)
        max_hours = max(max_hours, 1.0)
        bar_area = width - left_pad - right_pad
        colors = ["#d96c3f", "#3f8f7a", "#f0a74f", "#8c5e58", "#5f7ca8", "#6e7d51"]

        for index, row in enumerate(usable_rows):
            y = top_pad + index * row_height
            hours = float(row["total_hours"] or 0)
            bar_width = (hours / max_hours) * bar_area
            color = colors[index % len(colors)]

            canvas.create_text(
                left_pad - 12,
                y + 12,
                text=row["subject"],
                anchor="e",
                fill=THEME["navy"],
                font=("Segoe UI Semibold", 10),
            )
            canvas.create_rectangle(left_pad, y, left_pad + bar_width, y + 24, fill=color, outline="")
            canvas.create_text(
                left_pad + bar_width + 8,
                y + 12,
                text=f"{hours:.2f} h",
                anchor="w",
                fill=THEME["slate"],
                font=("Segoe UI", 10),
            )

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        try:
            user = login_user(username, password)
        except mysql.connector.Error as exc:
            messagebox.showerror("Database Error", exc.msg)
            return

        if not user:
            messagebox.showerror("Login Failed", "Invalid username or password.")
            return

        self.user = user
        self.build_dashboard_ui()

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        try:
            success, message = register_user(username, password)
        except mysql.connector.Error as exc:
            messagebox.showerror("Database Error", exc.msg)
            return

        if success:
            user = login_user(username, password)
            if not user:
                messagebox.showinfo("Success", f"{message}\n\nRegistered username: {username.strip()}")
                self.password_entry.delete(0, tk.END)
                return

            self.user = user
            messagebox.showinfo("Success", f"{message}\n\nLogged in as: {self.user['username']}")
            self.build_dashboard_ui()
        else:
            messagebox.showerror("Register Failed", message)

    def save_session(self):
        subject = self.subject_entry.get()
        date_text = self.date_var.get()
        notes = self.notes_text.get("1.0", tk.END)
        mood = self.mood_entry.get()

        try:
            hours = float(self.hours_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Hours", "Enter hours as a number like 1.5.")
            return

        try:
            log_study_session(self.user["id"], subject, hours, mood, date_text, notes)
        except ValueError as exc:
            messagebox.showerror("Validation Error", str(exc))
            return
        except mysql.connector.Error as exc:
            messagebox.showerror("Database Error", exc.msg)
            return

        messagebox.showinfo("Saved", random.choice(TIP_MESSAGES))
        self.subject_entry.delete(0, tk.END)
        self.hours_entry.delete(0, tk.END)
        self.date_var.set("")
        self.mood_entry.set("")
        self.notes_text.delete("1.0", tk.END)
        self.refresh_dashboard()
        self.root.after(180, self.maybe_show_goal_popup)

    def refresh_dashboard(self):
        try:
            summary = get_dashboard_summary(self.user["id"])
            breakdown = get_subject_breakdown(self.user["id"])
            recent_sessions = get_recent_sessions(self.user["id"], limit=12)
            progress_rows = get_daily_progress(self.user["id"])
            preferences = get_user_preferences(self.user["id"])
            streak_days = get_study_streak(self.user["id"])
            badges = get_user_badges(self.user["id"])
        except mysql.connector.Error as exc:
            messagebox.showerror("Database Error", exc.msg)
            return

        insights = build_wellness_insights(recent_sessions, summary, preferences, streak_days)
        sessions = recent_sessions[:10]

        try:
            focus_risk = get_focus_prediction(self.user["id"], preferences["daily_goal_hours"], "Focused")
        except Exception:
            focus_risk = None
        sentiment_pct = int(round(((insights["avg_sentiment"] + 1) / 2) * 100))
        if focus_risk is None:
            self.ai_insight_var.set(
                f"Avg note sentiment: {insights['sentiment_label']} "
                f"(score {insights['avg_sentiment']:+.2f}, mood index {sentiment_pct}/100). "
                "Train the focus-risk model with `python -m ml.train --user-id <id>` "
                "to enable predictions."
            )
        else:
            risk_label = "high" if focus_risk >= 0.6 else ("medium" if focus_risk >= 0.35 else "low")
            self.ai_insight_var.set(
                f"Avg note sentiment: {insights['sentiment_label']} "
                f"(score {insights['avg_sentiment']:+.2f}). "
                f"Predicted low-focus risk for next session: {focus_risk:.0%} ({risk_label})."
            )

        self.summary_labels["today_hours"].config(text=f"{summary['today_hours']:.2f} h")
        self.summary_labels["total_hours"].config(text=f"{summary['total_hours']:.2f} h")
        self.summary_labels["total_sessions"].config(text=str(summary["total_sessions"]))
        last_session = summary["last_session_date"].strftime("%Y-%m-%d") if summary["last_session_date"] else "-"
        self.summary_labels["last_session_date"].config(text=last_session)

        goal_hours = insights["goal_hours"]
        progress_percent = 0 if goal_hours <= 0 else min((summary["today_hours"] / goal_hours) * 100, 100)
        if self.goal_progress is not None:
            self.goal_progress["value"] = progress_percent
        self.goal_progress_var.set(
            f"Today's goal progress: {summary['today_hours']:.2f} / {goal_hours:.2f} h"
        )
        if self.goal_entry is not None:
            self.goal_entry.delete(0, tk.END)
            self.goal_entry.insert(0, f"{goal_hours:.2f}")

        self.wellness_headline_var.set(
            f"{insights['headline']}  Focus Score: {insights['focus_score']}/100 | Streak: {insights['streak_days']} day(s)"
        )
        self.wellness_message_var.set(insights["message"])
        self.wellness_action_var.set(f"Recommended action: {insights['action']}")
        self.hero_default_text = (
            f"Today: {summary['today_hours']:.2f}h | Weekly: {summary['weekly_hours']:.2f}h | "
            f"Goal: {goal_hours:.2f}h | Focus Score: {insights['focus_score']}/100"
        )
        self.hero_status_var.set(self.hero_default_text)
        if badges:
            self.badge_var.set(" | ".join(badge["badge_name"] for badge in badges[:4]))
        else:
            self.badge_var.set("No badges unlocked yet. Reach a 7-day streak for your first one.")

        if breakdown:
            top_lines = [f"{row['subject']}: {float(row['total_hours']):.2f} h" for row in breakdown[:5]]
            self.breakdown_var.set("\n".join(top_lines))
        else:
            self.breakdown_var.set("No sessions logged yet.")

        self._cached_top_subjects = breakdown
        self._cached_progress = progress_rows
        self._cached_subject_breakdown = breakdown
        self.draw_top_subjects_chart(breakdown)
        self.draw_progress_graph(progress_rows)
        self.draw_subject_graph(breakdown)

        for item in self.session_table.get_children():
            self.session_table.delete(item)
        for row in sessions:
            self.session_table.insert(
                "",
                "end",
                values=(
                    row["session_date"].strftime("%Y-%m-%d"),
                    row["subject"],
                    f"{float(row['hours']):.2f}",
                    row["mood"],
                    row["notes"],
                ),
            )


def main():
    try:
        initialize_database()
    except mysql.connector.Error as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database Setup Error",
            f"Could not initialize the database.\n\n{exc.msg}",
        )
        root.destroy()
        return

    root = tk.Tk()
    print("Smart Study Tracker is starting. Check the desktop or taskbar for the window.")
    StudyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
