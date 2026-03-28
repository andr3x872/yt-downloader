import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import json
import sys
import ctypes # <- LIBRERIA AGGIUNTA PER PARLARE CON WINDOWS

stop_download = False
FILE_CONFIG = "ytdl_config_pro.json"

# --- Configurazione Font ---
FONT_TITOLO_WIZARD = ("Segoe UI", 16, "bold")
FONT_NORMALE = ("Segoe UI", 11)
FONT_PICCOLO = ("Segoe UI", 9)

# --- Tavolozza Colori Tema ---
THEMES = {
    "light": {
        "bg": "white",
        "fg": "black",
        "nav_bg": "#f5f5f5",
        "btn_bg": "#e0e0e0",
        "btn_active": "#d0d0d0",
        "accent": "#0056b3",
        "inactive_step_bg": "#e0e0e0",
        "inactive_step_fg": "#555555",
        "log_bg": "#1e1e1e",
        "log_fg": "#00ff00",
        "entry_bg": "#ffffff",
        "entry_fg": "black",
        "folder_bg": "#f5f5f5",
        "border": "#cccccc"
    },
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#ffffff",
        "nav_bg": "#2d2d2d",
        "btn_bg": "#444444",
        "btn_active": "#555555",
        "accent": "#4da6ff",
        "inactive_step_bg": "#333333",
        "inactive_step_fg": "#aaaaaa",
        "log_bg": "#000000",
        "log_fg": "#00ff00",
        "entry_bg": "#333333",
        "entry_fg": "#ffffff",
        "folder_bg": "#2d2d2d",
        "border": "#444444"
    }
}

frame_tracciati = []
bordi_tracciati = []
titoli_tracciati = []
testi_tracciati = []

passaggio_corrente = 0
frame_passaggi = []
etichette_tappe = []

def carica_percorso():
    if os.path.exists(FILE_CONFIG):
        try:
            with open(FILE_CONFIG, "r") as f:
                return json.load(f).get("cartella_destinazione", os.getcwd())
        except Exception: pass
    return os.getcwd()

def salva_percorso(percorso):
    try:
        with open(FILE_CONFIG, "w") as f:
            json.dump({"cartella_destinazione": percorso}, f)
    except Exception: pass

# --- TRUCCO PER LA BARRA DEL TITOLO DI WINDOWS ---
def imposta_barra_titolo_scura(window, scura=True):
    """Forza la barra del titolo di Windows 10/11 a diventare scura o chiara."""
    if sys.platform != "win32":
        return # Funziona solo su Windows
    try:
        window.update() # Assicurati che la finestra sia renderizzata
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        valore = ctypes.c_int(2 if scura else 0)
        # 20 è per Windows 11, 19 è per le vecchie build di Windows 10
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(valore), ctypes.sizeof(valore))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(valore), ctypes.sizeof(valore))
    except Exception:
        pass # Ignora gli errori se la versione di Windows è troppo vecchia

def applica_tema(*args):
    is_dark = tema_scuro_var.get()
    modo = "dark" if is_dark else "light"
    t = THEMES[modo]

    # Aggiorna la barra del titolo nativa di Windows!
    imposta_barra_titolo_scura(root, is_dark)

    root.config(bg=t["bg"])
    
    root.option_add('*TCombobox*Listbox.background', t["entry_bg"])
    root.option_add('*TCombobox*Listbox.foreground', t["entry_fg"])

    style.configure(".", background=t["bg"], foreground=t["fg"])
    style.configure("TButton", background=t["btn_bg"], foreground=t["fg"], bordercolor=t["bg"], lightcolor=t["btn_bg"], darkcolor=t["btn_bg"])
    style.map("TButton", background=[("active", t["btn_active"]), ("disabled", t["bg"])], foreground=[("disabled", "gray")])
    style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
    style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"], background=t["btn_bg"])
    style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
    style.configure("TRadiobutton", background=t["bg"], foreground=t["fg"])
    style.configure("Nav.TCheckbutton", background=t["nav_bg"], foreground=t["fg"]) 

    for f in frame_tracciati: f.config(bg=t["bg"])
    for b in bordi_tracciati: b.config(bg=t["border"])
    for l in titoli_tracciati: l.config(bg=t["bg"], fg=t["accent"])
    for l in testi_tracciati: l.config(bg=t["bg"], fg=t["fg"])

    nav_frame.config(bg=t["nav_bg"])
    lbl_cartella.config(bg=t["folder_bg"], fg=t["fg"])
    lbl_log.config(bg=t["bg"], fg=t["fg"])
    lista_scaricati.config(bg=t["log_bg"], fg=t["log_fg"], selectbackground="#444")
    menu_contestuale.config(bg=t["entry_bg"], fg=t["entry_fg"])
    
    btn_scarica.config(bg="#4CAF50" if modo=="light" else "#2e7d32", fg="white")

    aggiorna_wizard()

