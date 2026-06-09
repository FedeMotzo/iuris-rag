"""Converte il gold set UC1 (data/benchmark/gold_set_uc1.md) nel dataset gold JSON.

Asset durevole → data/benchmark/gold_uc1_classification.json.

Applica SOLO le sei ri-tipizzazioni edge→positive richieste (S07, S18, S19, S20,
S21, S23): il `verdetto_atteso` NON cambia; la motivazione edge è degradata a nota
di confine in `note`. Nessun altro `tipo` né `verdetto_atteso` è toccato.

I `gold_candidates` (punti Allegato III, lettere art. 5, flag art. 6(1)) sono
derivati dalla `base_giuridica` operativa di ciascuno scenario. Le sotto-lettere
Allegato III sono registrate per fedeltà; i punti sono la versione deduplicata a
granularità di classificatore (5(b)→punto 5).

    python scripts/build_gold_uc1.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "benchmark" / "gold_uc1_classification.json"

# edge → positive (verdetto invariato; motivazione edge → nota)
RETYPE_TO_POSITIVE = {"S07", "S18", "S19", "S20", "S21", "S23"}

# Scenari il cui esito "non alto rischio" dipende dal filtro art. 6(3) /
# lettura a-contrario di un punto Allegato III → isolati nel run.
ART6_3_EXEMPTION = {"S10", "S13", "S22", "S24", "S37", "S38", "S39", "S40"}

V_VIETATO = "vietato"
V_HR = "alto rischio (Allegato III)"
V_61 = "possibile alto rischio (art. 6(1))"
V_NO = "non alto rischio"


def C(points=None, subletters=None, art5=None, art6_1=False):
    return {
        "annex_iii_points": sorted(set(points or [])),
        "annex_iii_subletters": list(subletters or []),
        "art5_letters": list(art5 or []),
        "art6_1": bool(art6_1),
    }


# (id, settore, tipo_orig, verdetto, descrizione, base_giuridica, gold_candidates, note, multi_cat)
S = [
    ("S01", "PA", "positive", V_VIETATO,
     "Un comune intende installare nelle stazioni della metropolitana un sistema di IA che confronta i volti dei passanti, ripresi a distanza e senza loro partecipazione attiva, con una watchlist per identificare soggetti ricercati. L'uso è previsto a fini di sicurezza urbana dalla polizia locale.",
     "art. 5(1)(h); in subordine Allegato III, punto 1(a)",
     C(art5=["h"]),
     "RBI real-time a fini di contrasto → vietato 5(1)(h). In subordine (se differita/non-contrasto) sarebbe alto rischio 1(a).", False),

    ("S02", "banking", "negative", V_NO,
     "Una banca implementa nell'app mobile il riconoscimento facciale per consentire al cliente già registrato di sbloccare il proprio conto: il cliente presenta attivamente il volto e il sistema effettua un confronto 1:1 con il template salvato per confermare che è chi dichiara di essere.",
     "Allegato III, punto 1(a), seconda frase (esclusione della verifica/autenticazione biometrica)",
     C(),
     "Verifica/autenticazione 1:1 attiva esclusa dall'alto rischio (1(a) seconda frase).", False),

    ("S03", "insurance", "edge", V_HR,
     "Una compagnia assicurativa usa, per ricerche di mercato sul gradimento dei propri spot pubblicitari, un sistema di IA che analizza le espressioni facciali di un panel di volontari reclutati esternamente (non dipendenti) per inferire emozioni (gioia, irritazione) durante la visione.",
     "Allegato III, punto 1(c) (riconoscimento delle emozioni)",
     C(points=[1], subletters=["1c"]),
     "Context-flip emozioni: fuori lavoro/istruzione → alto rischio 1(c) (non vietato 5(f)).", False),

    ("S04", "PA", "edge", V_HR,
     "Un gestore pubblico della rete idrica installa un sistema di IA che funge da componente di sicurezza nel controllo della pressione delle condotte: in caso di anomalia critica può comandare l'arresto per prevenire rotture e rischi per l'incolumità.",
     "Allegato III, punto 2 (componenti di sicurezza nella fornitura di acqua); art. 3(14)",
     C(points=[2], subletters=["2"]),
     "Componente di sicurezza (protezione fisica diretta). Watch item Omnibus (test causale).", False),

    ("S05", "PA", "edge", V_NO,
     "La stessa utility usa un sistema di IA che ottimizza la distribuzione idrica prevedendo la domanda per ridurre i costi energetici; le funzioni di sicurezza (arresto di emergenza, allarmi) sono gestite da sistemi indipendenti che non dipendono da questa IA.",
     "Allegato III, punto 2 (esclusione: non è componente di sicurezza); art. 3(14)",
     C(),
     "Mera ottimizzazione/efficienza → non componente di sicurezza (based on draft).", False),

    ("S06", "PA", "positive", V_HR,
     "Un'università pubblica adotta un sistema di IA che assegna un punteggio e ordina in graduatoria i candidati per determinare l'ammissione ai corsi a numero chiuso.",
     "Allegato III, punto 3(a); art. 6(3) ultimo comma",
     C(points=[3], subletters=["3a"]),
     "Ammissione + scoring = profilazione → filtro 6(3) precluso (positive).", False),

    ("S07", "PA", "edge", V_HR,
     "Una scuola usa un sistema di IA di sorveglianza durante gli esami (proctoring) che monitora la webcam degli studenti per rilevare comportamenti vietati (consultazione di materiali non consentiti, presenza di terzi).",
     "Allegato III, punto 3(d)",
     C(points=[3], subletters=["3d"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: poggia sui confini del caso 3(d) chiariti dalla bozza; se inferisse emozioni/attenzione scatterebbe 5(f).", False),

    ("S08", "PA", "edge", V_NO,
     "Un istituto di formazione professionale fornisce agli studenti un tutor virtuale di IA che dà feedback formativo continuo durante l'apprendimento, senza attribuire voti né incidere su valutazioni o sulla progressione di carriera scolastica.",
     "Allegato III, punto 3(b) (interpretato a contrario); art. 6(3)(a)/(d)",
     C(),
     "Discriminatore sommativo (alto rischio) vs formativo (fuori scope). Based on draft.", False),

    ("S09", "insurance", "positive", V_HR,
     "Una compagnia assicurativa usa un sistema di IA che analizza, filtra e classifica in graduatoria i CV dei candidati a posizioni interne, assegnando un punteggio di idoneità usato dai recruiter per selezionare chi convocare.",
     "Allegato III, punto 4(a); art. 6(3) ultimo comma",
     C(points=[4], subletters=["4a"]),
     "Screening valutativo CV = profilazione → sempre alto rischio (positive).", False),

    ("S10", "insurance", "edge", V_NO,
     "La stessa compagnia usa un diverso sistema di IA che si limita a riformattare e a estrarre in modo strutturato le informazioni dai CV (nome, titoli, esperienze) per popolare un database ricercabile dai recruiter, senza assegnare punteggi né ordinare i candidati.",
     "Allegato III, punto 4(a) + art. 6(3)(a) (compito procedurale limitato)",
     C(),
     "Esenzione 6(3)(a): organizza il dato senza scoring/ranking. Based on draft.", False),

    ("S11", "banking", "edge", V_HR,
     "Una banca usa un sistema di IA che monitora e valuta in continuo le prestazioni e il comportamento (puntualità, reattività alle richieste dei clienti, metriche di affidabilità) dei dipendenti di filiale, con output usato per decisioni su premi e assegnazione di compiti.",
     "Allegato III, punto 4(b)",
     C(points=[4], subletters=["4b"]),
     "Monitoraggio/valutazione lavoratori 4(b); valutazione di persone = profilazione.", False),

    ("S12", "PA", "positive", V_HR,
     "Un ente pubblico usa un sistema di IA per valutare l'ammissibilità dei cittadini a prestazioni essenziali di assistenza pubblica (sussidi sociali) e per decidere se concederle, ridurle o revocarle.",
     "Allegato III, punto 5(a)",
     C(points=[5], subletters=["5a"]),
     "Ammissibilità a prestazioni essenziali da/per autorità pubbliche; profilazione.", False),

    ("S13", "PA", "edge", V_NO,
     "Lo stesso ente offre sul portale un chatbot di IA che fornisce ai cittadini informazioni generali sui requisiti dei sussidi e li indirizza ai moduli pertinenti, senza valutare l'ammissibilità del singolo né incidere sulla decisione.",
     "Allegato III, punto 5(a) + art. 6(3)(a)/(d)",
     C(),
     "Informazione/orientamento ≠ valutazione ammissibilità. Esenzione 6(3). Based on draft.", False),

    ("S14", "banking", "positive", V_HR,
     "Una banca usa un sistema di IA per valutare l'affidabilità creditizia delle persone fisiche e stabilirne il merito di credito (credit scoring) nelle richieste di prestito al consumo.",
     "Allegato III, punto 5(b); art. 6(3) ultimo comma",
     C(points=[5], subletters=["5b"]),
     "Credit scoring di persone fisiche = profilazione (CGUE C-634/21) → sempre alto rischio.", False),

    ("S15", "banking", "edge", V_NO,
     "La stessa banca usa un sistema di IA la cui finalità principale è il riconoscimento di pattern e il rilevamento di anomalie per individuare frodi finanziarie sulle transazioni; l'output può occasionalmente alimentare valutazioni creditizie ma la funzione principale è antifrode.",
     "Allegato III, punto 5(b), inciso di esclusione (individuazione frodi finanziarie)",
     C(),
     "Carve-out antifrode (solo 5(b)). Based on draft; AML/CFT escluso dall'esenzione.", False),

    ("S16", "insurance", "positive", V_HR,
     "Una compagnia usa un sistema di IA per la valutazione del rischio e la tariffazione di polizze vita e malattia rivolte a persone fisiche; il sistema incorpora anche una funzione di rilevamento frodi integrata nello stesso modello di pricing.",
     "Allegato III, punto 5(c)",
     C(points=[5], subletters=["5c"]),
     "Asimmetria 5(b) vs 5(c): nessun carve-out antifrode in 5(c) (assicurazione vita/salute).", False),

    ("S17", "healthcare", "positive", V_HR,
     "Una centrale operativa del 118 usa un sistema di IA che valuta e classifica le chiamate di emergenza e stabilisce le priorità di invio dei mezzi di soccorso, incluso il triage dei pazienti per l'assistenza sanitaria d'emergenza.",
     "Allegato III, punto 5(d)",
     C(points=[5], subletters=["5d", "5a"]),
     "Multi-categoria 5(d) + 5(a): ENTRAMBE sotto-lettere del PUNTO 5 → a granularità classificatore = punto 5.", True),

    ("S18", "PA", "edge", V_HR,
     "Una forza di polizia usa un sistema di IA come poligrafo digitale (\"macchina della verità\") per valutare l'attendibilità delle dichiarazioni di persone durante le indagini.",
     "Allegato III, punto 6(b)",
     C(points=[6], subletters=["6b"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: dipende dai confini del caso del punto 6 (uso consentito dal diritto) chiariti dalla bozza.", False),

    ("S19", "PA", "edge", V_HR,
     "La stessa autorità usa un sistema di IA per valutare l'affidabilità degli elementi probatori raccolti nel corso delle indagini penali.",
     "Allegato III, punto 6(c)",
     C(points=[6], subletters=["6c"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: la bozza esclude indicizzazione/traduzione/trascrizione; linea valutazione-vs-organizzazione interpretativa (¶365).", False),

    ("S20", "PA", "edge", V_HR,
     "Una procura usa un sistema di IA che stima il rischio di recidiva di un imputato a supporto della valutazione del giudice/PM; la valutazione si fonda anche su fatti oggettivi e verificabili direttamente connessi all'attività criminosa, NON unicamente sulla profilazione.",
     "Allegato III, punto 6(d)",
     C(points=[6], subletters=["6d"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: linea 5(1)(d) vietato vs 6(d) alto rischio dipende dalla soglia di intervento umano e dall'essere o meno 'unicamente' su profilazione.", False),

    ("S21", "PA", "edge", V_HR,
     "Un'autorità competente usa un sistema di IA per valutare il rischio (per la sicurezza, di immigrazione irregolare, per la salute) posto da una persona fisica che intende entrare nel territorio nazionale.",
     "Allegato III, punto 7(b)",
     C(points=[7], subletters=["7b"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: confini del caso del punto 7 (uso consentito dal diritto) precisati dalla bozza; valutazione di rischio individuale = profilazione.", False),

    ("S22", "PA", "edge", V_NO,
     "La stessa autorità usa un sistema di IA per tradurre automaticamente dalla lingua originale i documenti allegati alle domande d'asilo, mettendo il testo tradotto a disposizione del funzionario che esamina la pratica, senza valutare l'ammissibilità.",
     "Allegato III, punto 7(c) + art. 6(3)(d) (compito preparatorio)",
     C(),
     "Traduzione = compito preparatorio 6(3)(d). Based on draft.", False),

    ("S23", "PA", "edge", V_HR,
     "Un tribunale adotta un sistema di IA che assiste il giudice nella ricerca e interpretazione dei fatti e del diritto e nell'applicazione della legge a una serie concreta di fatti, producendo bozze argomentate di decisione.",
     "Allegato III, punto 8(a)",
     C(points=[8], subletters=["8a"]),
     "RI-TIPIZZATO edge→positive (verdetto invariato). Nota di confine originale: la bozza esclude da 8(a) strumenti interni di corte (trascrizione/anonimizzazione/ricerca senza significato, ¶419); linea assistenza-sostanziale vs amministrativo interpretativa.", False),

    ("S24", "PA", "edge", V_NO,
     "Lo stesso tribunale usa un sistema di IA esclusivamente per la trascrizione delle udienze (speech-to-text) e per l'anonimizzazione delle sentenze prima della pubblicazione, senza alcuna funzione di ricerca/interpretazione giuridica.",
     "Allegato III, punto 8(a) (interpretato a contrario) + art. 6(3)(a)/(d)",
     C(),
     "Strumento amministrativo di corte (¶419). Esenzione 6(3). Based on draft.", False),

    ("S25", "PA", "positive", V_HR,
     "Un soggetto realizza un sistema di IA destinato a influenzare l'esito di elezioni/referendum o il comportamento di voto delle persone fisiche, con output destinato a essere utilizzato direttamente dagli elettori (es. micro-messaggi persuasivi personalizzati).",
     "Allegato III, punto 8(b)",
     C(points=[8], subletters=["8b"]),
     "Influenza diretta sul voto (nucleo 8(b)). Se manipolativo/subliminale valutare anche 5(1)(a).", False),

    ("S26", "banking", "positive", V_VIETATO,
     "Una banca implementa nell'app un sistema di IA che, analizzando in tempo reale lo stato di frustrazione del cliente, inserisce tecniche manipolative non percepibili per indurlo a sottoscrivere prodotti finanziari ad alto margine che non avrebbe altrimenti scelto, con rischio di danno economico significativo.",
     "art. 5(1)(a)",
     C(art5=["a"]),
     "Tecniche subliminali/manipolative non percepibili + danno significativo (5(1)(a)).", False),

    ("S27", "banking", "positive", V_VIETATO,
     "Una società di credito al consumo usa un sistema di IA predittivo per individuare persone in grave difficoltà economica residenti in specifici quartieri a basso reddito e proporre loro prodotti finanziari predatori, sfruttandone la situazione socio-economica e causando danno finanziario significativo.",
     "art. 5(1)(b)",
     C(art5=["b"]),
     "Sfruttamento vulnerabilità socio-economica (5(1)(b)).", False),

    ("S28", "PA", "positive", V_VIETATO,
     "Un ente pubblico realizza un sistema di IA che attribuisce ai cittadini un \"punteggio sociale\" basato sul comportamento sociale e su caratteristiche personali, usato poi per negare l'accesso a servizi in contesti non collegati e in modo sproporzionato.",
     "art. 5(1)(c)",
     C(art5=["c"]),
     "Social scoring cross-contesto/sproporzionato (5(1)(c)).", False),

    ("S29", "PA", "positive", V_VIETATO,
     "Una forza di polizia usa un sistema di IA che predice il rischio che singole persone commettano reati unicamente sulla base della profilazione e della valutazione dei tratti della personalità, senza alcun fatto oggettivo verificabile connesso a un'attività criminosa.",
     "art. 5(1)(d)",
     C(art5=["d"]),
     "Polizia predittiva UNICAMENTE su profilazione (5(1)(d)). Flip con S20 (6(d)).", False),

    ("S30", "PA", "positive", V_VIETATO,
     "Un fornitore realizza un sistema di IA che crea/amplia una banca dati di riconoscimento facciale tramite scraping non mirato di immagini facciali da internet e da filmati di telecamere a circuito chiuso, offerto poi ad enti per finalità di sicurezza.",
     "art. 5(1)(e)",
     C(art5=["e"]),
     "Scraping facciale non mirato (5(1)(e)), vietato a prescindere dall'uso.", False),

    ("S31", "banking", "positive", V_VIETATO,
     "Una banca installa nei call center un sistema di IA che, dai segnali biometrici vocali, inferisce le emozioni dei propri dipendenti operatori (rabbia, stress) per monitorarne lo stato emotivo durante le chiamate, con risultati condivisi con l'HR per valutazioni.",
     "art. 5(1)(f)",
     C(art5=["f"]),
     "Inferenza emozioni DIPENDENTI sul lavoro (5(1)(f)). Flip: clienti → 1(c) alto rischio.", False),

    ("S32", "insurance", "positive", V_VIETATO,
     "Una compagnia usa un sistema di IA di categorizzazione biometrica che, dai volti dei clienti, deduce convinzioni religiose e orientamento sessuale per segmentare l'offerta assicurativa.",
     "art. 5(1)(g)",
     C(art5=["g"]),
     "Categorizzazione biometrica di attributi protetti (5(1)(g)).", False),

    ("S33", "PA", "positive", V_VIETATO,
     "Una questura intende usare l'identificazione biometrica remota \"in tempo reale\" in piazze e stazioni a fini di contrasto, senza che ricorra alcuna delle eccezioni tassative né un'autorizzazione giudiziaria/amministrativa, e senza una legge nazionale conforme che la abiliti.",
     "art. 5(1)(h)",
     C(art5=["h"]),
     "RBI real-time contrasto senza base conforme (5(1)(h)).", False),

    ("S34", "healthcare", "positive", V_61,
     "Un'azienda immette un software di IA per l'analisi di immagini mammografiche che rileva lesioni sospette; è un dispositivo medico classe IIb ai sensi del Regolamento (UE) 2017/745 (MDR), soggetto a valutazione di conformità con organismo notificato.",
     "art. 6(1)(a)(b); Allegato I, sez. A (MDR Reg. 2017/745); art. 3(14)",
     C(art6_1=True),
     "Dispositivo medico classe IIb + organismo notificato → art. 6(1). MDR fuori corpus.", False),

    ("S35", "healthcare", "negative", V_NO,
     "Una software house immette un'app di IA, qualificata come dispositivo medico di classe I ai sensi dell'MDR (autocertificata, senza organismo notificato), che si limita ad archiviare e comunicare dati clinici con rischio minimo; non svolge alcuna funzione dell'Allegato III.",
     "art. 6(1)(b) (a contrario: assenza di valutazione di terzi); Allegato I",
     C(),
     "Classe I MDR = autocertificazione, manca la valutazione di terzi (2a condizione 6(1)).", False),

    ("S36", "altro", "edge", V_61,
     "Un costruttore integra in un macchinario industriale (coperto dal Regolamento Macchine, Allegato I) un sistema di visione IA la cui funzione prevista è arrestare in sicurezza la macchina al rilevamento della presenza di un operatore nella zona pericolosa; il prodotto è soggetto a valutazione di conformità.",
     "art. 6(1)(a)(b); Allegato I (Regolamento Macchine, Reg. (UE) 2023/1230); art. 3(14)",
     C(art6_1=True),
     "Componente di sicurezza di prodotto Allegato I + valutazione terzi → art. 6(1). Watch item Omnibus.", False),

    ("S37", "insurance", "edge", V_NO,
     "Una compagnia usa un sistema di IA che converte documenti non strutturati (email, PDF) dei sinistri in dati strutturati e li classifica in categorie predefinite per il fascicolo, senza assegnare punteggi né valutare la posizione del cliente.",
     "art. 6(3)(a)",
     C(),
     "Filtro 6(3)(a): compito procedurale limitato (no scoring/ranking). Based on draft.", False),

    ("S38", "PA", "edge", V_NO,
     "Un ente usa un sistema di IA che, su un provvedimento amministrativo già redatto e deciso da un funzionario, individua refusi ed errori formali per migliorarne la qualità, senza sostituire né modificare la valutazione di merito.",
     "art. 6(3)(b)",
     C(),
     "Filtro 6(3)(b): migliora un'attività umana già completata. Based on draft.", False),

    ("S39", "banking", "edge", V_NO,
     "Una banca usa un sistema di IA che, ex post, analizza le decisioni di affidamento già adottate dai gestori per rilevare deviazioni/anomalie rispetto agli schemi decisionali passati; le discrepanze sono sottoposte a revisione umana e non rientrano in tempo reale nel processo decisionale.",
     "art. 6(3)(c)",
     C(),
     "Filtro 6(3)(c): rileva schemi/deviazioni ex post con revisione umana. Based on draft.", False),

    ("S40", "banking", "edge", V_NO,
     "Una banca usa un sistema di IA che produce un riassunto strutturato e l'indicizzazione dei documenti di supporto (buste paga, estratti conto) per l'analista del credito, senza assegnare punteggi né raccomandare l'esito.",
     "art. 6(3)(d)",
     C(),
     "Filtro 6(3)(d): compito preparatorio (indicizzazione/riassunto). Based on draft.", False),

    ("S41", "insurance", "positive", V_HR,
     "Una compagnia sostiene che il proprio sistema di IA per la tariffazione vita svolga solo un \"compito preparatorio\", ma il sistema profila le persone fisiche elaborando dati personali per valutarne/prevederne aspetti (stato di salute, stile di vita) ai fini del prezzo.",
     "art. 6(3), ultimo comma (caveat profilazione) + Allegato III p.5(c)",
     C(points=[5], subletters=["5c"]),
     "Caveat profilazione: profilazione → SEMPRE alto rischio, filtro 6(3) non invocabile (gold netto).", False),

    ("S42", "banking", "negative", V_NO,
     "Una banca usa un sistema di IA per ottimizzare la gestione energetica e la climatizzazione delle filiali, regolando il riscaldamento in base all'affluenza per ridurre i consumi.",
     "nessun punto Allegato III; nessun art. 6(1); nessun art. 5",
     C(),
     "Negativo netto: nessun gancio normativo.", False),

    ("S43", "insurance", "negative", V_NO,
     "Una compagnia usa un sistema di IA per valutare l'affidabilità creditizia di società (persone giuridiche), elaborandone bilanci e dati finanziari aziendali, senza valutare le finanze personali di alcuna persona fisica.",
     "Allegato III, punto 5(b) (a contrario — solo persone fisiche)",
     C(),
     "Persone GIURIDICHE → fuori 5(b) (¶74). Trappola persone fisiche vs giuridiche.", False),

    ("S44", "banking", "negative", V_NO,
     "Una banca usa un chatbot di IA per assistenza clienti che risponde a domande su orari, sedi e funzionalità dell'app, dichiarando di essere un sistema automatizzato.",
     "nessun punto Allegato III; nessuna pratica vietata",
     C(),
     "Assistenza informativa generica. Trasparenza art. 50 ≠ classificazione (fuori oggetto).", False),

    ("S45", "healthcare", "negative", V_NO,
     "Un ospedale usa un sistema di IA per ottimizzare la logistica del magazzino farmaceutico e prevedere il riapprovvigionamento delle scorte, senza alcun impatto su decisioni cliniche o su persone fisiche.",
     "nessun punto Allegato III; nessun art. 6(1)",
     C(),
     "Gestionale puro in sanità (contrasto con triage 5(d)/dispositivo medico 6(1)).", False),

    ("S46", "PA", "negative", V_NO,
     "Un comune usa un sistema di IA per indirizzare e instradare le segnalazioni dei cittadini (buche, rifiuti) all'ufficio competente in base a parole chiave, senza valutare persone né incidere su prestazioni essenziali.",
     "nessun punto Allegato III",
     C(),
     "Instradamento amministrativo (contrasto con 5(a)/5(d)).", False),

    ("S47", "insurance", "edge", V_NO,
     "Una compagnia usa un sistema di IA che, dopo una decisione su una polizza, gestisce i reclami e simula prezzi alternativi (\"what-if\") a fini informativi per il cliente, senza determinare la tariffa effettiva né valutare il rischio della persona.",
     "Allegato III, punto 5(c) (a contrario); art. 6(3)",
     C(),
     "Simulazione informativa/reclami a valle ≠ valutazione/tariffazione 5(c). Based on draft.", False),

    ("S48", "healthcare", "edge", V_NO,
     "Un ospedale usa un sistema di IA che, dai segnali fisiologici, inferisce la stanchezza/sonnolenza dei chirurghi per allertarli ed evitare incidenti in sala operatoria; non inferisce emozioni né stati psicologici.",
     "art. 5(1)(f) (a contrario) + Allegato III p.1(c) (a contrario)",
     C(),
     "Stato fisico (fatica) ≠ emozione (cons. 18); eccezione sicurezza. Based on draft.", False),

    ("S49", "banking", "edge", V_NO,
     "Una banca usa un sistema di IA antiriciclaggio (AML/CFT) per individuare operazioni sospette ai fini degli obblighi di legge; l'output non è usato per valutare il merito creditizio dei clienti.",
     "Allegato III, punto 5(b) (a contrario); punto 6 (a contrario, \"per conto di\")",
     C(),
     "AML/CFT: non carve-out frode 5(b) ma neppure automaticamente 5(b)/punto 6 (¶81). Based on draft.", False),

    ("S50", "PA", "positive", V_HR,
     "Un'azienda sanitaria pubblica adotta un unico sistema di IA che (i) valuta l'ammissibilità dei cittadini a prestazioni sanitarie essenziali e (ii) all'interno dello stesso flusso, in pronto soccorso, esegue il triage dei pazienti per stabilire la priorità di accesso alle cure d'emergenza.",
     "Allegato III, punto 5(a) e punto 5(d)",
     C(points=[5], subletters=["5a", "5d"]),
     "Multi-categoria 5(a) + 5(d): ENTRAMBE sotto-lettere del PUNTO 5 → a granularità classificatore = punto 5.", True),
]


def main() -> int:
    entries = []
    for sid, settore, tipo_orig, verdetto, descr, base, cand, note, multi in S:
        tipo = "positive" if sid in RETYPE_TO_POSITIVE else tipo_orig
        entries.append({
            "id": sid,
            "settore": settore,
            "tipo": tipo,
            "tipo_originale": tipo_orig,
            "retyped_edge_to_positive": sid in RETYPE_TO_POSITIVE,
            "descrizione": descr,
            "verdetto_atteso": verdetto,
            "gold_candidates": cand,
            "base_giuridica": base,
            "multi_categoria": multi,
            "art6_3_exemption": sid in ART6_3_EXEMPTION,
            "note": note,
        })

    assert len(entries) == 50, f"attesi 50 scenari, trovati {len(entries)}"
    n_retyped = sum(e["retyped_edge_to_positive"] for e in entries)
    assert n_retyped == 6, f"attese 6 ri-tipizzazioni, trovate {n_retyped}"

    payload = {
        "schema": "uc1_classification_gold_v1",
        "source": "data/benchmark/gold_set_uc1.md",
        "gold_verified_date": "2026-06-09",
        "verdict_classes": [V_VIETATO, V_HR, V_61, V_NO],
        "retypings_applied": sorted(RETYPE_TO_POSITIVE),
        "n_scenarios": len(entries),
        "scenarios": entries,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scritto {OUT.relative_to(ROOT)} — {len(entries)} scenari "
          f"({n_retyped} ri-tipizzati edge→positive).")
    from collections import Counter
    print("Per tipo:", dict(Counter(e["tipo"] for e in entries)))
    print("Per verdetto:", dict(Counter(e["verdetto_atteso"] for e in entries)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
