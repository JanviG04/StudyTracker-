# Smart Study Tracker - by Janvi Gaikwad

import tkinter as tk
from tkinter import messagebox, ttk
from tracker_utils import register_user, login_user, log_study_session
import random

class StudyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Study Tracker - by Janvi Gaikwad")
        self.root.configure(bg="#f0f4f8")
        self.user_id = None
        self.build_login_ui()

    def build_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        tk.Label(self.root, text="Login", font=("Helvetica", 18, "bold"), bg="#f0f4f8").pack(pady=10)
        tk.Label(self.root, text="Username", bg="#f0f4f8").pack()
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
        tk.Label(self.root, text="Password", bg="#f0f4f8").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()
        tk.Button(self.root, text="Login", command=self.login).pack(pady=5)
        tk.Button(self.root, text="Register", command=self.register).pack()

    def build_tracker_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        tk.Label(self.root, text="Log Study Session", font=("Helvetica", 16, "bold"), bg="#f0f4f8").pack(pady=10)
        tk.Label(self.root, text="Subject", bg="#f0f4f8").pack()
        self.subject_entry = tk.Entry(self.root)
        self.subject_entry.pack()

        tk.Label(self.root, text="Hours Studied", bg="#f0f4f8").pack()
        self.hours_entry = tk.Entry(self.root)
        self.hours_entry.pack()

        tk.Label(self.root, text="Mood (😊 Happy / 😴 Tired / 😩 Stressed)", bg="#f0f4f8").pack()
        moods = ["😊 Happy", "😴 Tired", "😩 Stressed"]
        self.mood_entry = tk.StringVar()
        ttk.Combobox(self.root, textvariable=self.mood_entry, values=moods).pack()

        tk.Button(self.root, text="Submit", command=self.log_session).pack(pady=5)
        tk.Button(self.root, text="Logout", command=self.build_login_ui).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        uid = login_user(username, password)
        if uid:
            self.user_id = uid
            self.build_tracker_ui()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if register_user(username, password):
            messagebox.showinfo("Success", "Registered Successfully!")
        else:
            messagebox.showerror("Error", "Username already exists")

    def log_session(self):
        subject = self.subject_entry.get()
        try:
            hours = float(self.hours_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid hours")
            return
        mood = self.mood_entry.get()
        if not (subject and mood):
            messagebox.showerror("Error", "All fields are required")
            return
        log_study_session(self.user_id, subject, hours, mood)
        messagebox.showinfo("Logged", "Study session logged successfully!")

        # Show random study tip
        tips = [
            "Take a 5-minute break every 25 minutes! 🧠",
            "Avoid multitasking. Focus on one thing at a time.",
            "Sleep well to remember what you study!",
            "Don’t study harder, study smarter! 🧩"
        ]
        messagebox.showinfo("Productivity Tip", random.choice(tips))

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x400")
    app = StudyApp(root)
    root.mainloop()