import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import json

stop_download = False
FILE_CONFIG = "ytdl_config_pro.json"

# --- Configurazione Font Professionali ---
FONT_NORMALE = ("Segoe UI", 11)
FONT_PICCOLO = ("Segoe UI", 9)

# --- Funzioni di Memoria Configurazione ---
def carica_percorso():
    if os.path.exists(FILE_CONFIG):
        try:
            with open(FILE_CONFIG, "r") as f:
                dati = json.load(f)
                return dati.get("cartella_destinazione", os.getcwd())
        except Exception:
            pass
    return os.getcwd()

def salva_percorso(percorso):
    try:
        with open(FILE_CONFIG, "w") as f:
            json.dump({"cartella_destinazione": percorso}, f)
    except Exception:
        pass

# --- Funzioni della GUI ---
def incolla_url():
    try:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, root.clipboard_get())
    except tk.TclError:
        pass

def mostra_menu_tasto_destro(event):
    try:
        menu_contestuale.tk_popup(event.x_root, event.y_root)
    finally:
        menu_contestuale.grab_release()

def seleziona_cartella():
    cartella = filedialog.askdirectory()
    if cartella:
        percorso_var.set(cartella)
        salva_percorso(cartella)

def aggiorna_dropdowns(*args):
    """Abilita o disabilita le opzioni in base al formato scelto (Audio o Video)"""
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

def aggiorna_stato(testo, colore="black"):
    status_label.config(text=testo, foreground=colore)

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

    if d['status'] == 'downloading':
        percentuale = d.get('_percent_str', 'N/A').strip()
        velocita = d.get('_speed_str', 'N/A').strip()
        eta = d.get('_eta_str', 'N/A').strip()
        testo = f"Download: {percentuale} | Vel: {velocita} | ETA: {eta}"
        root.after(0, aggiorna_stato, testo, "#0056b3")
        
    elif d['status'] == 'finished':
        root.after(0, aggiorna_stato, "Post-elaborazione (FFmpeg) in corso...", "#0056b3")
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
    
    # Disabilita controlli durante il download
    btn_scarica.config(state=tk.DISABLED)
    btn_incolla.config(state=tk.DISABLED)
    btn_cartella.config(state=tk.DISABLED)
    btn_annulla.config(state=tk.NORMAL)
    url_entry.config(state=tk.DISABLED)
    
    aggiorna_stato("Inizializzazione motore yt-dlp...", "#0056b3")

    thread = threading.Thread(target=esegui_download, args=(url, formato, qualita_v, qualita_a, destinazione, is_playlist, usa_compatibilita))
    thread.start()

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
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }],
            })
        else:
            altezza_max = qualita_v.split("p")[0]
            if usa_compatibilita:
                formato_str = f'bestvideo[height<={altezza_max}][vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={altezza_max}][ext=mp4]+bestaudio[ext=m4a]/best'
                formato_merge = 'mp4'
            else:
                formato_str = f'bestvideo[height<={altezza_max}]+bestaudio/best'
                formato_merge = 'mkv'

            opzioni_ydl.update({
                'format': formato_str,
                'merge_output_format': formato_merge,
            })

        with yt_dlp.YoutubeDL(opzioni_ydl) as ydl:
            ydl.download([url])

        if not stop_download:
            root.after(0, aggiorna_stato, "Operazione completata con successo.", "green")
            root.after(0, lambda: [url_entry.config(state=tk.NORMAL), url_entry.delete(0, tk.END)])
        
    except Exception as e:
        if stop_download:
            root.after(0, aggiorna_stato, "Download interrotto dall'utente.", "red")
        else:
            root.after(0, aggiorna_stato, "Errore irreversibile durante il download.", "red")
            root.after(0, messagebox.showerror, "Errore", str(e))
            
    finally:
        # Riabilita i controlli
        root.after(0, lambda: url_entry.config(state=tk.NORMAL))
        root.after(0, lambda: btn_scarica.config(state=tk.NORMAL))
        root.after(0, lambda: btn_incolla.config(state=tk.NORMAL))
        root.after(0, lambda: btn_cartella.config(state=tk.NORMAL))
        root.after(0, lambda: btn_annulla.config(state=tk.DISABLED))


# --- INIZIALIZZAZIONE FINESTRA ---
root = tk.Tk()
root.title("YT Downloader Pro - Dashboard")
root.geometry("850x750") 
root.minsize(700, 650)   

