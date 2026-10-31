# Saját realtime HAL-modul a /data vagy a cartridge alól

**[English](hal-app-modules.md)**

Ez a támogatás a kiegészített ninjaLinux-platform része. Az alkalmazás ezután
saját modulokat adhat hozzá a rendszerfájlok módosítása nélkül. Korábbi kiadott
image-en nem szabad meglévőnek feltételezni: az új betöltővel fordított image
szükséges. A futó Pi most nem kapott frissítést.

## Telepítési hely

Belső tárolós alkalmazásnál:

```text
/data/apps/my-app/
  hal/main.hal
  rtlib/my_component.so
  lib/                 saját függőségek, ha szükséges
```

A bootkor megtalált USB-cartridge most `/data/cartridges/volume-sdX…` alá
csatolódik, nem a belső `/data` tetejére. A saját `rtlib` a pendrive-on marad.
Az app megkapja a `NINJALINUX_CARTRIDGE_ROOT` környezeti változót; a kötet nevét
ne égesd a programba. A HAL-nak nem kell írnia a modul könyvtárát, ezért
`writable: false` cartridge-ról is betölthető saját RT-modul.

## Fordítás és másolás

A modul **userspace RTAPI `.so`**, nem Linux-kernel `.ko`. A ninjaLinuxhoz
illeszkedő StandaloneHAL/Automation HAL SDK-val kell fordítani: cél AArch64,
megfelelő libc/ABI és a saját HAL IPC-változtatásai. Egy szokásos LinuxCNC-ből
vagy más architektúrára készült bináris nem helyettesíti ezt.

Fejlesztői SDK-környezetben a `halcompile --compile` készítse el a fájlt;
a Pi rendszerébe fordítóeszközt nem kell telepíteni. A PC-s natív SDK x86-64
modult ad, nem Pi-re valót: a célképhez tartozó cross-toolchain/SDK szükséges.

A kész csomagból csak az alkalmazás saját könyvtárába másolj:

```sh
mkdir -p /data/apps/my-app/rtlib
cp my_component.so /data/apps/my-app/rtlib/my_component.so
chmod 644 /data/apps/my-app/rtlib/my_component.so
```

Ez a modul telepítése: nincs `/opt`-ba másolás, root-remount, `ldconfig` vagy
rendszerszintű `halcompile --install`. Cartridge esetén a fájlt már a PC-n
elhelyezheted a pendrive `rtlib/` könyvtárában. A HAL-t futtató `ahal` usernek
olvasnia kell a fájlt és be kell tudnia lépni az odavezető könyvtárakba.
Egyedi dinamikus függőség legyen az app saját `lib/` könyvtárában, megfelelő,
csomagoláskor kialakított relatív RPATH-pal; ne írd át a rendszer könyvtárait.

## Betöltés

A saját `.hal` fájlban a megszokott **modulnév** szerepel, `.so` és útvonal nélkül:

```hal
loadrt my_component count=1
# A modul saját függvényeinek addf/net/... bekötése ezután következik.
```

Az app indítója adja meg a modulok könyvtárát a munkamenet létrehozásakor:

```sh
ninjalinux-hal start /data/apps/my-app/hal/main.hal \
  --rtlib /data/apps/my-app/rtlib
```

Cartridge-on, az alkalmazás saját indítójában:

```sh
ninjalinux-hal start "$NINJALINUX_CARTRIDGE_ROOT/hal/main.hal" \
  --rtlib "$NINJALINUX_CARTRIDGE_ROOT/rtlib"
```

A `--rtlib` ismételhető, a sorrend a saját könyvtárak közötti keresési sorrend.
A könyvtáraknak már létezniük kell, abszolút útvonalon, `:` nélkül; az image
admin-indítója csak `/data` alá feloldódó könyvtárat fogad el. A rendszeres
`ninjalinux-hal start` további opció nélkül változatlanul működik.
A generic `ahal run` ugyanezt a `--rtlib` opciót támogatja, a megfelelő,
nem root HAL-felhasználó és RT-limitek környezetében.

Ne indíts második HAL-t egy élő munkamenet mellé. A könyvtárlista az adott
munkamenet indításakor rögzül; egy későbbi `ahal cmd` környezete nem módosítja.
A cartridge felismerése nem indít automatikusan HAL-t és nem tölt be modulokat;
ezt az alkalmazás saját, engedélyezett indítása végzi.

## Rendszermodulok védelme

1. Mindig a rendszer `/opt/automation-hal/rtlib` könyvtára az első.
2. Csak onnan hiányzó névhez keresi a megadott appkönyvtárakat.
3. Meglévő, de hibás rendszermodulnál is hiba lesz, nem appverzióra váltás.
4. A `hal_lib` magmodul kizárólag a rendszerből jöhet.
5. Saját `.so`-nak közönséges fájlnak kell lennie: modul-symlinket, FIFO-t és
   eszközfájlt nem követ a betöltő. A modulnévben `/` és `..` továbbra is tiltott.

A launcher csak az explicit `--rtlib` listából állít elő belső
`AHAL_RTLIB_PATH` változót; egy örökölt globális értéket töröl.
A régi `HAL_RTMOD_DIR` nem ennek a támogatásnak a kapcsolója.
Ez alkalmazássaját kódbetöltés, nem sandbox vagy automatikus kódellenőrzés.
Saját névvel készíts modult; ne próbálj rendszerkomponenst felülírni.

A pendrive maradjon csatlakoztatva a teljes munkamenet alatt. Módosítás és
csere előtt a saját alkalmazás/HAL szabályos leállítása szükséges; nincs
észrevétlen hot reload. A webes fájlkezelő a `/data/cartridges` alatti kötetet
is látja; írhatóságát továbbra is a cartridge `writable` beállítása dönti el.

## Ellenőrzés

A natív PC-s HAL és SDK teljes fordítása után, csak staging fájlokra telepítve:

```sh
sh components/automation-hal/tools/test_app_modules.sh \
  /tmp/ninja-hal-module-stage/opt/automation-hal
```

A teszt új tmpfs gyökérben, külön fájlrendszer/PID/IPC/hálózati névtérben
fordít és betölt egy valódi saját RTAPI-modult `/data/cartridges` alól.
Ellenőrzi a ciklikusan növekvő pint, a rendszer elsőbbségét, az explicit
könyvtárakat és a tiltott útvonal/symlink eseteket. A host/Pi HAL-jához nem nyúl.
Ez **sim ütemezési módú PC-teszt**, nem fizikai PREEMPT_RT időzítésmérés.
A teljes Pi-image újrafordítása, valódi USB-mount és célgépi RT/I/O-próba még
hátravan. Az egységtesztek a gyökér `tests/test_hal_app_modules.py` fájlban vannak.
