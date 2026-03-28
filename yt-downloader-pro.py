import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import json
import sys
import ctypes

stop_download = False
FILE_CONFIG = "ytdl_config_pro.json"

# --- Configurazione Font ---
FONT_TITOLO = ("Segoe UI", 11, "bold")
FONT_NORMALE = ("Segoe UI", 11)
FONT_PICCOLO = ("Segoe UI", 9)

# --- Tavolozza Colori Tema ---
THEMES = {
    "light": {
        "bg": "#f5f5f5",          
        "panel_bg": "#ffffff",    
        "fg": "#000000",          
        "accent": "#0056b3",      
        "btn_bg": "#e0e0e0",      
        "btn_active": "#d0d0d0",  
        "log_bg": "#1e1e1e",      
        "log_fg": "#00ff00",      
        "entry_bg": "#ffffff",    
        "entry_fg": "#000000",
        "folder_bg": "#e8e8e8",   
        "border": "#cccccc"       
    },
    "dark": {
        "bg": "#121212",          
        "panel_bg": "#1e1e1e",    
        "fg": "#ffffff",          
        "accent": "#4da6ff",      
        "btn_bg": "#333333",      
        "btn_active": "#444444",  
        "log_bg": "#000000",      
        "log_fg": "#00ff00",      
        "entry_bg": "#2d2d2d",    
        "entry_fg": "#ffffff",
        "folder_bg": "#2d2d2d",   
        "border": "#444444"       
    }
}

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

def imposta_barra_titolo_scura(window, scura=True):
    if sys.platform != "win32": return
    try:
        window.update() 
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        valore = ctypes.c_int(2 if scura else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(valore), ctypes.sizeof(valore))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(valore), ctypes.sizeof(valore))
    except Exception: pass

def applica_tema(*args):
    is_dark = tema_scuro_var.get()
    modo = "dark" if is_dark else "light"
    t = THEMES[modo]

    imposta_barra_titolo_scura(root, is_dark)

    root.config(bg=t["bg"])
    main_container.config(bg=t["bg"])
    
    root.option_add('*TCombobox*Listbox.background', t["entry_bg"])
    root.option_add('*TCombobox*Listbox.foreground', t["entry_fg"])

    style.configure(".", background=t["panel_bg"], foreground=t["fg"])
    style.configure("TFrame", background=t["panel_bg"])
    style.configure("TLabelframe", background=t["panel_bg"], bordercolor=t["border"])
    style.configure("TLabelframe.Label", background=t["panel_bg"], foreground=t["accent"], font=FONT_TITOLO)
    style.configure("TButton", background=t["btn_bg"], foreground=t["fg"], bordercolor=t["border"], lightcolor=t["btn_bg"], darkcolor=t["btn_bg"])
    style.map("TButton", background=[("active", t["btn_active"]), ("disabled", t["panel_bg"])], foreground=[("disabled", "gray")])
    style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
    style.configure("TCombobox", fieldbackground=t["entry_bg"], foreground=t["entry_fg"], background=t["btn_bg"])
    style.configure("TCheckbutton", background=t["panel_bg"], foreground=t["fg"])
    style.configure("TRadiobutton", background=t["panel_bg"], foreground=t["fg"])
    style.configure("Tema.TCheckbutton", background=t["bg"], foreground=t["fg"])
    check_tema.config(style="Tema.TCheckbutton")

    lbl_cartella.config(bg=t["folder_bg"], fg=t["fg"])
    lista_scaricati.config(bg=t["log_bg"], fg=t["log_fg"], selectbackground="#444")
    menu_contestuale.config(bg=t["entry_bg"], fg=t["entry_fg"])
    status_label.config(bg=t["bg"], fg=t["fg"])
    frame_azioni_bottom.config(bg=t["bg"])

    btn_scarica.config(bg="#4CAF50" if modo=="light" else "#2e7d32", fg="white")