def incolla_url():
    try:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, root.clipboard_get())
    except tk.TclError: pass

def mostra_menu_tasto_destro(event):
    try: menu_contestuale.tk_popup(event.x_root, event.y_root)
    finally: menu_contestuale.grab_release()

def seleziona_cartella():
    cartella = filedialog.askdirectory()
    if cartella:
        percorso_var.set(cartella)
        salva_percorso(cartella)

def aggiorna_dropdowns(*args):
    if formato_var.get() == "mp4":
        combo_video.config(state="readonly")
        check_compatibilita.config(state="normal")
        combo_audio.config(state="disabled")
    else:
        combo_video.config(state="disabled")
        check_compatibilita.config(state="disabled")
        combo_audio.config(state="readonly")

def aggiorna_wizard():
    t = THEMES["dark" if tema_scuro_var.get() else "light"]
    for i, lbl in enumerate(etichette_tappe):
        if i == passaggio_corrente:
            lbl.config(bg=t["accent"], fg="white")
        else:
            lbl.config(bg=t["inactive_step_bg"], fg=t["inactive_step_fg"])
    for i, frame in enumerate(frame_passaggi):
        if i == passaggio_corrente:
            frame.pack(fill="both", expand=True)
        else:
            frame.pack_forget()
    btn_indietro.config(state=tk.NORMAL if passaggio_corrente > 0 else tk.DISABLED)
    btn_avanti.config(state=tk.NORMAL if passaggio_corrente < len(frame_passaggi) - 1 else tk.DISABLED)

def vai_avanti():
    global passaggio_corrente
    if passaggio_corrente < len(frame_passaggi) - 1:
        if passaggio_corrente == 0 and not url_entry.get().strip():
            messagebox.showwarning("Attenzione", "Inserisci un URL valido per proseguire.")
            return
        passaggio_corrente += 1
        aggiorna_wizard()

def vai_indietro():
    global passaggio_corrente
    if passaggio_corrente > 0:
        passaggio_corrente -= 1
        aggiorna_wizard()

def annulla_download():
    global stop_download
    stop_download = True
    aggiorna_stato("Annullamento in corso...", "orange")
    btn_annulla.config(state=tk.DISABLED)

def aggiorna_stato(testo, colore=None):
    if colore is None:
        colore = THEMES["dark" if tema_scuro_var.get() else "light"]["fg"]
    status_label.config(text=testo, fg=colore)

def aggiungi_a_lista_univoca(titolo):
    elemento_testo = f"✔ {titolo}"
    if elemento_testo not in lista_scaricati.get(0, tk.END):
        lista_scaricati.insert(tk.END, elemento_testo)
        lista_scaricati.yview(tk.END)

def hook_progresso(d):
    global stop_download
    if stop_download:
        raise Exception("Download annullato dall'utente.")
    info = d.get('info_dict', {})
    titolo_pulito = info.get('title', 'Elaborazione in corso')
    colore_blu = THEMES["dark" if tema_scuro_var.get() else "light"]["accent"]
    if d['status'] == 'downloading':
        percentuale = d.get('_percent_str', 'N/A').strip()
        velocita = d.get('_speed_str', 'N/A').strip()
        eta = d.get('_eta_str', 'N/A').strip()
        testo = f"Download: {percentuale} | Vel: {velocita} | ETA: {eta}"
        root.after(0, aggiorna_stato, testo, colore_blu)
    elif d['status'] == 'finished':
        root.after(0, aggiorna_stato, "Post-elaborazione in corso...", colore_blu)
        root.after(0, aggiungi_a_lista_univoca, titolo_pulito)

