# Dropzone Map Service 14.4

Servizio GitHub Actions + Pages da pubblicare sul proprio repository. Esegue il controllo ogni sei ore e pubblica `mappa-verificata.json`.

**Novità:** pubblica anche informazioni testuali senza coordinate. L’app le mostra nell’elenco della categoria; solo gli elementi con coordinate normalizzate valide diventano tag sulla mappa. Non inventa posizioni.

Fonti automatiche: Fortnite-API (POI) e FN Api (missioni). NPC e luoghi nascosti possono essere importati da `data/verified-points.json` con `kind`, `name`, `description`, `sourceUrl` HTTPS e `source`; `x` e `y` sono facoltativi. Non viene eseguito scraping automatico dei forum. Sono escluse Fortnite.gg e Fortnite Database.

**Attivazione:** carica il contenuto di questa cartella in un repository pubblico GitHub, abilita Actions con permessi di scrittura e Pages dalla branch main (root), avvia il workflow una volta. Nell’app inserisci l’URL `https://TUO-UTENTE.github.io/NOME-REPO/mappa-verificata.json`.

In caso di errore di una fonte il servizio mantiene gli elementi precedenti della fonte e segnala l’errore. La data `lastSuccessfulDataAt` cambia soltanto se almeno una fonte online ha restituito dati validi. Il workflow programmato può subire ritardi.

## Tag approssimativi
Nel file data/verified-points.json aggiungere `zoneName` con il nome esatto di una location della mappa e `searchHint` con istruzioni concrete per riconoscere il luogo. L’app usa il centro del POI corrispondente come riferimento APPROSSIMATIVO, non come posizione reale dell’oggetto. Se il POI non ha coordinate normalizzate, non visualizza il tag. Nessuna estrazione automatica di coordinate dai forum.