# --- NUOVE FUNZIONI DI ANALISI ---
def avvia_analisi():
    url = url_entry.get().strip()
    if not url: return

    # Disabilita UI durante l'analisi
    btn_analizza.config(state=tk.DISABLED)
    btn_scarica.config(state=tk.DISABLED)
    combo_video.config(state=tk.NORMAL)
    combo_video.set("Ricerca qualità...")
    combo_video.config(state=tk.DISABLED)
    
    aggiorna_stato("Analisi del link in corso...", THEMES["dark" if tema_scuro_var.get() else "light"]["accent"])

    threading.Thread(target=esegui_analisi, args=(url,)).start()

def esegui_analisi(url):
    try:
        opzioni = {
            'quiet': True,
            'no_warnings': True,
            'playlist_items': '1', # Se è una playlist, analizza solo il primo video per essere veloce
        }
        with yt_dlp.YoutubeDL(opzioni) as ydl:
            info = ydl.extract_info(url, download=False)

        # Se il link è una playlist, estrai le info dal primo video disponibile
        video_info = info['entries'][0] if 'entries' in info and info['entries'] else info

        # Estrae le risoluzioni uniche disponibili per il video
        altezze = set()
        for f in video_info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('height'):
                altezze.add(int(f.get('height')))

        altezze_ordinate = sorted(list(altezze), reverse=True)
        nuovi_valori = []
        for h in altezze_ordinate:
            if h >= 2160: nuovi_valori.append(f"{h}p (4K)")
            elif h >= 1440: nuovi_valori.append(f"{h}p (2K)")
            elif h >= 1080: nuovi_valori.append(f"{h}p (Full HD)")
            elif h >= 720: nuovi_valori.append(f"{h}p (HD)")
            else: nuovi_valori.append(f"{h}p (SD)")

        if not nuovi_valori: # CORRETTO QUI: not invece di non
            nuovi_valori = ["Migliore disponibile"]

        root.after(0, lambda: completa_analisi(nuovi_valori, "Analisi completata. Scegli la qualità."))

    except Exception as e:
        valori_fallback = ("1080p (Fallback)", "720p", "480p")
        root.after(0, lambda: completa_analisi(valori_fallback, "Analisi fallita. Usa impostazioni standard.", "orange"))

def completa_analisi(valori, messaggio, colore=None):
    combo_video.config(values=valori)
    combo_video.current(0) # Seleziona automaticamente la più alta trovata!
    aggiorna_dropdowns() # Ripristina lo stato corretto (readonly/disabled)
    
    btn_analizza.config(state=tk.NORMAL)
    btn_scarica.config(state=tk.NORMAL)
    aggiorna_stato(messaggio, colore)


def incolla_url():
    try:
        testo = root.clipboard_get()
        url_entry.delete(0, tk.END)
        url_entry.insert(0, testo)
        avvia_analisi() # Avvia automaticamente l'analisi quando si incolla!
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

# --- Funzioni Download ---
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
    if stop_download: raise Exception("Download annullato dall'utente.")

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
        root.after(0, aggiorna_stato, "Post-elaborazione FFmpeg in corso...", colore_blu)
        root.after(0, aggiungi_a_lista_univoca, titolo_pulito)

