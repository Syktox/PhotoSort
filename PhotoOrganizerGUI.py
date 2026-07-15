import hashlib
import os
import shutil
import threading
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

class PhotoOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Organizer")
        self.root.geometry("1000x420")
        self.root.resizable(False, False)
        
        self.source_path = tk.StringVar(value="Quellordner wählen...")
        self.target_path = tk.StringVar(value="Zielordner wählen...")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Erstellt die Benutzeroberfläche"""
        
        # Hauptcontainer
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Obere Reihe - Buttons zum Pfad wählen
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=False, pady=(0, 20))
        
        # Linker Button - Quellordner
        ttk.Button(
            button_frame, 
            text="📁 Quellordner wählen",
            command=self.choose_source,
            width=35
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), ipady=16)
        
        # Rechter Button - Zielordner
        ttk.Button(
            button_frame, 
            text="📁 Zielordner wählen",
            command=self.choose_target,
            width=35
        ).pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0), ipady=16)
        
        # Mittlere Reihe - Pfade anzeigen
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Quellpfad
        ttk.Label(path_frame, text="Quellordner:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.source_label = ttk.Label(
            path_frame, 
            text=self.source_path.get(),
            font=("Arial", 12),
            foreground="gray",
            wraplength=700,
            justify=tk.LEFT
        )
        self.source_label.pack(anchor=tk.W, fill=tk.BOTH, padx=10, pady=(5, 20))
        
        # Zieldpfad
        ttk.Label(path_frame, text="Zielordner:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.target_label = ttk.Label(
            path_frame, 
            text=self.target_path.get(),
            font=("Arial", 12),
            foreground="gray",
            wraplength=700,
            justify=tk.LEFT
        )
        self.target_label.pack(anchor=tk.W, fill=tk.BOTH, padx=10, pady=(5, 20))
        
        # Untere Reihe - Start Button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, expand=False, pady=(20, 0))
        
        self.start_button = ttk.Button(
            bottom_frame,
            text="▶ Organisieren starten",
            command=self.start_organization
        )
        self.start_button.pack(fill=tk.X, expand=True, padx=(0, 10), pady=(0, 8))
        
        self.delete_button = ttk.Button(
            bottom_frame,
            text="🗑️ Duplikate löschen",
            command=self.delete_duplicates
        )
        self.delete_button.pack(fill=tk.X, expand=True, padx=(0, 10))
        
        # Info-Label
        self.info_label = ttk.Label(
            bottom_frame,
            text="Bereit",
            font=("Arial", 10),
            foreground="green"
        )
        self.info_label.pack(side=tk.LEFT, pady=(10, 0))
    
    def choose_source(self):
        """Wählt den Quellordner"""
        folder = filedialog.askdirectory(title="Quellordner mit Fotos wählen")
        if folder:
            self.source_path.set(folder)
            self.source_label.config(text=folder, foreground="black")
    
    def choose_target(self):
        """Wählt den Zielordner"""
        folder = filedialog.askdirectory(title="Zielordner wählen")
        if folder:
            self.target_path.set(folder)
            self.target_label.config(text=folder, foreground="black")
    
    def start_organization(self):
        """Startet die Organisation in einem separaten Thread"""
        source = self.source_path.get()
        target = self.target_path.get()
        
        # Validierung
        if source == "Quellordner wählen..." or target == "Zielordner wählen...":
            messagebox.showwarning("Fehler", "Bitte wähle Quell- und Zielordner!")
            return
        
        if not Path(source).exists():
            messagebox.showerror("Fehler", f"Quellordner existiert nicht:\n{source}")
            return
        
        # Starte Organisation in separatem Thread (verhindert Einfrieren des UI)
        thread = threading.Thread(target=self.organize_with_progress, args=(source, target))
        thread.daemon = True
        thread.start()
    
    def delete_duplicates(self):
        """Löscht doppelte Dateien aus einem ausgewählten Ordner"""
        folder = filedialog.askdirectory(title="Ordner für Duplikate wählen")
        if not folder:
            return
        
        if not Path(folder).exists():
            messagebox.showerror("Fehler", f"Ordner existiert nicht:\n{folder}")
            return
        
        self.start_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        self.info_label.config(text="Duplikate prüfen...", foreground="orange")
        self.root.update()
        
        try:
            result = self.remove_duplicate_files(folder)
            self.info_label.config(
                text=f"✓ {result['deleted']} Duplikate gelöscht",
                foreground="green"
            )
            messagebox.showinfo(
                "Fertig",
                f"Duplikate gelöscht: {result['deleted']}\n"
                f"Behaltene Dateien: {result['kept']}\n"
                f"Gescannt: {result['scanned']}"
            )
        except Exception as e:
            self.info_label.config(text="Fehler!", foreground="red")
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{str(e)}")
        finally:
            self.start_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
    
    def hash_file(self, file_path):
        """Berechnet einen SHA-256 Hash für eine Datei."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def remove_duplicate_files(self, folder):
        """Entfernt doppelte Dateien im Ordner basierend auf ihrem Inhalt."""
        folder_path = Path(folder).expanduser()
        size_groups = {}
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = Path(root) / file
                try:
                    size = file_path.stat().st_size
                except OSError:
                    continue
                size_groups.setdefault(size, []).append(file_path)
        
        hashes = {}
        deleted = 0
        kept = 0
        scanned = 0
        
        for paths in size_groups.values():
            if len(paths) == 1:
                kept += 1
                continue
            for file_path in paths:
                file_hash = self.hash_file(file_path)
                scanned += 1
                if file_hash in hashes:
                    try:
                        file_path.unlink()
                        deleted += 1
                    except OSError:
                        pass
                else:
                    hashes[file_hash] = file_path
                    kept += 1
        
        return {
            'scanned': scanned,
            'deleted': deleted,
            'kept': kept
        }
    
    def organize_with_progress(self, source_dir, target_dir):
        """Organisiert Dateien und zeigt Fortschritt"""
        try:
            self.start_button.config(state=tk.DISABLED)
            self.info_label.config(text="Läuft...", foreground="orange")
            self.root.update()
            
            result = self.organize_photos(source_dir, target_dir)
            
            if result:
                self.info_label.config(
                    text=f"✓ Fertig! {result['organized']}/{result['found']} Dateien organisiert",
                    foreground="green"
                )
                messagebox.showinfo(
                    "Erfolg",
                    f"Verarbeitung abgeschlossen!\n\n"
                    f"Gefundene Dateien: {result['found']}\n"
                    f"Organisiert: {result['organized']}\n\n"
                    f"Zielordner: {target_dir}"
                )
            
        except Exception as e:
            self.info_label.config(text="Fehler!", foreground="red")
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{str(e)}")
        
        finally:
            self.start_button.config(state=tk.NORMAL)
    
    def get_creation_date(self, file_path):
        """
        Extrahiert das Aufnahmedatum aus EXIF-Daten.
        Rückgabe: datetime-Objekt oder None
        """
        try:
            image = Image.open(file_path)
            exif_data = image._getexif()
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ["DateTimeOriginal", "DateTime"]:
                        date_obj = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                        return date_obj
        except Exception:
            pass
        
        return None

    def get_modification_date(self, file_path):
        """
        Liest das Änderungsdatum der Datei.
        Rückgabe: datetime-Objekt oder None
        """
        try:
            timestamp = os.path.getmtime(file_path)
            return datetime.fromtimestamp(timestamp)
        except Exception:
            return None
    
    def organize_photos(self, source_dir, target_dir):
        """
        Organisiert Fotos und Videos nach Erstellungsdatum.
        Format: M-YYYY (z.B. 2-2024 für Februar 2024)
        """
        
        source_path = Path(source_dir).expanduser()
        target_path = Path(target_dir).expanduser()
        
        # Validierung
        if not source_path.exists() or not source_path.is_dir():
            raise Exception(f"Quellordner '{source_dir}' ist ungültig")
        
        # Zielordner erstellen
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Unterstützte Dateitypen
        supported_extensions = {
            # Fotoformate
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff',
            '.heic', '.heif', '.raw', '.arw', '.cr2', '.nef', '.orf', '.sr2',
            '.dng', '.rw2', '.raf', '.pef', '.mos', '.mrw', '.kdc', '.erf',
            '.ai', '.eps', '.psd',
            # Videoformate
            '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.webm',
            '.3gp', '.3g2', '.mts', '.m2ts', '.ts', '.vob', '.rm', '.rmvb',
            '.mpg', '.mpeg', '.mpe', '.mxf', '.asf', '.f4v', '.dv', '.divx',
            '.xvid'
        }
        
        # Durch alle Dateien in Ordnern und Unterordnern gehen
        file_count = 0
        organized_count = 0
        
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()
                
                # Prüfe, ob Dateityp unterstützt ist
                if file_ext not in supported_extensions:
                    rest_folder = target_path / "Rest"
                    rest_folder.mkdir(parents=True, exist_ok=True)
                    target_file = rest_folder / file_path.name

                    if target_file.exists():
                        name, ext = file_path.stem, file_path.suffix
                        counter = 1
                        while (rest_folder / f"{name}_{counter}{ext}").exists():
                            counter += 1
                        target_file = rest_folder / f"{name}_{counter}{ext}"

                    try:
                        shutil.copy2(file_path, target_file)
                    except Exception:
                        pass
                    continue
                
                file_count += 1
                
                # Aufnahmedatum und Änderungsdatum auslesen
                capture_date = self.get_creation_date(str(file_path))
                modification_date = self.get_modification_date(str(file_path))
                
                # Wenn Änderungsdatum älter ist als Aufnahmedatum, verwende Änderungsdatum.
                # Ansonsten verwende das Aufnahmedatum. Fallback auf vorhandenes Datum.
                date_obj = None
                if capture_date and modification_date:
                    date_obj = modification_date if modification_date < capture_date else capture_date
                elif capture_date:
                    date_obj = capture_date
                else:
                    date_obj = modification_date
                
                if date_obj:
                    # Erst den Jahresordner, dann den Monatsunterordner erstellen
                    year_folder = str(date_obj.year)
                    month_folder = str(date_obj.month)
                    
                    target_folder = target_path / year_folder / month_folder
                    target_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Zieldatei-Pfad
                    target_file = target_folder / file_path.name
                    
                    # Wenn Datei bereits existiert, füge Nummer hinzu
                    if target_file.exists():
                        name, ext = file_path.stem, file_path.suffix
                        counter = 1
                        while (target_folder / f"{name}_{counter}{ext}").exists():
                            counter += 1
                        target_file = target_folder / f"{name}_{counter}{ext}"
                    
                    try:
                        # Kopiere Datei
                        shutil.copy2(file_path, target_file)
                        organized_count += 1
                    except Exception as e:
                        pass
        
        return {
            'found': file_count,
            'organized': organized_count
        }


def main():
    root = tk.Tk()
    app = PhotoOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
