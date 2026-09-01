# Witzeseiten für WordPress

## Der Weg vom Rohmaterial zur Seite

    "1 Lager witze"            Rohmaterial: Satzpaare in einer Zeile, ohne Nummern,
                               ohne Aufklappboxen
        |  tools/lager_aufbereiten.py
        v
    lager-aufbereitet.txt      Wiki-Format wie witze01.txt ... witze17.txt
        |  tools/seiten_aufteilen.py
        v
    witze18.txt ... witze23.txt
        |  tools/wiki2wp.py
        v
    wordpress/witzeNN-v01.txt      <- das kommt in den WordPress-Code-Editor
    wordpress/witzeNN-v01.meta.json <- Titel, Permalink, Übergeordnet, Reihenfolge
        |  tools/wp_preview.py
        v
    vorschau/witzeNN-v01.html      <- im Browser ansehen

## Alles neu bauen

    python3 tools/lager_aufbereiten.py "1 Lager witze" lager-aufbereitet.txt lager-pruefbericht.txt 261
    python3 tools/seiten_aufteilen.py lager-aufbereitet.txt 18 6
    for n in $(seq -w 1 23); do
      python3 tools/wiki2wp.py "witze${n}.txt" "wordpress/witze${n}-v01.txt" "${n#0}"
      python3 tools/wp_preview.py "wordpress/witze${n}-v01.txt" "vorschau/witze${n}-v01.html"
    done

## Was beim Einfügen in WordPress von Hand zu tun ist

Der Seitencode enthält den Inhalt. Titel, Permalink und "Übergeordnet" speichert
WordPress getrennt davon; sie stehen in der .meta.json und müssen in der
Seitenleiste eingetragen werden - oder später vom Upload-Programm über die
REST-API (`POST /wp-json/wp/v2/pages` mit `parent`).

## Seitennummern verschieben

Die Nummer steuert Titel, Permalink und beide Navigationslinks. Sie wird
`wiki2wp.py` als drittes Argument übergeben - eine andere Zahl, und die ganze
Seite hängt woanders.