def scarica_media():
    global stop_download
    stop_download = False
    url = url_entry.get()
    
    if not url:
        messagebox.showwarning("Attenzione", "Inserisci un URL valido per iniziare.")
        return

    formato = formato_var.get()
    qualita_v = qualita_video_var.get()
    qualita_a = qualita_audio_var.get()
    destinazione = percorso_var.get()
    is_playlist = playlist_var.get()
    usa_compatibilita = compatibilita_var.get()
    
    btn_scarica.config(state=tk.DISABLED)
    btn_analizza.config(state=tk.DISABLED)
    btn_incolla.config(state=tk.DISABLED)
    btn_annulla.config(state=tk.NORMAL)
    url_entry.config(state=tk.DISABLED)
    
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
            
            if altezza_max.isdigit():
                vincolo_altezza = f"[height<={altezza_max}]"
            else:
                vincolo_altezza = "" 

            if usa_compatibilita:
                formato_str = f'bestvideo{vincolo_altezza}[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo{vincolo_altezza}[ext=mp4]+bestaudio[ext=m4a]/best'
                formato_merge = 'mp4'
            else:
                formato_str = f'bestvideo{vincolo_altezza}+bestaudio/best'
                formato_merge = 'mkv'
            
            opzioni_ydl.update({'format': formato_str, 'merge_output_format': formato_merge})

        with yt_dlp.YoutubeDL(opzioni_ydl) as ydl:
            ydl.download([url])

        if not stop_download:
            root.after(0, aggiorna_stato, "Operazione completata con successo.", "#4CAF50")
            root.after(0, lambda: [url_entry.config(state=tk.NORMAL), url_entry.delete(0, tk.END), combo_video.set("In attesa di un link...")])
        
    except Exception as e:
        if stop_download:
            root.after(0, aggiorna_stato, "Download interrotto dall'utente.", "red")
        else:
            root.after(0, aggiorna_stato, "Errore irreversibile.", "red")
            root.after(0, messagebox.showerror, "Errore", str(e))
            
    finally:
        root.after(0, lambda: url_entry.config(state=tk.NORMAL))
        root.after(0, lambda: btn_scarica.config(state=tk.NORMAL))
        root.after(0, lambda: btn_analizza.config(state=tk.NORMAL))
        root.after(0, lambda: btn_incolla.config(state=tk.NORMAL))
        root.after(0, lambda: btn_annulla.config(state=tk.DISABLED))


# --- INIZIALIZZAZIONE FINESTRA ---
root = tk.Tk()
root.title("YT Downloader Pro - Auto Analyze")
root.geometry("850x800") 
root.minsize(750, 700)   

style = ttk.Style()
style.theme_use('clam') 
tema_scuro_var = tk.BooleanVar(value=True) 
percorso_var = tk.StringVar(value=carica_percorso())

main_container = tk.Frame(root)
main_container.pack(expand=True, fill="both", padx=15, pady=15)

# ==========================================
# SEZIONE 1: SORGENTE
# ==========================================
frame_sorgente = ttk.LabelFrame(main_container, text=" 1. Sorgente Media ", padding="10")
frame_sorgente.pack(fill="x", pady=(0, 15))

frame_url_inner = ttk.Frame(frame_sorgente)
frame_url_inner.pack(fill="x")

url_entry = ttk.Entry(frame_url_inner, font=FONT_NORMALE) 
url_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 10)) 
btn_analizza = ttk.Button(frame_url_inner, text="🔍 Analizza Link", command=avvia_analisi)
btn_analizza.pack(side=tk.LEFT, padx=(0, 5))
btn_incolla = ttk.Button(frame_url_inner, text="Incolla", command=incolla_url)
btn_incolla.pack(side=tk.RIGHT)

menu_contestuale = tk.Menu(root, tearoff=0, font=FONT_NORMALE)
menu_contestuale.add_command(label="Incolla", command=incolla_url)
url_entry.bind("<Button-3>", mostra_menu_tasto_destro)


# ==========================================
# SEZIONE 2: IMPOSTAZIONI
# ==========================================
frame_impostazioni = ttk.LabelFrame(main_container, text=" 2. Impostazioni di Estrazione ", padding="10")
frame_impostazioni.pack(fill="x", pady=(0, 15))

formato_var = tk.StringVar(value="mp4")
formato_var.trace_add("write", aggiorna_dropdowns) 

grid_imp = ttk.Frame(frame_impostazioni)
grid_imp.pack(fill="x")
grid_imp.columnconfigure(1, weight=1)

# VIDEO
ttk.Radiobutton(grid_imp, text="Video (MP4 / MKV)", variable=formato_var, value="mp4").grid(row=0, column=0, sticky="w", pady=(5, 0))
qualita_video_var = tk.StringVar()
combo_video = ttk.Combobox(grid_imp, textvariable=qualita_video_var, state="disabled", font=FONT_NORMALE)
combo_video.set("In attesa di un link...") 
combo_video.grid(row=0, column=1, sticky="ew", padx=10, pady=(5, 0))

