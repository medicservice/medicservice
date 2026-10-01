# Landing page Epilazione laser — medicservice.it

## Dove va
Copiare la cartella `epilazione-laser/` nella root del repository `medicservice/medicservice`
(stesso livello di `medicina-estetica/`, `medici/`, `styles.css`).
URL finale: https://medicservice.it/epilazione-laser/

La pagina usa i file già presenti nel sito, non va copiato altro:
- `/styles.css`, `/site.js`, `/assets/logo-horizontal.svg`, `/assets/logo-horizontal-white.svg`
- `/assets/photos/MS-33.jpg` (og:image)
- Iubenda (siteId 305777, cookiePolicyId 865793) e GTM-TKGKM6ZJ, già configurati nell'head.

## Da completare prima della pubblicazione (cerca le parentesi quadre nel file)
1. `[ID-FORMSPREE]` — creare un modulo su formspree.io (gratuito fino a 50 invii/mese) e inserire l'ID.
   I contatti arrivano via email all'indirizzo registrato su Formspree.
2. Numero WhatsApp inserito: +39 389 125 5173.
3. Pacchetti: zone comprese e numero di sedute indicative sono nello script del quiz
   (oggetto `packs`, in fondo al file) ancora tra parentesi quadre. I prezzi a seduta sono già inseriti
   (Viso 50, Ascelle e inguine 100, Gambe complete 200, Schiena e spalle 200).
4. `[4–8]` settimane e `[6–8]` sedute nel percorso e nelle FAQ — intervalli reali.
5. FAQ "E se dopo la visita il laser non fosse adatto a me?" — politica del centro.
6. Nota sotto il quiz: condizioni di pagamento in più soluzioni (o togliere la frase).
7. Dr. Paolo Solinas: non ha ancora una pagina in `medici/`; quando c'è, trasformare il nome in link.

## Tracciamento (Meta Pixel)
Il Pixel NON è nel file: va aggiunto in Google Tag Manager (GTM-TKGKM6ZJ) con attivazione
dopo il consenso marketing di Iubenda (emitGtmEvents è già attivo).
- Tag "Meta Pixel — base code": trigger = consenso Iubenda (purpose marketing).
- Tag "Meta Lead": trigger = evento personalizzato `lead_epilazione`
  (la pagina lo spinge nel dataLayer a invio riuscito, con la variabile `pacchetto`).
- Eventi del quiz, utili per analisi e remarketing: `quiz_step` (variabile `step` 1–4)
  e `quiz_result` (variabili `pacchetto`, `fototipo`, `eta`).
- Il modulo invia anche un campo nascosto `quiz` con fototipo ed età scelti.
Se il Pixel è già caricato in pagina, la pagina chiama anche `fbq('track','Lead')` da sola.

## Campagna Meta (riassunto)
- Obiettivo Lead; testare in parallelo modulo nativo Meta ("maggiore intenzione") e landing.
- Pubblico Advantage+, raggio 15–20 km da Oristano, età 20–55, uomini inclusi.
- Budget iniziale 15 €/giorno per 14 giorni.
- Domande modulo: zone/pacchetto, contatto preferito (WhatsApp/telefono), fascia oraria.
- Ricontattare i lead entro un'ora.
- Pubblicità sanitaria (L. 145/2018 c. 525): solo contenuti informativi. Ok indicare i prezzi,
  evitare "promo", "sconto", "offerta limitata", "gratis". Niente prima/dopo, solo 18+.

### Annuncio A — autorevolezza
Testo: Epilazione laser in un centro medico a Oristano. Ogni percorso inizia con una visita
dermatologica: controllo della pelle e del fototipo, poi un piano di sedute su misura.
Pacchetti completi, dalla visita al controllo finale.
Titolo: Epilazione laser con visita dermatologica
Pulsante: Richiedi informazioni

### Annuncio B — domande frequenti
Testo: Fa male? Quante sedute servono? Funziona su pelle scura o abbronzata? Il nostro
dermatologo risponde alle domande più comuni sull'epilazione laser. Lascia i tuoi dati e ti
ricontattiamo per una valutazione in studio.
Titolo: Epilazione laser: le risposte del medico
Pulsante: Richiedi informazioni

Creatività consigliata: video verticale 15–20 s del medico che risponde a una domanda.
