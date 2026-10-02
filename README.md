# 📘 Guida Semplice per Aggiornare i Dati del Sito

Segui questi passaggi in ordine per aggiornare il sito in meno di 2 minuti.

---

### PASSAGGIO 1: Apri il progetto
1. Apri l'app **GitHub Desktop**.
2. Clicca nel menu in alto su **Repository** e poi su **Open in Visual Studio Code** (oppure premi sulla tastiera `Ctrl + Shift + A`).

---

### PASSAGGIO 2: Sostituisci il file con i nuovi dati
1. Prendi il nuovo file CSV aggiornato.
2. Incollalo dentro la cartella **`data`** del progetto.
3. Assicurati che il file si chiami esattamente:
   `ordini.csv`  
   *(Se chiede di sostituire il file esistente, clicca **Sì**)*.

---

### PASSAGGIO 3: Apri il Terminale in VS Code
Dentro Visual Studio Code, vai nel menu in alto e clicca **Terminal** > **New Terminal** *(oppure premi `Ctrl + Shift + ~` sulla tastiera)*.

---

### PASSAGGIO 4: Genera i nuovi dati
Copia questo comando, incollalo nel terminale di VS Code e premi **Invio**:

```powershell
python build.py
git add . ; git commit -m "Aggiornato ordini.csv e data.json" ; git push
