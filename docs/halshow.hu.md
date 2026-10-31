# Távoli eredeti HALShow

Magyar · [English](halshow.md) · [Windows / WSL](windows-remote.hu.md#az-eredeti-halshow-wsl2-alatt)

A saját LinuxCNC-forrás eredeti Tcl/Tk HALShow-ja, csak olvasó SSH-adapterrel. A grafikus ablak a PC-n fut, és a Pi már működő leválasztott Automation HAL-ját figyeli. Az [SSHFS](sshfs.hu.md) ehhez nem szükséges: a kapcsolat közvetlenül SSH-n megy.

## PC és csatlakozás

Debian/Ubuntu csomagok:

```sh
sudo apt install python3 python3-tk bwidget openssh-client
```

A ninjaLinux repó gyökerében:

```sh
./components/automation-hal/tools/remote-halshow/run.sh
```

A kapcsolati ablakban IP/gépnév, SSH-felhasználó, port, privát kulcs és ismert gépkulcsfájl adható meg. Most: `192.168.0.234`, `root`, `22`. Előbb állítsd be a kulcsos SSH-belépést és ellenőrizd a gépkulcsot. A néző nem kér be SSH-jelszót; jelmondatos kulcshoz futó SSH-agent szükséges.

Közvetlen indítás saját SSH-fájlokkal:

```sh
./components/automation-hal/tools/remote-halshow/run.sh \
  --host 192.168.0.234 --user root --port 22 \
  --identity "$HOME/.ssh/id_ed25519" \
  --known-hosts "$HOME/.ssh/known_hosts"
```

A célgépen szükséges a `/opt/automation-hal/libexec/halshow_agent.py`, a Python 3 és a futó privát `ahal` rendszer. Az agentet a jelenlegi Pi-n 2026. október 31-én ellenőriztük. A frissített Automation HAL telepítése már tartalmazza; az eredeti v0.1.0-rc1 kép korábbi. Friss kártyára előbb az új runtime/agent telepítendő.

## Használat

A fán a komponensek, pinek, paraméterek, jelek, függvények és szálak böngészhetők. A **Show** nézet a kiválasztott objektum adatait mutatja. Válaszd a **Watch** fület, majd kattints a fán egy pin/jel/paraméter konkrét nevére: így kerül a figyelőlistára. Itt változó számértékek és bit-LED-ek láthatók. A keresés/szűrés szűkíti a fát. A mentett figyelőlisták célgépenként a PC-n, az eszköz Gitből kizárt `state/` könyvtárában maradnak.

A parancsmező olvasó lekérdezéseket fogad, például `show pin`, `list pin`, `getp NÉV`, `gets NÉV`. Támogatott: `show`, `list`, `getp`, `gets`, `ptype`, `stype`. Az írás és a komponensek betöltése/újraindítása tiltott. Nem indul második HAL, és a PC helyi LinuxCNC-jéhez sem kapcsolódik.

Az alapfrissítés 500 ms, a szerkezeti metaadatoké 3 s. Rövid impulzus kimaradhat két minta között; ehhez HAL-retesz/számláló/mintavételező kell. Ez állapotnéző, nem oszcilloszkóp és nem késleltetésmérő. Szakadáskor az értékek szürkére/hiányzóra váltanak, az SSH automatikusan újrapróbálkozik.

Az ablak bezárása csak a saját SSH-agent munkamenetet zárja le; az alkalmazás és a HAL tovább fut. Nem kell állandó kiszolgálószolgáltatás vagy új TCP-port.

## Hibakeresés

- **Permission denied:** felhasználó, privát kulcs, hozzá tartozó engedélyezett nyilvános kulcs és SSH-agent ellenőrzése.
- **Host key verification failed:** ujjlenyomat és ismert gépkulcsfájl ellenőrzése; ne kapcsold ki a védelmet.
- **Hiányzó agent:** a friss runtime/agent telepítendő a fenti pontos helyre.
- **Nincs futó saját HAL:** a megfelelő `ahal` felhasználó alatt az alkalmazásnak/HAL-tulajdonosnak már futnia kell.

[Technikai részletek, tesztek, eredeti forrás és GPL-licenc](../components/automation-hal/tools/remote-halshow/README.hu.md).