percorso_var = tk.StringVar(value=carica_percorso())

# Container principale
main_container = ttk.Frame(root, padding="15")
main_container.pack(expand=True, fill="both")

# ==========================================
# SEZIONE 1: SORGENTE
# ==========================================
frame_sorgente = ttk.LabelFrame(main_container, text=" 1. Sorgente Media ", padding="10")
frame_sorgente.pack(fill="x", pady=(0, 10))

frame_url_inner = ttk.Frame(frame_sorgente)
frame_url_inner.pack(fill="x")

url_entry = ttk.Entry(frame_url_inner, font=FONT_NORMALE) 
url_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 10)) 
btn_incolla = ttk.Button(frame_url_inner, text="Incolla", command=incolla_url)
btn_incolla.pack(side=tk.RIGHT)

menu_contestuale = tk.Menu(root, tearoff=0, font=FONT_NORMALE)
menu_contestuale.add_command(label="Incolla", command=incolla_url)
url_entry.bind("<Button-3>", mostra_menu_tasto_destro)


# ==========================================
# SEZIONE 2: IMPOSTAZIONI
# ==========================================
frame_impostazioni = ttk.LabelFrame(main_container, text=" 2. Impostazioni di Estrazione ", padding="10")
frame_impostazioni.pack(fill="x", pady=(0, 10))

formato_var = tk.StringVar(value="mp4")
formato_var.trace_add("write", aggiorna_dropdowns) 

grid_imp = ttk.Frame(frame_impostazioni)
grid_imp.pack(fill="x")
grid_imp.columnconfigure(1, weight=1)

# RIGA 0: VIDEO
ttk.Radiobutton(grid_imp, text="Video (MP4 / MKV)", variable=formato_var, value="mp4").grid(row=0, column=0, sticky="w", pady=(5, 0))
qualita_video_var = tk.StringVar()
combo_video = ttk.Combobox(grid_imp, textvariable=qualita_video_var, state="readonly", font=FONT_NORMALE)
combo_video['values'] = ("2160p (4K)", "1440p (2K)", "1080p (Full HD)", "720p (HD)", "480p (SD)")
combo_video.current(2) 
combo_video.grid(row=0, column=1, sticky="ew", padx=10, pady=(5, 0))

# RIGA 1: COMPATIBILITA'
compatibilita_var = tk.BooleanVar(value=True)
check_compatibilita = ttk.Checkbutton(grid_imp, text="Forza codec H.264 (Massima compatibilità Windows/TV)", variable=compatibilita_var)
check_compatibilita.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(2, 10))

# RIGA 2: AUDIO
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

lbl_cartella = ttk.Label(frame_dest_inner, textvariable=percorso_var, font=FONT_PICCOLO, background="#e8e8e8", relief="sunken", anchor="w", padding=4)
lbl_cartella.pack(side=tk.LEFT, fill="x", expand=True)


# ==========================================
# SEZIONE 4: AZIONI E STATO
# ==========================================
frame_azioni = ttk.Frame(main_container)
frame_azioni.pack(fill="x", pady=(0, 5))

btn_scarica = tk.Button(frame_azioni, text="AVVIA DOWNLOAD", command=scarica_media, bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), padx=20, pady=5)
btn_scarica.pack(side=tk.LEFT, padx=(0, 10))

btn_annulla = ttk.Button(frame_azioni, text="Interrompi", command=annulla_download, state=tk.DISABLED)
btn_annulla.pack(side=tk.LEFT)

status_label = ttk.Label(frame_azioni, text="Pronto.", font=("Segoe UI", 11, "bold"), foreground="#555555")
status_label.pack(side=tk.RIGHT, pady=5)


# ==========================================
# SEZIONE 5: LOG (In basso)
# ==========================================
frame_log = ttk.LabelFrame(main_container, text=" Registro Sessione ", padding="5")
frame_log.pack(fill="both", expand=True)

scrollbar = ttk.Scrollbar(frame_log)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

lista_scaricati = tk.Listbox(frame_log, yscrollcommand=scrollbar.set, font=FONT_PICCOLO, bg="#1e1e1e", fg="#00ff00", selectbackground="#333333", borderwidth=0, highlightthickness=0)
lista_scaricati.pack(side=tk.LEFT, fill="both", expand=True)
scrollbar.config(command=lista_scaricati.yview)

# Inizializza gli stati
aggiorna_dropdowns()

root.mainloop()