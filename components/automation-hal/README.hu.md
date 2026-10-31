# Automation HAL

A rögzített CPU-kiosztás indítói és a Pi rendszerbeállításai:
[CPU-LAYOUT.hu.md](CPU-LAYOUT.hu.md) — rendszer CPU0–1, felület CPU2, HAL CPU3.

Önálló automatizálási HAL a LinuxCNC 2.9.10 helyi forrásából kiemelve.
Fordításához és használatához nem szükséges telepített LinuxCNC vagy az eredeti
LinuxCNC-forráskönyvtár. A későbbi NinjaNodeEditor-integráció futtatási alapja;
a node editor és az új Counter node nem része ennek a változatnak.

## Tartalom és állapot

- HAL mag, userspace RTAPI/ULAPI, modulbetöltő és INI-olvasó.
- `halcmd`, `inivar`, `halsampler`, `halstreamer`, saját `ahal` indító.
- 65 lefordított komponensmodul és a `hal_lib.so` magmodul: logikai elemek,
  késleltetők, számlálók, konverterek, PID, watchdog, encoder, stepgen, pwmgen stb.
- C és `.comp` SDK: `halcompile`, fejlécek, `Makefile.modinc`.
- Python 3 `hal`/`_hal` kötés a privát környezetben.
- CMake/CPack build, három `.deb`, Dockerfile és Bubblewrap telepítési teszt.
- Kézzel aktiválható systemd szolgáltatásminta; a csomagtelepítés nem indít HAL-t.

A 0.1.0 csomagokat Debian 13 / amd64 alatt lefordítottam, majd külön Debian
tesztgyökérben tényleges `dpkg --install` telepítéssel ellenőriztem. Mind a 11
integrációs teszt sikeres volt telepítés után, majd eltávolítás és újratelepítés
után ismét. A részletes határokat a [VALIDATION.md](VALIDATION.md) tartalmazza.

Raspberry Pi 4 / DietPi Debian 13 alatt natívan elkészítettem az arm64 csomagokat
is. A Pi-re ezeket nem telepítettem, HAL-t nem indítottam; a valódi PREEMPT_RT
időzítést, fizikai I/O-t és systemd alatti célgépi futást még nem validáltam.
GPIO-, Mesa- és Modbus-meghajtók nem kerültek az első csomagba. Az első változat
headless: nincs Tcl/Tk HAL-felület, grafikus halscope/halmeter vagy shell completion.
A hagyományos `halrun` helyett az `ahal run` kezeli az egész munkamenetet.

## Elkülönítés a telepített LinuxCNC-től

Minden csomagfájl az `/opt/automation-hal` alá települ. Nincs globális
`/usr/bin/halcmd`, `/usr/include/linuxcnc`, Python `hal` vagy LinuxCNC-könyvtár
felülírás. A privát könyvtárak neve `libautomationhal` és `libautomationini`.
A wrapper csak a saját gyermekfolyamata számára állítja be a PATH/PYTHONPATH-ot.

A vezérlősocket `/tmp/automation-hal-UID/control.sock`. A közösmemória-kulcsok
a saját RTAPI-ban `key XOR 0x41480000` leképezést kapnak, a streamer/sampler és
az SDK-val újrafordított külső komponensek esetén is. Leállításkor kizárólag a
saját, ismert, felhasználó által birtokolt és már leválasztott szegmensek törölhetők.
Nincs globális `halrun -U`, `killall`, vagy LinuxCNC-kulcsokra kiadott `ipcrm`.

Az első kiadás egy aktív Automation HAL környezetet támogat egy IPC-névtérben.
A launcher azonos felhasználó második indítását zárral elutasítja. Több külön
felhasználó független párhuzamos példánya nincs támogatva. A LinuxCNC-vel közös
gazdán történő egyidejű fizikai hardverhasználat nincs tesztelve. A jelenlegi
ellenőrzések külön fájlrendszer-, PID-, hálózati és IPC-névtérben történnek.

Külső modulokat ezzel az SDK-val újra kell fordítani. A LinuxCNC bináris
moduljainak és klienskönyvtárainak keverése nem támogatott. Külső modulok saját
extra memóriaszegmenseinek hibakezelése a modul feladata. Már élő HAL-munkamenetben
kézzel végrehajtott parancssorozat nem tranzakció: a korábbi parancsok hatása
megmarad, ha egy későbbi parancs hibázik.

## Csomagok

| Csomag | Tartalom |
|---|---|
| `automation-hal` | Futtatókörnyezet, alapkomponensek, indító, példák |
| `automation-hal-dev` | C/`.comp` fordítóeszköz és fejlécek |
| `python3-automation-hal` | A build Python minor verziójához kötött Python-modul |

