# Távoli eredeti HALShow

A saját LinuxCNC 2.9.10 forrásában lévő eredeti Tcl/Tk HALShow, SSH-s adatkapcsolattal. A `vendor/bin/halshow.tcl` és a `cbutton.tcl` változatlan másolat; a távoli HAL-parancsot a külön kapcsolati réteg biztosítja. A helyi LinuxCNC-telepítést nem módosítja és annak HAL-jához nem kapcsolódik.

## Indítás a PC-n

```sh
./run.sh
```

A megjelenő ablakban a HAL-t futtató Pi címe `192.168.0.234`, az SSH-felhasználó jelenleg `root`. A megszokott SSH-kulcsot és ellenőrzött gépkulcsot használja. A kapcsolathoz működő kulcsos SSH-bejelentkezés szükséges; ismeretlen gépkulcsot nem fogad el automatikusan.

Közvetlen indítás:

```sh
./run.sh --host 192.168.0.234
```

Más géphez az `--identity` és `--known-hosts` kapcsolókkal is megadhatók a kulcsfájlok. A PC-n Python 3, Tk (`python3-tk`), BWidget (`bwidget`) és OpenSSH kliens szükséges. Teljes LinuxCNC telepítése nem szükséges a PC-re.

## Pi oldali kapcsolat

A saját HAL-csomag telepíti a `remote_agent.py` fájlt ide:

`/opt/automation-hal/libexec/halshow_agent.py`

A jelenlegi Pi-re már telepítve van. A segéd csak az SSH-munkamenet idejére fut, `ahal` felhasználóra vált, és a 0–1. rendszerprocesszorokon dolgozik. A privát HAL-hoz tartozó `halcmd show` parancsokat használja. Nem indul új HAL, nem módosít pineket vagy összekötéseket, és nem nyit további hálózati portot. A HAL és a DRO újraindítása nem szükséges.

## Megjelenítés

Az eredeti komponens-/pin-/paraméter-/jel-/függvény-/szálfa, Show és Watch nézet, keresés és menthető figyelőlista használható. A figyelőlista és a beállítások célgépenként külön, a helyi `state/` könyvtárban maradnak.

A kapcsolat csak olvasó: `show`, `list`, `getp`, `gets`, `ptype`, `stype`. Az íróparancsok tiltottak, a Watch nézet írókezelői nem jelennek meg. Megszakadáskor az élő értékek szürkére/hiányzóra váltanak, az SSH-kapcsolat automatikusan újrapróbálkozik.

Az alapmintavételezés 500 ms, a szerkezeti metaadatok frissítése 3 s. Ez állapotfigyelő; rövid impulzusok megfigyeléséhez HAL-számláló, tároló/latch vagy mintavételező szükséges.

## Ellenőrzés

```sh
python3 tests/test_model.py
python3 tests/live_connection.py
./run.sh --host 192.168.0.234 --smoke --report /tmp/remote-halshow-report.json
```

Az utolsó két próba a már futó Pi saját HAL-ját olvassa. A kapcsolatpróba kizárólag a saját SSH-kliensét szakítja meg. A HAL-t, a DRO-t és a kimeneteket nem módosítja.

A LinuxCNC HALShow GPL-2.0 licencét és az eredeti szerzői fejléceket megőriztük. Forrás és ellenőrzőösszegek: `provenance.json`.