# COMPATIBILITA'
compatibilita_var = tk.BooleanVar(value=True)
check_compatibilita = ttk.Checkbutton(grid_imp, text="Forza codec H.264 (Massima compatibilità Windows/TV)", variable=compatibilita_var)
check_compatibilita.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(2, 10))

# AUDIO
ttk.Radiobutton(grid_imp, text="Solo Audio (MP3)", variable=formato_var, value="mp3").grid(row=2, column=0, sticky="w", pady=(0, 5))
qualita_audio_var = tk.StringVar()
combo_audio = ttk.Combobox(grid_imp, textvariable=qualita_audio_var, state="disabled", font=FONT_NORMALE)
combo_audio['values'] = ("320 kbps (Alta)", "256 kbps (Buona)", "192 kbps (Standard)", "128 kbps (Bassa)")
combo_audio.current(0) 
combo_audio.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 5))

ttk.Separator(frame_impostazioni, orient="horizontal").pack(fill="x", pady=10)

# PLAYLIST
playlist_var = tk.BooleanVar(value=False)
ttk.Checkbutton(frame_impostazioni, text="Scarica intera playlist se l'URL appartiene a una lista", variable=playlist_var).pack(anchor="w")


# ==========================================
# SEZIONE 3: DESTINAZIONE
# ==========================================
frame_destinazione = ttk.LabelFrame(main_container, text=" 3. Destinazione Output ", padding="10")
frame_destinazione.pack(fill="x", pady=(0, 15))

frame_dest_inner = ttk.Frame(frame_destinazione)
frame_dest_inner.pack(fill="x")

btn_cartella = ttk.Button(frame_dest_inner, text="Sfoglia...", command=seleziona_cartella)
btn_cartella.pack(side=tk.LEFT, padx=(0, 10))

lbl_cartella = tk.Label(frame_dest_inner, textvariable=percorso_var, font=FONT_PICCOLO, relief="sunken", anchor="w")
lbl_cartella.pack(side=tk.LEFT, fill="x", expand=True, ipady=4)


# ==========================================
# SEZIONE 4 E 5: AZIONI E LOG
# ==========================================
frame_bottom = tk.Frame(main_container)
frame_bottom.pack(fill="both", expand=True)

frame_azioni_bottom = tk.Frame(frame_bottom)
frame_azioni_bottom.pack(fill="x", pady=(0, 10))

btn_scarica = tk.Button(frame_azioni_bottom, text="AVVIA DOWNLOAD", command=scarica_media, font=("Segoe UI", 11, "bold"), padx=20, pady=5)
btn_scarica.pack(side=tk.LEFT, padx=(0, 10))

btn_annulla = ttk.Button(frame_azioni_bottom, text="Interrompi", command=annulla_download, state=tk.DISABLED)
btn_annulla.pack(side=tk.LEFT)

status_label = tk.Label(frame_azioni_bottom, text="Pronto.", font=("Segoe UI", 11, "bold"))
status_label.pack(side=tk.LEFT, padx=15)

check_tema = ttk.Checkbutton(frame_azioni_bottom, text="🌙 Tema Scuro", variable=tema_scuro_var, command=applica_tema)
check_tema.pack(side=tk.RIGHT)

# LOG
frame_log = ttk.LabelFrame(frame_bottom, text=" Registro Sessione ", padding="5")
frame_log.pack(fill="both", expand=True)

scrollbar = ttk.Scrollbar(frame_log)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

lista_scaricati = tk.Listbox(frame_log, yscrollcommand=scrollbar.set, font=FONT_PICCOLO, borderwidth=0, highlightthickness=0)
lista_scaricati.pack(side=tk.LEFT, fill="both", expand=True)
scrollbar.config(command=lista_scaricati.yview)

aggiorna_dropdowns()
root.update()
applica_tema()

root.mainloop()