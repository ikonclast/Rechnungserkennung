# Screenshots fürs README

Zwei Aufnahmen, aufgenommen auf dem Server/Laptop, wo die Review-UI läuft
(`uvicorn src.ui.app:app` → http://127.0.0.1:8000). Dateinamen exakt so, dann
zieht das README sie automatisch:

| Datei | Motiv | Worauf achten |
|---|---|---|
| `01-rechnungsliste.png` | Übersicht `/invoices` | Mehrere Zeilen mit Dokumenttyp, Betrag und **Fail/Warn-Zählern**; Filterleiste oben sichtbar. |
| `02-review-detail.png` | Detailansicht `/invoices/{id}` | PDF-Panel links **mit sichtbarer Rechnung**, rechts die Felder mit **Confidence-Ampel** (grün/gelb/orange), darunter Validierung + „Rechnung bestätigen". Am besten eine Rechnung mit gemischten Ampelfarben zeigen. |

**Tipps:**
- Fenster auf ~1280–1440 px Breite, damit das Split-Layout (PDF | Felder) sauber steht.
- **Testdaten statt echter Mandantenrechnungen** verwenden (die Muster aus `samples/realtestdata/` — billomat/fastbill/lexoffice/sevdesk). Nichts Personenbezogenes im Bild.
- PNG, gern im Retina-/2×-Export für Schärfe.

Danach: `git add docs/screenshots/*.png` — die `.gitignore` ist bereits dafür freigeschaltet.