A runtime nem függ a fejlesztőcsomagtól vagy a Python HAL-kötéstől. Az indítóhoz
Python >= 3.11 szükséges. A runtime ELF-függőségeit a CPack/dpkg-shlibdeps állítja
elő; nincs LinuxCNC-csomagfüggőség. Az SDK fordítót és `python3-yapps` csomagot kér.
A `.deb` architektúráját a buildkörnyezet adja: amd64 csomagot nem lehet Pi-re tenni.

## Fordítás

Debian buildkörnyezetben szükséges csomagok:

```sh
apt-get install build-essential cmake ninja-build libboost-dev libudev-dev \
    python3-dev python3-yapps dpkg-dev
```

Ez a parancs a kiválasztott buildkonténerbe vagy külön buildrendszerbe való.
Az itt végzett munka során a gazdagép csomagjait nem módosítottam; a hiányzó
Boost-fejléceket `/tmp` alá letöltött `.deb` kibontásából használtam.

```sh
sh tools/build.sh
```

A három csomag a `build/` könyvtárba kerül. Meglévő, más generátorral készült
buildkönyvtár helyett adj új könyvtárat: `sh tools/build.sh build-release`.
A telepítési prefix csomagkiadáskor `/opt/automation-hal`; a példák és tesztek
ezt használják. A build nem futtat HAL-t, és nem telepít a gazdagépre.

Pi-re a cél Debian-verzióval egyező arm64 környezetben, natívan fordíts. Ninja
nélkül a meglévő GNU Make is használható; a Pi-n ezt az utat ellenőriztem:

```sh
cmake -S . -B build-pi -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build-pi --parallel 2
(cd build-pi && cpack)
```

A kész arm64 csomagok a helyi `dist/arm64/` könyvtárban vannak. A
Dockerfile `DEBIAN_RELEASE` argumentuma választható; az egyes Debian/Python/
architektúra kombinációkhoz külön csomag és külön teszt szükséges. A 32 bites
armhf cél nincs még ellenőrizve.

## Docker build és telepítési teszt

```sh
docker build --target test -f packaging/Dockerfile -t automation-hal-test .
docker build --target packages --output type=local,dest=dist \
    -f packaging/Dockerfile .
```

A `test` cél tiszta Debian alapképre telepíti a `.deb` csomagokat, lefordít és
telepít egy saját tesztkomponenst, majd normál felhasználóval futtatja a teszteket.
A `packages` cél önmagában csak buildel és exportál, nem futtatja a `test` célt.
Ne adj a konténernek gazdagépi `/dev`, `/proc`, `/run` kötetet vagy `--ipc=host`
beállítást. A tesztekhez nincs szükség `--privileged` módra.

Docker/Podman ezen a gépen nem volt elérhető, ezért a Dockerfile futtatása még
nincs ellenőrizve. A következő Bubblewrap eljárást ténylegesen végrehajtottam.

## Bubblewrap: teszt Docker nélkül

A hoston `bwrap`, `apt-get`, `dpkg-deb` és Python 3 kell. A parancsok nem
telepítenek hostcsomagot; Debian-archívumokat töltenek le, és saját tesztgyökeret
állítanak össze. A kernelnek engedélyeznie kell a felhasználói névtereket.

```sh
python3 tools/make_test_rootfs.py /tmp/automation-hal-test --download
python3 tools/test_isolated.py /tmp/automation-hal-test/rootfs build
```

A tesztgyökér minimális Debian fixture: a függőségeket archívumból bontja ki,
rögzíti dpkg-metaadataikat, és néhány szokásos alaprendszeri alternatívát
(`sh`, `awk`, `cc`) beállít. Nem bootolható Debian-telepítés, és nem futtatja
a függőségcsomagok teljes maintainer-script életciklusát. Az Automation HAL
csomagok viszont valódi dpkg telepítésen, újratelepítésen és eltávolításon mennek át.

A wrapper a hostot nem csatolja a tesztgyökérbe; csak a három csomagot és a
tesztforrást teszi olvashatóvá. A futási tesztek UID 1000 alatt, eldobott
capabilitykkel, külön hálózati/IPC/PID névtérben futnak. Csak szimulációt mérnek.
A dependency-manifest JSON és az apt-terv a tesztgyökér mellett marad.

## Használat egy tesztrendszeren

Telepítés a kiválasztott, elkülönített tesztrendszerben:

```sh
apt-get install ./automation-hal_0.1.0_*.deb \
    ./automation-hal-dev_0.1.0_*.deb ./python3-automation-hal_0.1.0_*.deb
```

