# Helyi ellenőrzés – 2026-10-16

A projektet Debian 13 / amd64 környezetben, GCC 14 és Python 3.13 használatával
fordítottam. A hiányzó Boost-fejléceket külön `/tmp` könyvtárba bontottam ki;
a gazdagép csomagadatbázisát nem módosítottam.

## Végrehajtott ellenőrzések

- Önálló CMake-build a másolt forrásfából; nincs buildhivatkozás az eredeti
  LinuxCNC-forráskönyvtárra és nincs LinuxCNC-könyvtár linkelése.
- Három CPack `.deb`: runtime, SDK, Python-kötés.
- A runtime önmagában, SDK és Python HAL-kötés nélkül is futtatja a logikai példát.
- Valódi `dpkg --install` egy külön Debian-archívumokból összeállított gyökérben.
- A gyökér nem tartalmaz LinuxCNC-csomagot vagy globálisan importálható `hal` modult.
- Bubblewrap: külön mount/user/PID/IPC/network névtér, a működési tesztek UID 1000
  alatt, capabilityk nélkül futottak.
- Mind a 11 alábbi teszt sikeres volt, majd az azonos verzió újratelepítése,
  eltávolítása és friss telepítése után ismét mind a 11 sikeres volt.

| Teszt | Ellenőrzött viselkedés |
|---|---|
| 01 | Nincs LinuxCNC runtime-függőség; az ELF-függőségek feloldhatók |
| 02 | 1 ms-ra beállított szál, AND és késleltető működése, hibás jelösszekötés elutasítása |
| 03 | Python-komponens létrehozása, pinérték és eltávolítás |
| 04 | Saját `.comp` fordítása/betöltése/futása, C userspace komponens fordítása/futása |
| 05 | INI-paraméter behelyettesítése a HAL-konfigurációba |
| 06 | Második tulajdonos elutasítása, rendezett leállás és újraindítás |
| 07 | Hibás konfiguráció utáni takarítás és újraindítás |
| 08 | RTAPI-folyamat SIGKILL hibájának jelzése és következő indítás |
| 09 | Jogosultság nélküli realtime mód hibával leáll, nincs sim fallback |
| 10 | Betöltés közben várakozó userspace folyamat megszakítása és takarítása |
| 11 | Az eredeti LinuxCNC IPC-kulcsokon létrehozott kontrollszegmensek érintetlenek maradnak |

Az 1 ms itt beállított periódust és funkcionális viselkedést jelent, nem mért
valós idejű pontosságot. A tesztgyökér függőségei archívumból kibontott fixture-k;
ez nem egy teljesen bootolt Debian rendszer tesztje.

## Natív Raspberry Pi / arm64 fordítás – 2026-10-16

A Raspberry Pi 4 Model B Rev 1.5 gépen, DietPi / Debian 13, Python 3.13
környezetben natívan lefordítottam a projektet, és elkészítettem mindhárom
`arm64` `.deb` csomagot. A Pi meglévő fordítóját és fejléceit használtam;
buildfüggőséget sem kellett telepítenem. A build GNU Make generátorral és két
párhuzamos fordítási feladattal futott, Release konfigurációban.

Távoli buildkönyvtár: `/home/dietpi/automation-hal-builds/0.1.0-arm64.ZKf7Vx`.
A csomagok és a naplók helyi másolata: `dist/arm64/`.
Mind a 74 különálló ELF-állomány AArch64, a dinamikus könyvtárfüggőségek a
kibontott csomag saját könyvtáraival feloldhatók. Nincs `liblinuxcnc` függőség;
minden csomagfájl a saját `/opt/automation-hal` prefix alatt van.
A Pi csomagadatbázisának SHA-256 értéke változatlan maradt, a telepített LinuxCNC
továbbra is `1:2.9.10+magor1`. A csomagokat csak külön ellenőrzési könyvtárba
bontottam ki; ez nem telepítés. A fent felsorolt 11 működési teszt továbbra is
az amd64-es izolált környezet eredménye, nem Pi-n elvégzett futási teszt.

## Még nem ellenőrzött

- Raspberry Pi / arm64 csomagtelepítés és funkcionális HAL-futás.
- armhf fordítás és telepítés.
- PREEMPT_RT-n pozitív realtime-indítás, ütemezési késleltetés és jitter.
- Fizikai GPIO, Mesa, Modbus, StepperNinja vagy más I/O.
- Systemd szolgáltatás tényleges célgépi indítása és bootkori működése.
- Dockerfile buildje; ezen a gépen Bubblewrap volt elérhető.
- LinuxCNC és Automation HAL egyidejű, közös hardvert használó futása.
- Különböző kiadások közötti csomag- és ABI-migráció; most azonos verziót
  telepítettem újra.

Az elkészült amd64 `.deb` csomagok a PC-s izolált teszt artefaktumai, nem Pi-re
telepíthető csomagok. A Pi-hez külön arm64 csomagok készültek. A gazdagépre
és a Pi-re nem telepítettem ezt a HAL-t.