def scarica_media():
    global stop_download
    stop_download = False
    url = url_entry.get()
    if not url: return
    formato = formato_var.get()
    qualita_v = qualita_video_var.get()
    qualita_a = qualita_audio_var.get()
    destinazione = percorso_var.get()
    is_playlist = playlist_var.get()
    usa_compatibilita = compatibilita_var.get()
    btn_scarica.config(state=tk.DISABLED)
    btn_indietro.config(state=tk.DISABLED)
    btn_annulla.config(state=tk.NORMAL)
    aggiorna_stato("Inizializzazione motore...", THEMES["dark" if tema_scuro_var.get() else "light"]["accent"])
    threading.Thread(target=esegui_download, args=(url, formato, qualita_v, qualita_a, destinazione, is_playlist, usa_compatibilita)).start()

def esegui_download(url, formato, qualita_v, qualita_a, destinazione, is_playlist, usa_compatibilita):
    try:
        percorso_salvataggio = os.path.join(destinazione, '%(playlist_title)s', '%(title)s.%(ext)s') if is_playlist else os.path.join(destinazione, '%(title)s.%(ext)s')
        opzioni_ydl = {
            'outtmpl': percorso_salvataggio,
            'noplaylist': not is_playlist,
            'progress_hooks': [hook_progresso],
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True
        }
        if formato == "mp3":
            bitrate = qualita_a.split(" ")[0]
            opzioni_ydl.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}],
            })
        else:
            altezza_max = qualita_v.split("p")[0]
            if usa_compatibilita:
                formato_str = f'bestvideo[height<={altezza_max}][vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={altezza_max}][ext=mp4]+bestaudio[ext=m4a]/best'
                formato_merge = 'mp4'
            else:
                formato_str = f'bestvideo[height<={altezza_max}]+bestaudio/best'
                formato_merge = 'mkv'
            opzioni_ydl.update({'format': formato_str, 'merge_output_format': formato_merge})
        with yt_dlp.YoutubeDL(opzioni_ydl) as ydl:
            ydl.download([url])
        if not stop_download:
            root.after(0, aggiorna_stato, "Operazione completata con successo.", "#4CAF50")
            root.after(0, lambda: url_entry.delete(0, tk.END))
            root.after(2500, lambda: [globals().update(passaggio_corrente=0), aggiorna_wizard(), aggiorna_stato("Pronto.")])
    except Exception as e:
        if stop_download:
            root.after(0, aggiorna_stato, "Download interrotto dall'utente.", "red")
        else:
            root.after(0, aggiorna_stato, "Errore irreversibile.", "red")
            root.after(0, messagebox.showerror, "Errore", str(e))
    finally:
        root.after(0, lambda: btn_scarica.config(state=tk.NORMAL))
        root.after(0, lambda: btn_indietro.config(state=tk.NORMAL))
        root.after(0, lambda: btn_annulla.config(state=tk.DISABLED))


root = tk.Tk()
root.title("YT Downloader Pro - Wizard Dark/Light")
root.geometry("900x600") 
root.minsize(800, 500)   

style = ttk.Style()
style.theme_use('clam') 
tema_scuro_var = tk.BooleanVar(value=True) 
percorso_var = tk.StringVar(value=carica_percorso())

main_container = tk.Frame(root)
frame_tracciati.append(main_container)
main_container.pack(expand=True, fill="both", padx=10, pady=10)
main_container.columnconfigure(0, weight=6)
main_container.columnconfigure(1, weight=4)
main_container.rowconfigure(0, weight=1)

left_panel = tk.Frame(main_container, bd=1, relief="solid")
frame_tracciati.append(left_panel)
left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

progress_frame = tk.Frame(left_panel)
frame_tracciati.append(progress_frame)
progress_frame.pack(fill="x", pady=10)

