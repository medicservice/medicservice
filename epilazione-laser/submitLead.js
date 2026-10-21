// URL della web app Apps Script (finisce con /exec).
// Non è un dato segreto: il sito è statico su GitHub Pages, va bene lasciarlo qui.
const LEAD_ENDPOINT = 'https://script.google.com/macros/s/AKfycbwsDL4fQpA_WnNfaikGB6Cssq6XkR42Z1Kr9z80BCJJOXRGrKnslqUava3uGNFP03NmwQ/exec';

/**
 * Invia una richiesta di contatto al Google Sheet.
 *
 * @param {{
 *   nome: string,
 *   telefono: string,
 *   email?: string,
 *   preferenza: 'Chiamata' | 'WhatsApp' | 'Email',
 *   privacy: boolean,
 *   website?: string   // campo trappola anti-bot, deve restare vuoto
 * }} lead
 * @returns {Promise<{ ok: boolean, error?: string }>}
 */
async function submitLead(lead) {
  try {
    const res = await fetch(LEAD_ENDPOINT, {
      method: 'POST',
      // text/plain evita la richiesta preliminare CORS, che Apps Script non gestisce
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ ...lead, pagina: window.location.href }),
    });
    return await res.json();
  } catch {
    return { ok: false, error: 'Invio non riuscito. Riprova o chiama il centralino.' };
  }
}

/*
  Campo trappola da aggiungere dentro il <form> (invisibile alle persone):

  <input type="text" name="website" tabindex="-1" autocomplete="off"
         aria-hidden="true" style="position:absolute;left:-9999px" />

  Esempio d'uso nel submit:

  const result = await submitLead({
    nome, telefono, email, preferenza,
    privacy: consensoSpuntato,
    website: valoreCampoTrappola,
  });
  if (result.ok) mostraMessaggioDiConferma();
  else mostraErrore(result.error);

  Su HTML statico (questo progetto) la funzione è globale: includi lo script
  e chiama submitLead(...) dal listener di submit del form.
*/
