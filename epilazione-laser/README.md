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
3. Pacchetti: tutti da 6 sedute (più 2 di ripasso). Le zone comprese sono nello script del quiz
   (oggetto `packs`, in fondo al file) ancora tra parentesi quadre.
   Lunghezza d'onda indicata per fototipo (funzione `wl` nello script): I–II alessandrite 755 nm,
   III–IV 755 o 1064 nm in base al pelo, V–VI Nd:YAG 1064 nm. Da far confermare ai dermatologi, soprattutto per il IV.
4. `[4–8]` settimane tra le sedute nel percorso — intervallo reale.
5. FAQ "E se dopo la visita il laser non fosse adatto a me?": testo già scritto. Decidere cosa succede
   con la visita e il pacchetto in questo caso e dirlo al ricontatto, non in pagina.
6. Dr. Paolo Solinas: non ha ancora una pagina in `medici/`; quando c'è, trasformare il nome in link.
7. FAQ "Come mi preparo alla seduta?": `[4]` settimane senza ceretta, pinzetta ed epilatore — confermare con il protocollo del centro.
8. Prezzi: la pagina non riporta prezzi di pacchetti né della visita, per scelta. Si comunicano al ricontatto o in visita.
9. Visita dermatologica e pacchetto: oggi la pagina non dice se la visita è compresa nel pacchetto
   (non compare negli elenchi di ciò che è compreso). Se lo è, aggiungerla al riquadro "In sintesi",
   alla lista del risultato del quiz e alla nota sotto il quiz.

## Posizionamento
Tre punti di forza con lo stesso peso: visita dermatologica preventiva, tecnologia (Deka Again PRO,
alessandrite 755 nm + Nd:YAG 1064 nm, modalità Moveo, raffreddamento) e percorso seguito (test, sedute, due ripassi compresi).
Le caratteristiche vengono dalle comunicazioni pubbliche di DEKA:
verificarle con la scheda tecnica del sistema in uso (nome esatto del modello compreso).
Niente superlativi ("il migliore", "il più avanzato"): la pubblicità sanitaria deve restare informativa.
Non presentare le sedute come eseguite dal medico: il medico fa la visita iniziale.
Il centro non fa una seduta di controllo finale: non citarla in pagina né negli annunci.

## Tracciamento (Meta Pixel)
Il Pixel NON è nel file: va aggiunto in Google Tag Manager (GTM-TKGKM6ZJ) con attivazione
dopo il consenso marketing di Iubenda (emitGtmEvents è già attivo).
- Tag "Meta Pixel — base code": trigger = consenso Iubenda (purpose marketing).
- Tag "Meta Lead": trigger = evento personalizzato `lead_epilazione`
  (la pagina lo spinge nel dataLayer a invio riuscito, con la variabile `pacchetto`).
- Eventi del quiz, utili per analisi e remarketing: `quiz_step` (variabile `step` 1–4)
  e `quiz_result` (variabili `pacchetto`, `fototipo`, `eta`, `lunghezza_onda`).
- Il modulo invia anche un campo nascosto `quiz` con fototipo, età, zona e lunghezza d'onda.
- Clic su telefono e WhatsApp: evento `contatto_click` (variabili `tipo` = telefono/whatsapp,
  `posizione` = header, footer o id della sezione). Da usare come conversione secondaria in GTM:
  da smartphone molti contatti passano da qui e non dal modulo.
Se il Pixel è già caricato in pagina, la pagina chiama anche `fbq('track','Lead')` da sola.

## Campagna Meta (riassunto)
- Obiettivo Lead; testare in parallelo modulo nativo Meta ("maggiore intenzione") e landing.
- Pubblico Advantage+, raggio 15–20 km da Oristano, età 20–55, uomini inclusi.
- Budget iniziale 15 €/giorno per 14 giorni.
- Domande modulo: zone/pacchetto, contatto preferito (WhatsApp/telefono), fascia oraria.
- Ricontattare i lead entro un'ora.
- Pubblicità sanitaria (L. 145/2018 c. 525): solo contenuti informativi. Niente prezzi in pagina
  né negli annunci; evitare "promo", "sconto", "offerta limitata", "gratis". Niente prima/dopo, solo 18+.

### Annuncio A — autorevolezza
Testo: Epilazione laser in un centro medico a Oristano. Ogni percorso inizia con una visita
dermatologica: controllo della pelle e del fototipo, poi un piano di sedute su misura.
Le sedute si fanno con Deka Again PRO, per pelli chiare e scure.
Pacchetti completi, dalla visita all'ultima seduta.
Titolo: Epilazione laser con visita dermatologica
Pulsante: Richiedi informazioni

### Annuncio B — domande frequenti
Testo: Fa male? Quante sedute servono? Funziona su pelle scura o abbronzata? Sulla nostra pagina
trovi le risposte alle domande più comuni sull'epilazione laser. Ogni percorso inizia con una visita
dermatologica. Lascia i tuoi dati e ti ricontattiamo.
Titolo: Epilazione laser: i dubbi più comuni
Pulsante: Richiedi informazioni

Creatività consigliata: video verticale 15–20 s con una domanda e la risposta in sovrimpressione,
immagini del laser e del centro. Se compare un dermatologo, parla solo della visita.