Normál felhasználóval, két terminálból:

```sh
# 1. terminál: előtérben marad; Ctrl+C leállítja a teljes munkamenetet.
/opt/automation-hal/bin/ahal run --mode sim \
    /opt/automation-hal/share/automation-hal/examples/logic.hal

# 2. terminál: ugyanazzal a felhasználóval.
/opt/automation-hal/bin/ahal cmd show pin
/opt/automation-hal/bin/ahal cmd setp and2.0.in0 true
/opt/automation-hal/bin/ahal cmd setp and2.0.in1 true
/opt/automation-hal/bin/ahal cmd getp timedelay.0.out
```

A `sim` mód SCHED_OTHER alatt fut, valós idejű garancia nélkül. A `realtime`
mód PREEMPT_RT-t, működő SCHED_FIFO jogosultságot és memórialockot kér; hiba esetén
kilép, nem vált csendben szimulációra. A realtime ág célgépi mérése még hátravan.
Az `ahal run -i program.ini --mode sim program.hal` INI-helyettesítést is támogat.

A `run` figyeli az RTAPI-folyamatot; konfigurációhiba és futtatókörnyezet-összeomlás
esetén hibával tér vissza. A konfigurációból indított userspace folyamatokat
leállításkor takarítja. Egy már késznek jelzett, külön userspace komponens
későbbi alkalmazásszintű hibájához a programban külön watchdog szükséges.
Ha magát a launchert SIGKILL éri, a hátrahagyott socketet nem törli találomra:
az indítás állapotellenőrzést kér. A systemd minta ezért teljes cgroupot állít le.

## Saját komponensek

```sh
/opt/automation-hal/bin/ahal compile --compile sajat.comp
/opt/automation-hal/bin/ahal compile --compile --userspace sajat.c
/opt/automation-hal/bin/ahal compile --print-modinc
/opt/automation-hal/bin/ahal python sajat_komponens.py
```

A `--install` a saját prefixbe ír, így normál telepítésben adminisztrátori
jogosultság kell hozzá. A futtatás továbbra is normál felhasználóval történik.
Komponensprojektben a Makefile ezt tartalmazhatja:

```make
obj-m += sajat.o
include /opt/automation-hal/share/automation-hal/Makefile.modinc
```

## Systemd célgépen, külön aktiválással

A csomagban lévő minták nem aktiválódnak automatikusan. Először külön felhasználó,
konfiguráció és megfelelő I/O-jogosultságok szükségesek. Egy kiválasztott célgépen
az alábbi lépések készítik elő a szolgáltatást:

```sh
systemd-sysusers /opt/automation-hal/share/automation-hal/systemd/automation-hal.sysusers
install -d /etc/automation-hal
install -m 644 /opt/automation-hal/share/automation-hal/examples/logic.hal \
    /etc/automation-hal/main.hal
install -m 644 /opt/automation-hal/share/automation-hal/systemd/automation-hal.service \
    /etc/systemd/system/automation-hal.service
systemctl daemon-reload
```

Indítás és bootkori engedélyezés csak a célgépi ellenőrzés után történjen.
A minta `LimitRTPRIO=99`, `LimitMEMLOCK=infinity` és `NoNewPrivileges=yes`
beállításokat használ, setuid bináris nélkül. A felügyeleti HAL-klienseket a
szolgáltatás felhasználójaként kell indítani; a közös memória 0600 jogosultságú.

## Eredet és módosítások

A [vendor-manifest.json](vendor-manifest.json) fájlonként rögzíti az átvett
123 fájl SHA-256 értékét és a kiinduló Git-commitot. A `vendor/` a helyi,
módosított LinuxCNC 2.9.10-ből származik, többek között E-HAL/E-RTAPI hibakódokkal.
Az eredeti munkakönyvtárat nem módosítottam.

A standalone adaptációk a [tools/prepare_sources.py](tools/prepare_sources.py)
fájlban vannak, a build külön másolatán alkalmazva. A HAL adatszerkezeteket és
komponensalgoritmusokat nem írtam újra. A módosítások a privát IPC-re,
útvonalakra, explicit futásmódra és a headless parancssori buildre vonatkoznak.

Az átvett fájlok saját licencfejlécei, `vendor/COPYING` és `vendor/COPYING.more`
megmaradtak. Az új build-, indító- és tesztkód GPL-2.0-or-later licencű.
A forrásarchívum az összes buildhez szükséges projektforrást tartalmazza;
a rendszer buildfüggőségeit külön kell biztosítani.
