import customtkinter as ctk
import sqlite3
import requests
import threading
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv # <--- Nueva librería

# Cargar variables desde el archivo .env
load_dotenv()
API_KEY_ENV = os.getenv("STEAM_API_KEY", "")
STEAM_ID_ENV = os.getenv("STEAM_ID", "")

# --- CONFIGURACIÓN DE DISEÑO ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLOR_FONDO = "#121212"
COLOR_SIDEBAR = "#1e1e24"
COLOR_ACCENT = "#00f2ff"
COLOR_PLATINO = "#E5E4E2"
COLOR_CARTUCHO = "#252525"

class PlatinumHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Steam Platinum Hunter - Secure Edition")
        self.geometry("1200x800")
        self.configure(fg_color=COLOR_FONDO)
        
        # Variables de control (Cargadas desde .env)
        self.api_key = ctk.StringVar(value=API_KEY_ENV)
        self.steam_id = ctk.StringVar(value=STEAM_ID_ENV)
        self.status_msg = ctk.StringVar(value="Esperando órdenes...")
        
        self.init_db()
        
        # --- UI SETUP ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # BARRA LATERAL
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="🏆 PLATINUM\nCOLLECTION", font=("Arial Black", 26), text_color=COLOR_ACCENT)
        self.logo_label.pack(pady=40)
        
        # Indicador de conexión
        estado_color = "#2ecc71" if API_KEY_ENV else "#e74c3c"
        self.lbl_auth = ctk.CTkLabel(self.sidebar, text="● API KEY CARGADA" if API_KEY_ENV else "● SIN API KEY", text_color=estado_color, font=("Arial", 11, "bold"))
        self.lbl_auth.pack(pady=5)

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#444").pack(fill="x", padx=20, pady=20)

        self.btn_scan = ctk.CTkButton(self.sidebar, text="BUSCAR PLATINOS 🚀", command=self.start_scan_thread, height=60, fg_color=COLOR_ACCENT, text_color="black", hover_color="#00c4cf", font=("Arial", 14, "bold"))
        self.btn_scan.pack(padx=20, pady=20, fill="x")

        self.lbl_status = ctk.CTkLabel(self.sidebar, textvariable=self.status_msg, wraplength=220, text_color="#aaa", font=("Consolas", 12))
        self.lbl_status.pack(padx=20, pady=10)

        # ÁREA PRINCIPAL
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.carousel = ctk.CTkScrollableFrame(self.main_area, orientation="horizontal", height=550, fg_color="#0f0f0f", corner_radius=20)
        self.carousel.pack(fill="both", expand=True)
        
        self.refresh_gallery()

    def init_db(self):
        conn = sqlite3.connect("platinos_pro.db")
        conn.execute('''CREATE TABLE IF NOT EXISTS juegos (appid TEXT PRIMARY KEY, nombre TEXT, img_url TEXT, playtime INTEGER)''')
        conn.close()

    def start_scan_thread(self):
        if not self.api_key.get():
            self.status_msg.set("❌ Error: No hay API Key en el archivo .env")
            return
        threading.Thread(target=self.scan_steam_games, daemon=True).start()

    def scan_steam_games(self):
        key = self.api_key.get()
        steamid = self.steam_id.get()
        self.btn_scan.configure(state="disabled")
        
        try:
            url_games = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={steamid}&format=json&include_appinfo=true"
            games = requests.get(url_games).json()['response']['games']
            
            conn = sqlite3.connect("platinos_pro.db")
            platinums_found = 0

            for i, game in enumerate(games):
                appid = game['appid']
                name = game['name']
                self.status_msg.set(f"Analizando: {name}")

                if game.get('playtime_forever', 0) > 60:
                    try:
                        url_ach = f"http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={appid}&key={key}&steamid={steamid}"
                        ach_res = requests.get(url_ach, timeout=5).json()
                        if ach_res.get('playerstats') and all(a['achieved'] == 1 for a in ach_res['playerstats']['achievements']):
                            img_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/library_600x900.jpg"
                            conn.execute("INSERT OR REPLACE INTO juegos VALUES (?, ?, ?, ?)", (appid, name, img_url, game['playtime_forever']))
                            conn.commit()
                            platinums_found += 1
                    except: continue
            
            conn.close()
            self.status_msg.set(f"✅ Éxito: {platinums_found} nuevos.")
            self.after(0, self.refresh_gallery)
        except Exception as e:
            self.status_msg.set(f"❌ Error: {e}")
        self.btn_scan.configure(state="normal")

    def refresh_gallery(self):
        for w in self.carousel.winfo_children(): w.destroy()
        conn = sqlite3.connect("platinos_pro.db")
        juegos = conn.execute("SELECT nombre, img_url FROM juegos ORDER BY nombre").fetchall()
        conn.close()

        for nombre, img_url in juegos:
            self.create_cartridge(nombre, img_url)

    def create_cartridge(self, nombre, url):
        box = ctk.CTkFrame(self.carousel, width=240, height=420, fg_color=COLOR_PLATINO, corner_radius=12)
        box.pack(side="left", padx=15, pady=20)
        box.pack_propagate(False)
        
        inner = ctk.CTkFrame(box, fg_color=COLOR_CARTUCHO, corner_radius=8)
        inner.pack(fill="both", expand=True, padx=3, pady=3)

        try:
            res = requests.get(url, timeout=3)
            img = Image.open(BytesIO(res.content)).resize((210, 315), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, size=(210, 315))
            ctk.CTkLabel(inner, image=ctk_img, text="").pack(pady=10)
        except:
            ctk.CTkLabel(inner, text="Error Img").pack(pady=50)

        ctk.CTkLabel(inner, text=nombre, font=("Arial", 13, "bold"), wraplength=180).pack(pady=5)

if __name__ == "__main__":
    app = PlatinumHunterApp()
    app.mainloop()