nomi_tappe = ["1. Sorgente", "2. Impostazioni", "3. Destinazione", "4. Esecuzione"]
for i, nome in enumerate(nomi_tappe):
    lbl = tk.Label(progress_frame, text=nome, font=FONT_PICCOLO, pady=8)
    lbl.pack(side=tk.LEFT, expand=True, fill="x")
    etichette_tappe.append(lbl)

separatore = tk.Frame(left_panel, height=1)
bordi_tracciati.append(separatore)
separatore.pack(fill="x")

content_frame = tk.Frame(left_panel)
frame_tracciati.append(content_frame)
content_frame.pack(fill="both", expand=True, padx=30, pady=20)

for _ in range(4): 
    f = tk.Frame(content_frame)
    frame_tracciati.append(f)
    frame_passaggi.append(f)

# -- PASSAGGIO 0 --
lbl_t0 = tk.Label(frame_passaggi[0], text="Sorgente Media", font=FONT_TITOLO_WIZARD)
lbl_t0.pack(anchor="w", pady=(10, 20))
titoli_tracciati.append(lbl_t0)
lbl_txt0 = tk.Label(frame_passaggi[0], text="Inserisci l'URL del video o della playlist:", font=FONT_NORMALE)
lbl_txt0.pack(anchor="w")
testi_tracciati.append(lbl_txt0)
url_entry = ttk.Entry(frame_passaggi[0], font=FONT_NORMALE) 
url_entry.pack(fill="x", pady=10) 
ttk.Button(frame_passaggi[0], text="Incolla dagli appunti", command=incolla_url).pack(anchor="w", pady=5)
menu_contestuale = tk.Menu(root, tearoff=0, font=FONT_NORMALE)
menu_contestuale.add_command(label="Incolla", command=incolla_url)
url_entry.bind("<Button-3>", mostra_menu_tasto_destro)

# -- PASSAGGIO 1 --
lbl_t1 = tk.Label(frame_passaggi[1], text="Impostazioni di Estrazione", font=FONT_TITOLO_WIZARD)
lbl_t1.pack(anchor="w", pady=(10, 15))
titoli_tracciati.append(lbl_t1)
formato_var = tk.StringVar(value="mp4")
formato_var.trace_add("write", aggiorna_dropdowns) 
grid_impostazioni = tk.Frame(frame_passaggi[1])
frame_tracciati.append(grid_impostazioni)
grid_impostazioni.pack(fill="x", pady=5)
grid_impostazioni.columnconfigure(1, weight=1)
ttk.Radiobutton(grid_impostazioni, text="Video (MP4 / MKV)", variable=formato_var, value="mp4").grid(row=0, column=0, sticky="w", pady=(10, 0))
qualita_video_var = tk.StringVar()
combo_video = ttk.Combobox(grid_impostazioni, textvariable=qualita_video_var, state="readonly", font=FONT_NORMALE)
combo_video['values'] = ("2160p (4K)", "1440p (2K)", "1080p (Full HD)", "720p (HD)", "480p (SD)")
combo_video.current(2) 
combo_video.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))
compatibilita_var = tk.BooleanVar(value=True)
check_compatibilita = ttk.Checkbutton(grid_impostazioni, text="Forza codec H.264 (Massima compatibilità, MP4)", variable=compatibilita_var)
check_compatibilita.grid(row=1, column=0, columnspan=2, sticky="w", padx=25, pady=(2, 10))
ttk.Radiobutton(grid_impostazioni, text="Solo Audio (MP3)", variable=formato_var, value="mp3").grid(row=2, column=0, sticky="w", pady=10)
qualita_audio_var = tk.StringVar()
combo_audio = ttk.Combobox(grid_impostazioni, textvariable=qualita_audio_var, state="disabled", font=FONT_NORMALE)
combo_audio['values'] = ("320 kbps (Alta)", "256 kbps (Buona)", "192 kbps (Standard)", "128 kbps (Bassa)")
combo_audio.current(0) 
combo_audio.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
sep2 = tk.Frame(frame_passaggi[1], height=1)
bordi_tracciati.append(sep2)
sep2.pack(fill="x", pady=15)
lbl_txt1 = tk.Label(frame_passaggi[1], text="Gestione Playlist:", font=FONT_NORMALE)
lbl_txt1.pack(anchor="w")
testi_tracciati.append(lbl_txt1)
playlist_var = tk.BooleanVar(value=False)
ttk.Checkbutton(frame_passaggi[1], text="Scarica l'intera playlist se l'URL lo consente", variable=playlist_var).pack(anchor="w", pady=5)

