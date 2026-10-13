# Landing page Radiofrequenza Exilis Elite — medicservice.it

## Dove va
Copiare la cartella `radiofrequenza-exilis/` nella root del repository `medicservice/medicservice`.
URL finale: https://medicservice.it/radiofrequenza-exilis/
Usa `/styles.css`, `/site.js`, i loghi in `/assets` e `/assets/photos/MS-33.jpg` (og:image), già presenti nel sito.
Iubenda e GTM-TKGKM6ZJ sono già nell'head, identici alle altre pagine.

## Da completare (cerca le parentesi quadre nel file)
1. `[ID-FORMSPREE]` — ID del modulo creato su formspree.io.
2. WhatsApp: già inserito (389 1255173 → wa.me/393891255173).
3. Pacchetti nello script del quiz (oggetto `packs`, in fondo al file): prezzo a seduta `[000]`,
   zone comprese e numero di sedute per Viso/collo, Braccia, Addome/fianchi, Cosce/ginocchia/glutei.
4. Nel percorso e nelle FAQ: `[4–6]` sedute, `[1–2]` settimane di intervallo, `[15–30]` minuti a zona,
   `[8]` settimane per il controllo, `[6–12]` mesi per il richiamo. Verificare con il protocollo BTL in uso.
5. Chi esegue il trattamento ("personale formato sulla tecnologia"): se è un medico, dirlo.
6. Nota sotto il quiz: condizioni di pagamento in più soluzioni (o togliere la frase).

## Cosa dice la pagina su Exilis Elite (da verificare con la scheda tecnica BTL)
- Radiofrequenza monopolare + ultrasuoni, raffreddamento integrato nel manipolo.
- Indicazioni: rilassamento cutaneo (viso, collo, braccia, addome, cosce, ginocchia) e adiposità localizzate.
- Nessun tempo di recupero; lieve arrossamento transitorio.
- Controindicazioni citate: gravidanza, pacemaker/impianti metallici nella zona, pelle infiammata o lesionata.
- Non è un sostituto di lifting o liposuzione e non fa perdere peso.
Fonte: conoscenza generale della tecnologia BTL Exilis; non è stata fatta una verifica online.

## Tracciamento
Stessa impostazione della pagina epilazione: Pixel in GTM dopo consenso Iubenda.
Eventi dataLayer: `lead_exilis` (invio modulo), `quiz_step` (step 1–4),
`quiz_result` (variabili `pacchetto`, `obiettivo`, `eta`). Campo nascosto `quiz` nel modulo.

## Note per gli annunci Meta
- Pubblico 18+, raggio 15–20 km da Oristano, età 30–60 rende di più per questo trattamento.
- Niente foto prima/dopo, niente riferimenti a difetti del corpo ("pancia", "cellulite" come problema).
  Parlare di tono, compattezza, profili.
- Annuncio A: "Radiofrequenza Exilis Elite a Oristano: tratta il rilassamento della pelle e le adiposità
  localizzate di viso e corpo. Senza aghi, senza tagli, senza tempi di recupero. Scopri cosa può fare per te."
- Annuncio B (FAQ): "Fa male? Quando si vedono i risultati? Si può fare in estate? Le risposte sulla
  radiofrequenza Exilis Elite. Lascia i tuoi dati e ti ricontattiamo."
