"""Lost & Found - Tkinter GUI connected to XAMPP MySQL.   Run:  python main.py
Default admin:  admin / Admin@123"""
import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import database as db
import matching
import validators as val

NAVY, SIDEBAR, SIDE_ACTIVE, BLUE = "#243A73", "#A0B3E8", "#7B93DE", "#1D4ED8"
CARD, WHITE, TEXT, MUTED = "#C5D0F2", "#FFFFFF", "#1B2A55", "#6B7280"
FONT = ("Segoe UI", 10)
CHIPS = {"Pending": ("#FBDCC8", "#E8590C"), "Found": ("#D1F0B8", "#3F7A0D"), "Not Found": ("#FFB3B3", "#C00000"),
         "Available": ("#D1F0B8", "#3F7A0D"), "Claim Pending": ("#CFE0FF", "#1D4ED8"), "Claimed": ("#B7E4A1", "#2F5E0A")}
_thumbs = {}


# ------------------------------------------------------------------ helpers
def thumb(path, size=(80, 80)):
    key = (path, size)
    if key not in _thumbs:
        try:
            img = Image.open(path)
            img.thumbnail(size)
        except Exception:  # missing/unreadable photo -> grey placeholder
            img = Image.new("RGB", size, CARD)
        _thumbs[key] = ImageTk.PhotoImage(img)
    return _thumbs[key]


def button(parent, text, cmd, kind="primary", **kw):
    bg, fg = {"primary": (BLUE, "white"), "outline": (WHITE, BLUE), "danger": (WHITE, "#C00000"), "success": ("#3F7A0D", "white")}[kind]
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", bd=0,
                     padx=kw.pop("padx", 16), pady=7, cursor="hand2", font=("Segoe UI", 10, "bold"),
                     highlightthickness=0 if kind == "primary" else 1, highlightbackground=fg, **kw)


def chip(parent, status):
    bg, fg = CHIPS.get(status, ("#EEE", "#333"))
    return tk.Label(parent, text=status, bg=bg, fg=fg, font=("Segoe UI", 9, "bold"), padx=12, pady=3)


def label(parent, text, size=10, bold=False, color=TEXT, **kw):
    return tk.Label(parent, text=text, bg=kw.pop("bg", WHITE), fg=color, font=("Segoe UI", size, "bold" if bold else "normal"), **kw)


def entry(parent, var, width=44, **kw):
    return tk.Entry(parent, textvariable=var, width=width, relief="solid", bd=1, font=FONT, **kw)


def pick_image(title="Choose an image"):
    path = filedialog.askopenfilename(title=title, filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
    if not path:
        return None
    try:
        val.validate_image(path)
    except ValueError as e:
        messagebox.showwarning("Invalid file", str(e))
        return None
    return path


def show_image(parent, path, title="Photo"):
    if not path:
        return messagebox.showinfo("No photo", "No photo was uploaded.")
    win = tk.Toplevel(parent)
    win.title(title)
    tk.Label(win, image=thumb(path, (560, 480))).pack(padx=10, pady=10)


class ScrollFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=WHITE)
        canvas = tk.Canvas(self, bg=WHITE, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=WHITE)
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")


class DateField(tk.Frame):
    """Month / Day / Year dropdowns - a simple date picker (no typing errors)."""
    MONTHS = [calendar.month_name[i] for i in range(1, 13)]

    def __init__(self, parent, initial=None):
        super().__init__(parent, bg=WHITE)
        d = initial or date.today()
        self.m, self.d, self.y = tk.StringVar(value=self.MONTHS[d.month - 1]), tk.StringVar(value=str(d.day)), tk.StringVar(value=str(d.year))
        ttk.Combobox(self, textvariable=self.m, values=self.MONTHS, width=11, state="readonly").pack(side="left", padx=(0, 4))
        ttk.Combobox(self, textvariable=self.d, values=list(range(1, 32)), width=4, state="readonly").pack(side="left", padx=4)
        ttk.Combobox(self, textvariable=self.y, values=list(range(date.today().year, date.today().year - 6, -1)), width=6, state="readonly").pack(side="left", padx=4)

    def get(self):
        try:
            return date(int(self.y.get()), self.MONTHS.index(self.m.get()) + 1, int(self.d.get())).isoformat()
        except ValueError:
            return ""