# -- PASSAGGIO 2 --
lbl_t2 = tk.Label(frame_passaggi[2], text="Destinazione Output", font=FONT_TITOLO_WIZARD)
lbl_t2.pack(anchor="w", pady=(10, 20))
titoli_tracciati.append(lbl_t2)
lbl_cartella = tk.Label(frame_passaggi[2], textvariable=percorso_var, font=FONT_PICCOLO, relief="sunken", anchor="w")
lbl_cartella.pack(fill="x", ipady=5, pady=10)
ttk.Button(frame_passaggi[2], text="Sfoglia...", command=seleziona_cartella).pack(anchor="w")

# -- PASSAGGIO 3 --
lbl_t3 = tk.Label(frame_passaggi[3], text="Pronto per l'esecuzione", font=FONT_TITOLO_WIZARD)
lbl_t3.pack(anchor="w", pady=(10, 20))
titoli_tracciati.append(lbl_t3)
frame_azioni = tk.Frame(frame_passaggi[3])
frame_tracciati.append(frame_azioni)
frame_azioni.pack(anchor="w", pady=10)
btn_scarica = tk.Button(frame_azioni, text="AVVIA DOWNLOAD", command=scarica_media, font=("Segoe UI", 12, "bold"), padx=20, pady=5)
btn_scarica.pack(side=tk.LEFT, padx=(0,10))
btn_annulla = ttk.Button(frame_azioni, text="Interrompi", command=annulla_download, state=tk.DISABLED)
btn_annulla.pack(side=tk.LEFT)
status_label = tk.Label(frame_passaggi[3], text="In attesa di avvio.", font=FONT_NORMALE)
status_label.pack(anchor="w", pady=20)
testi_tracciati.append(status_label)

# 3. NAVIGAZIONE
nav_frame = tk.Frame(left_panel, bd=1)
nav_frame.pack(fill="x", side=tk.BOTTOM)
btn_indietro = ttk.Button(nav_frame, text="Indietro", command=vai_indietro)
btn_indietro.pack(side=tk.LEFT, padx=15, pady=10)
check_tema = ttk.Checkbutton(nav_frame, text="🌙 Cambia Tema", variable=tema_scuro_var, command=applica_tema, style="Nav.TCheckbutton")
check_tema.pack(side=tk.LEFT, expand=True) 
btn_avanti = ttk.Button(nav_frame, text="Avanti", command=vai_avanti)
btn_avanti.pack(side=tk.RIGHT, padx=15, pady=10)

# COLONNA DESTRA
right_frame = tk.Frame(main_container)
frame_tracciati.append(right_frame)
right_frame.grid(row=0, column=1, sticky="nsew") 
lbl_log = tk.Label(right_frame, text="Registro Sessione", font=("Segoe UI", 12, "bold"))
lbl_log.pack(anchor="w", pady=(0, 5))
scrollbar = ttk.Scrollbar(right_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
lista_scaricati = tk.Listbox(right_frame, yscrollcommand=scrollbar.set, font=FONT_PICCOLO, borderwidth=0, highlightthickness=0)
lista_scaricati.pack(side=tk.LEFT, fill="both", expand=True)
scrollbar.config(command=lista_scaricati.yview)

# Inizializza tutto e applica il tema scuro compreso di barra del titolo!
aggiorna_dropdowns()
# IMPORTANTE: root.update() prima di chiamare il tema la prima volta fa sì che Windows generi l'ID della finestra per catturarne la barra
root.update() 
applica_tema()

root.mainloop()