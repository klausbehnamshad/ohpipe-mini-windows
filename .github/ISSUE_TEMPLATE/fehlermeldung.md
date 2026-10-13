name: Fehlermeldung
description: Ein Problem mit ohpipe-mini-windows melden
title: "[Fehler] "
body:
  - type: input
    attributes:
      label: Windows-Version
      description: z. B. Windows 11 Home 24H2
    validations:
      required: true
  - type: input
    attributes:
      label: Programmversion
      description: Ausgabe von `oh-status`
    validations:
      required: true
  - type: input
    attributes:
      label: Profil
      description: klein, Standard oder Qualität (mit welchem Befehl aufgerufen?)
    validations:
      required: false
  - type: textarea
    attributes:
      label: Bereinigte Fehlermeldung
      description: >-
        Terminalausgabe einfügen, aber vorher Aufnahmeinhalte, Namen und
        Token entfernen. Keine Interviews oder vollständigen Transkripte
        hochladen.
    validations:
      required: true