# ------------------------------------------------------------------ app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lost & Found")
        self.geometry("1040x680")
        self.minsize(920, 620)
        ttk.Style(self).theme_use("clam")
        ttk.Style(self).configure("Treeview", rowheight=30, font=FONT)
        ttk.Style(self).configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.current = None
        self.show(Welcome)

    def show(self, screen, *args):
        if self.current:
            self.current.destroy()
        self.current = screen(self, *args)
        self.current.pack(fill="both", expand=True)

    def report_callback_exception(self, exc, value, tb):  # last-resort error handler
        messagebox.showerror("Unexpected error", f"Something went wrong:\n{value}")

    def login_success(self, user):
        self.show(AdminShell if user["role"] == "admin" else StudentShell, user)

    def logout(self):
        if messagebox.askyesno("Log out", "Are you sure you want to log out?"):
            self.show(AuthScreen, "login")


class Welcome(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#9DB2EA")
        box = tk.Frame(self, bg="#9DB2EA")
        box.place(relx=.5, rely=.4, anchor="center")
        tk.Label(box, text="🎒", bg="#9DB2EA", font=("Segoe UI", 54)).pack()
        tk.Label(box, text="Lost & Found", bg="#9DB2EA", fg="#0B2E78", font=("Segoe UI", 34, "bold")).pack()
        tk.Label(box, text="Report, Find, Reconnect.", bg="#9DB2EA", font=("Segoe UI", 13)).pack(pady=6)
        button(self, "Get Started", lambda: app.show(AuthScreen, "login"), width=30).place(relx=.5, rely=.8, anchor="center")


class AuthScreen(tk.Frame):
    def __init__(self, app, mode):
        super().__init__(app, bg=WHITE)
        self.app, self.mode, self.vars = app, mode, {}
        left = tk.Frame(self, bg=NAVY, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="🎒  Lost & Found", bg=NAVY, fg="white", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=20)
        box = tk.Frame(tk.Frame(self, bg=WHITE), bg=WHITE)
        box.master.pack(side="left", fill="both", expand=True)
        box.place(relx=.5, rely=.5, anchor="center")
        if mode == "login":
            label(box, "Welcome back!", 18, True, BLUE).pack()
            label(box, "Log in to your account", 10, color=MUTED).pack(pady=(0, 14))
            fields = [("username", "Username", ""), ("password", "Password", "•")]
        else:
            label(box, "Create an account", 18, True).pack()
            label(box, "Fill in the details below to get started.", 10, color=MUTED).pack(pady=(0, 10))
            fields = [("name", "Full name", ""), ("sid", "Student ID", ""), ("username", "Username", ""),
                      ("password", "Password (8+ chars, letters & numbers)", "•"), ("confirm", "Confirm Password", "•")]
        for key, text, show in fields:
            self.vars[key] = tk.StringVar()
            label(box, text, 9, color=MUTED).pack(anchor="w")
            entry(box, self.vars[key], 42, show=show).pack(pady=(0, 8), ipady=5)
        button(box, "Log In" if mode == "login" else "Sign Up", self.submit, width=36).pack(pady=14)
        row = tk.Frame(box, bg=WHITE)
        row.pack()
        label(row, "Don't have an account? " if mode == "login" else "Already have an account? ").pack(side="left")
        tk.Button(row, text="Sign Up" if mode == "login" else "Log In", bg=WHITE, fg=BLUE, relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"), command=lambda: app.show(AuthScreen, "register" if mode == "login" else "login")).pack(side="left")
        app.bind("<Return>", lambda e: self.submit())

    def submit(self):
        g = lambda k: self.vars[k].get()
        try:
            if self.mode == "login":
                name, pw = val.validate_login(g("username"), g("password"))
                user = db.authenticate(name, pw)
                if not user:
                    return messagebox.showerror("Login failed", "Incorrect username or password.")
                self.app.unbind("<Return>")
                self.app.login_success(user)
            else:
                data = val.validate_registration(g("name"), g("sid"), g("username"), g("password"), g("confirm"))
                db.register_user(*data)
                messagebox.showinfo("Success", "Account created! You can now log in.")
                self.app.show(AuthScreen, "login")
        except (ValueError, db.DBError) as e:
            messagebox.showwarning("Please check", str(e))


# ------------------------------------------------------------------ dialogs
class MatchesDialog(tk.Toplevel):
    """AI matches. Students can start a claim on an Available found item."""
    def __init__(self, shell, item, matches, admin=False):
        super().__init__(shell)
        self.title("Possible matches")
        self.geometry("620x440")
        label(self, f"Possible matches for “{item['name']}”", 13, True).pack(anchor="w", padx=15, pady=10)
        if not matches:
            label(self, "No similar items found yet. Check back later.", color=MUTED).pack(padx=15)
        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True, padx=10)
        for score, m in matches:
            row = tk.Frame(sf.inner, bg=CARD, padx=8, pady=8)
            row.pack(fill="x", pady=4, padx=4)
            tk.Label(row, image=thumb(m["photo_abs"], (70, 70)), bg=CARD).pack(side="left")
            info = tk.Frame(row, bg=CARD)
            info.pack(side="left", padx=10)
            label(info, f"{m['name']}  ({m['report_no']})", 10, True, bg=CARD).pack(anchor="w")
            label(info, f"{m['category']} | {m['location']} | {m['date']}", 9, bg=CARD).pack(anchor="w")
            if admin:
                label(info, f"Reported by {m['reporter']}  ·  {m['contact']}", 9, color=MUTED, bg=CARD).pack(anchor="w")
            right = tk.Frame(row, bg=CARD)
            right.pack(side="right", padx=8)
            label(right, f"{score:.0%}", 14, True, BLUE, bg=CARD).pack()
            chip(right, m["status"]).pack(pady=2)
            if not admin and item["kind"] == "Lost" and m["status"] == "Available":
                button(right, "Claim", lambda m=m: (self.destroy(), ClaimDialog(shell, item, m)), "success", padx=10).pack()


class ClaimDialog(tk.Toplevel):
    """Verify ownership: upload ID/receipt, then Confirm Claim."""
    def __init__(self, shell, lost, found):
        super().__init__(shell)
        self.shell, self.lost, self.found, self.proof = shell, lost, found, None
        self.title("Verify Ownership")
        self.geometry("470x430")
        self.configure(bg=WHITE)
        top = tk.Frame(self, bg=CARD, padx=10, pady=10)
        top.pack(fill="x", padx=15, pady=15)
        tk.Label(top, image=thumb(found["photo_abs"], (70, 70)), bg=CARD).pack(side="left")
        info = tk.Frame(top, bg=CARD)
        info.pack(side="left", padx=10)
        label(info, found["name"], 12, True, bg=CARD).pack(anchor="w")
        label(info, f"{found['category']}\nReport #{found['report_no']}", 9, bg=CARD, justify="left").pack(anchor="w")
        label(self, "Verify Ownership", 11, True, BLUE).pack(anchor="w", padx=15)
        label(self, "Please provide a valid ID or proof of ownership\n(e.g., receipt, student ID).", 9, color=MUTED, justify="left").pack(anchor="w", padx=15)
        self.drop = tk.Label(self, text="⬆  Upload Photo / Document", bg="#E4E9FA", fg=BLUE, height=7, relief="groove", cursor="hand2",
                             font=("Segoe UI", 10, "bold"))
        self.drop.pack(fill="x", padx=15, pady=12)
        self.drop.bind("<Button-1>", lambda e: self.choose())
        button(self, "Confirm Claim", self.confirm).pack(anchor="e", padx=15)

    def choose(self):
        path = pick_image("Choose proof of ownership")
        if path:
            self.proof = path
            self.drop.configure(image=thumb(path, (200, 110)), text="", height=0)

    def confirm(self):
        if not self.proof:
            return messagebox.showwarning("Proof required", "Please upload your ID or proof of ownership.", parent=self)
        try:
            db.submit_claim(self.found["id"], self.shell.user["user_id"], self.lost["id"], self.proof)
        except db.DBError as e:
            return messagebox.showerror("Claim failed", str(e), parent=self)
        messagebox.showinfo("Claim submitted!", "Your claim was sent. An admin will verify it shortly.\nThank you!", parent=self)
        self.destroy()
        self.shell.go("My Reports")


class DetailDialog(tk.Toplevel):
    """View report status with 'Check for Updates'."""
    MSG = {"Pending": "Your report is being monitored.\nWe'll update the status once it is reviewed.",
           "Not Found": "Your report is being monitored.\nThe item is not found yet. Please check back later.",
           "Found": "Good news! Your item was found.\nUse “Matches / Claim” in My Reports to claim it.",
           "Available": "This found item is verified and waiting for its owner.",
           "Claim Pending": "A claim is waiting for admin verification.",
           "Claimed": "Item Claimed! The item was successfully returned to its owner."}

    def __init__(self, parent, kind, item_id):
        super().__init__(parent)
        self.kind, self.item_id = kind, item_id
        self.title("Report status")
        self.geometry("430x360")
        self.configure(bg=WHITE)
        self.body = tk.Frame(self, bg=WHITE)
        self.body.pack(fill="both", expand=True, padx=15, pady=15)
        self.refresh()

    def refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        try:
            it = db.get_item(self.kind, self.item_id)
        except db.DBError as e:
            return messagebox.showerror("Error", str(e), parent=self)
        row = tk.Frame(self.body, bg=WHITE)
        row.pack(fill="x")
        tk.Label(row, image=thumb(it["photo_abs"], (80, 80)), bg=WHITE).pack(side="left")
        info = tk.Frame(row, bg=WHITE)
        info.pack(side="left", padx=10)
        label(info, it["name"], 13, True).pack(anchor="w")
        label(info, f"Report Number: #{it['report_no']}", 9, color=MUTED).pack(anchor="w")
        chip(info, it["status"]).pack(anchor="w", pady=4)
        label(self.body, f"{it['category']}\n{it['description']}\nLocation: {it['location']}\nDate: {it['date']}", 10, justify="left").pack(anchor="w", pady=10)
        box = tk.Frame(self.body, bg=CARD, padx=10, pady=10)
        box.pack(fill="x")
        label(box, "ⓘ  " + self.MSG.get(it["status"], ""), 10, bg=CARD, justify="left").pack(anchor="w")
        button(self.body, "Check for Updates", self.refresh, "outline").pack(anchor="e", pady=12)


# ------------------------------------------------------------------ shells
class Shell(tk.Frame):
    def __init__(self, app, user, nav):
        super().__init__(app, bg=WHITE)
        self.app, self.user, self.nav, self.buttons = app, user, nav, {}
        header = tk.Frame(self, bg=NAVY, height=50)
        header.pack(fill="x")
        label(header, "🎒  Lost & Found", 13, True, "white", bg=NAVY).pack(side="left", padx=15, pady=10)
        initials = "".join(w[0] for w in user["full_name"].split()[:2]).upper()
        tk.Label(header, text=initials, bg=BLUE, fg="white", font=("Segoe UI", 9, "bold"), width=4).pack(side="right", padx=15)
        label(header, f"{user['full_name']}  ({user['role']})", 9, color="white", bg=NAVY).pack(side="right")
        body = tk.Frame(self, bg=WHITE)
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=SIDEBAR, width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        for name, _ in nav:
            b = tk.Button(side, text="   " + name, anchor="w", relief="flat", bd=0, bg=SIDEBAR, fg="black", cursor="hand2",
                          font=("Segoe UI", 10, "bold"), pady=10, command=lambda n=name: self.go(n))
            b.pack(fill="x", padx=8, pady=(8, 0))
            self.buttons[name] = b
        tk.Button(side, text="   Log Out", anchor="w", relief="flat", bd=0, bg=SIDEBAR, fg="#C00000", cursor="hand2",
                  font=("Segoe UI", 10, "bold"), pady=10, command=app.logout).pack(side="bottom", fill="x", padx=8, pady=12)
        self.content = tk.Frame(body, bg=WHITE)
        self.content.pack(side="left", fill="both", expand=True)
        self.go(nav[0][0])

    def go(self, name):
        for n, b in self.buttons.items():
            b.configure(bg=SIDE_ACTIVE if n == name else SIDEBAR)
        self.clear()
        try:
            dict(self.nav)[name]()
        except db.DBError as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def stat_cards(self, data):
        row = tk.Frame(self.content, bg=WHITE)
        row.pack(anchor="w", padx=25, pady=10)
        for title, value in data:
            c = tk.Frame(row, bg=CARD, padx=18, pady=14)
            c.pack(side="left", padx=8)
            label(c, str(value), 24, True, BLUE, bg=CARD).pack()
            label(c, title, 9, bg=CARD).pack()


class StudentShell(Shell):
    def __init__(self, app, user):
        super().__init__(app, user, [("Home", self.page_home), ("Reports", self.page_report),
                                     ("My Reports", self.page_my_reports), ("Profile", self.page_profile)])

    def page_home(self):
        h = datetime.now().hour
        greet = "Morning" if h < 12 else "Afternoon" if h < 18 else "Evening"
        label(self.content, f"Good {greet}, {self.user['full_name'].split()[0]}!", 16, True, BLUE).pack(anchor="w", padx=25, pady=(20, 0))
        label(self.content, "What would you like to do today?", 10, color=MUTED).pack(anchor="w", padx=25)
        s = db.stats(self.user["user_id"])
        self.stat_cards([("Lost reports", s["lost"]), ("Found reports", s["found"]), ("Pending", s["pending"]), ("Claimed", s["claimed"])])
        row = tk.Frame(self.content, bg=WHITE)
        row.pack(anchor="w", padx=33, pady=15)
        button(row, "Report an Item", lambda: self.go("Reports")).pack(side="left", padx=(0, 10))
        button(row, "View My Reports", lambda: self.go("My Reports"), "outline").pack(side="left")

    # ---- report lost / found item, step 1: details
    def page_report(self, draft=None):
        self.clear()
        d = draft or {"kind": "Lost", "name": "", "category": "", "description": "", "date": date.today().isoformat(),
                      "location": "", "contact": "", "photo": None}
        wrap = tk.Frame(self.content, bg=WHITE)
        wrap.pack(anchor="nw", padx=30, pady=14)
        label(wrap, "Item Details", 15, True).pack(anchor="w")
        kind = tk.StringVar(value=d["kind"])
        row = tk.Frame(wrap, bg=WHITE)
        row.pack(anchor="w", pady=4)
        for k in ("Lost", "Found"):
            tk.Radiobutton(row, text=f"I {k.lower()} an item", variable=kind, value=k, bg=WHITE, font=FONT).pack(side="left", padx=(0, 15))
        v = {k: tk.StringVar(value=d[k]) for k in ("name", "category", "description", "location", "contact")}

        def field(text, key, widget=None):
            label(wrap, text, 9, True).pack(anchor="w", pady=(5, 0))
            (widget or entry(wrap, v[key], 50)).pack(anchor="w", ipady=3)
        field("Item Name *  (e.g. Black backpack)", "name")
        field("Category *", "category", ttk.Combobox(wrap, textvariable=v["category"], values=val.CATEGORIES, state="readonly", width=47))
        field("Color / Brand / Description *  (e.g. Black Nike, torn strap)", "description")
        field("Location *  (e.g. Library, Room 101)", "location")
        label(wrap, "Date *", 9, True).pack(anchor="w", pady=(5, 0))
        dfield = DateField(wrap, date.fromisoformat(d["date"]))
        dfield.pack(anchor="w")
        field("Your contact info *  (email or phone)", "contact")
        photo = {"path": d["photo"]}
        prow = tk.Frame(wrap, bg=WHITE)
        prow.pack(anchor="w", pady=6)
        preview = tk.Label(prow, bg="#E4E9FA", width=10, height=3, text="No photo")
        preview.pack(side="left")
        if photo["path"]:
            preview.configure(image=thumb(photo["path"], (60, 60)), text="", width=60, height=60)

        def choose():
            p = pick_image("Choose item photo")
            if p:
                photo["path"] = p
                preview.configure(image=thumb(p, (60, 60)), text="", width=60, height=60)
        button(prow, "Upload Photo", choose, "outline").pack(side="left", padx=10)

        def nxt():
            try:
                data = val.validate_report(kind.get(), v["name"].get(), v["category"].get(), v["description"].get(),
                                           dfield.get(), v["location"].get(), v["contact"].get(), photo["path"])
            except ValueError as e:
                return messagebox.showwarning("Check your details", str(e))
            self.page_review(data)
        button(wrap, "Next", nxt, width=30).pack(anchor="w", pady=6)

    # ---- step 2: review + submit
    def page_review(self, d):
        self.clear()
        wrap = tk.Frame(self.content, bg=WHITE)
        wrap.pack(anchor="nw", padx=30, pady=20)
        label(wrap, f"Review {d['kind']} Item Report", 15, True).pack(anchor="w")
        card = tk.Frame(wrap, bg=CARD, padx=12, pady=12)
        card.pack(fill="x", pady=12)
        tk.Label(card, image=thumb(d["photo"], (90, 90)), bg=CARD).pack(side="left")
        info = tk.Frame(card, bg=CARD)
        info.pack(side="left", padx=12)
        label(info, d["name"], 13, True, bg=CARD).pack(anchor="w")
        label(info, f"{d['category']}  ·  {d['description']}", 9, bg=CARD).pack(anchor="w")
        label(info, f"📍 {d['location']}\n📅 {d['date']}\n☎ {d['contact']}", 10, bg=CARD, justify="left").pack(anchor="w", pady=4)
        label(wrap, "ⓘ Is this information correct? You can go back to edit if needed.", 10, color=BLUE).pack(anchor="w")
        row = tk.Frame(wrap, bg=WHITE)
        row.pack(anchor="w", pady=15)
        button(row, "Back", lambda: self.page_report(d), "outline").pack(side="left", padx=(0, 10))
        button(row, "Submit", lambda: self.submit(d)).pack(side="left")

    def submit(self, d):
        try:
            item_id = db.create_report(self.user["user_id"], d["kind"], d["name"], d["category"], d["description"],
                                       d["date"], d["location"], d["contact"], d["photo"])
            item = db.get_item(d["kind"], item_id)
            matches = matching.find_matches(item, db.candidates_for(item)) if d["kind"] == "Lost" else []
        except (db.DBError, OSError) as e:
            return messagebox.showerror("Could not submit", str(e))
        messagebox.showinfo("Report submitted", f"Your {d['kind'].lower()} report was submitted.\nReport #: {item['report_no']}")
        self.go("My Reports")
        if matches and matches[0][0] >= 0.5:
            MatchesDialog(self, item, matches)

    # ---- my reports (status + claim)
    def page_my_reports(self, flt="All"):
        self.clear()
        bar = tk.Frame(self.content, bg=WHITE)
        bar.pack(anchor="w", padx=25, pady=12)
        for text, key in [("All", "All"), ("Lost Items", "Lost"), ("Found Items", "Found")]:
            button(bar, text, lambda k=key: self.rerender(k), "primary" if flt == key else "outline").pack(side="left", padx=4)
        items = db.list_items(self.user["user_id"], None if flt == "All" else flt)
        sf = ScrollFrame(self.content)
        sf.pack(fill="both", expand=True, padx=20)
        if not items:
            label(sf.inner, "No reports yet. Use “Reports” to add one.", color=MUTED).pack(pady=30, padx=10)
        for it in items:
            row = tk.Frame(sf.inner, bg=WHITE, pady=8)
            row.pack(fill="x")
            tk.Label(row, image=thumb(it["photo_abs"], (90, 90)), bg=CARD, bd=1, relief="solid").pack(side="left")
            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", padx=12)
            label(info, f"{it['name']}  ·  {it['kind']}", 11, True).pack(anchor="w")
            label(info, f"{it['category']} | {it['date']} | {it['location']}", 9, color=MUTED).pack(anchor="w")
            chip(info, it["status"]).pack(anchor="w", pady=4)
            acts = tk.Frame(row, bg=WHITE)
            acts.pack(side="right", padx=10)
            button(acts, "Details", lambda i=it: DetailDialog(self, i["kind"], i["id"]), "outline").pack(side="left", padx=3)
            if it["kind"] == "Lost" and it["status"] != "Claimed":
                button(acts, "Matches / Claim", lambda i=it: self.show_matches(i), "success" if it["status"] == "Found" else "outline").pack(side="left", padx=3)

    def show_matches(self, item):
        try:
            MatchesDialog(self, item, matching.find_matches(item, db.candidates_for(item)))
        except db.DBError as e:
            messagebox.showerror("Error", str(e))

    def rerender(self, flt):
        self.clear()
        self.page_my_reports(flt)

    def page_profile(self):
        u = self.user
        row = tk.Frame(self.content, bg=WHITE)
        row.pack(anchor="w", padx=30, pady=25)
        tk.Label(row, text="".join(w[0] for w in u["full_name"].split()[:2]).upper(), bg=BLUE, fg="white", width=4, height=2,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        info = tk.Frame(row, bg=WHITE)
        info.pack(side="left", padx=15)
        label(info, u["full_name"], 18, True).pack(anchor="w")
        label(info, f"Student ID: {u['student_id']}   |   @{u['username']}", 10, color=MUTED).pack(anchor="w")
        for text, cmd in [("My Reports", lambda: self.go("My Reports")),
                          ("Help & Support", lambda: messagebox.showinfo("Help", "Visit the Lost & Found office for assistance."))]:
            tk.Button(self.content, text=f"  {text}   ›", anchor="w", relief="solid", bd=1, bg=WHITE, font=FONT, width=45, pady=8,
                      command=cmd).pack(anchor="w", padx=30, pady=4)
        button(self.content, "Log Out", self.app.logout, "danger").pack(anchor="w", padx=30, pady=12)


class AdminShell(Shell):
    def __init__(self, app, user):
        super().__init__(app, user, [("Dashboard", self.page_dash), ("All Reports", self.page_reports), ("Claims", self.page_claims)])

    def page_dash(self):
        label(self.content, "Admin Dashboard", 16, True, BLUE).pack(anchor="w", padx=25, pady=(20, 0))
        s = db.stats()
        self.stat_cards([("Students", s["students"]), ("Lost", s["lost"]), ("Found", s["found"]),
                         ("Pending", s["pending"]), ("Claims to verify", s["claims"]), ("Claimed", s["claimed"])])

    def _tree(self, cols, widths):
        frame = tk.Frame(self.content, bg=WHITE)
        frame.pack(fill="both", expand=True, padx=20, pady=(15, 5))
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=14, selectmode="browse")
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    def _selected(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select a row", "Please select a row first.")
        return sel[0] if sel else None

    # ---- all reports + update status
    def page_reports(self):
        tree = self._tree(("Report No", "Type", "Item", "Category", "Location", "Reporter", "Status"), (110, 55, 140, 100, 120, 120, 100))
        for i in db.list_items():
            tree.insert("", "end", iid=f"{i['kind']}-{i['id']}", values=(i["report_no"], i["kind"], i["name"], i["category"], i["location"], i["reporter"], i["status"]))
        bar = tk.Frame(self.content, bg=WHITE)
        bar.pack(anchor="w", padx=20, pady=8)
        status = tk.StringVar()
        cb = ttk.Combobox(bar, textvariable=status, state="readonly", width=16)
        cb.pack(side="left", padx=(0, 6))

        def on_select(_e=None):
            sel = tree.selection()
            if sel:
                kind = sel[0].split("-")[0]
                cb["values"] = db.LOST_STATUSES if kind == "Lost" else db.FOUND_STATUSES
                status.set(tree.item(sel[0], "values")[6])
        tree.bind("<<TreeviewSelect>>", on_select)

        def current():
            sel = self._selected(tree)
            if sel:
                kind, iid = sel.split("-")
                return db.get_item(kind, int(iid))

        def update():
            it = current()
            if it:
                try:
                    db.set_status(it["kind"], it["id"], status.get())
                except db.DBError as e:
                    return messagebox.showerror("Error", str(e))
                self.go("All Reports")

        def matches():
            it = current()
            if it:
                MatchesDialog(self, it, matching.find_matches(it, db.candidates_for(it)), admin=True)
        button(bar, "Update Status", update).pack(side="left", padx=4)
        button(bar, "View Photo", lambda: (lambda it: it and show_image(self, it["photo_abs"], it["name"]))(current()), "outline").pack(side="left", padx=4)
        button(bar, "AI Matches", matches, "outline").pack(side="left", padx=4)

    # ---- admin verification of claims
    def page_claims(self):
        tree = self._tree(("Claim #", "Found Item", "Claimant", "Student ID", "Date", "Status"), (70, 220, 150, 110, 100, 90))
        claims = db.list_claims()
        for c in claims:
            tree.insert("", "end", iid=str(c["claim_id"]), values=(c["claim_id"], f"{c['report_no']} · {c['item_name']}", c["claimant"], c["student_id"], c["claim_date"], c["status"]))
        bar = tk.Frame(self.content, bg=WHITE)
        bar.pack(anchor="w", padx=20, pady=8)

        def proof():
            sel = self._selected(tree)
            if sel:
                show_image(self, next(c for c in claims if str(c["claim_id"]) == sel)["proof_abs"], "Proof of ownership")

        def decide(approve):
            sel = self._selected(tree)
            if sel and messagebox.askyesno("Confirm", f"{'Verify and approve' if approve else 'Reject'} this claim?"):
                try:
                    db.resolve_claim(int(sel), approve)
                except db.DBError as e:
                    return messagebox.showerror("Error", str(e))
                self.go("Claims")
        button(bar, "View Proof", proof, "outline").pack(side="left", padx=4)
        button(bar, "Verify & Approve", lambda: decide(True), "success").pack(side="left", padx=4)
        button(bar, "Reject", lambda: decide(False), "danger").pack(side="left", padx=4)


def main():
    try:
        db.init_db()
    except db.DBError as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Startup error", str(e))
        return
    App().mainloop()


if __name__ == "__main__":
    main()