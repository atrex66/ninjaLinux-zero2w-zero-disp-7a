# ninjaLinux for Zero 2 W and Zero-DISP-7A

Magyar · **[English](README.md)**

[v0.1.0-rc1 letöltése: SD-kép, ellenőrzőösszegek és a hozzá tartozó források](https://github.com/atrex66/ninjaLinux-zero2w-zero-disp-7a/releases/tag/v0.1.0-rc1)

Gyorsan induló PREEMPT_RT Linux Raspberry Pi Zero 2 W és Waveshare
Zero-DISP-7A számára: Python/PySide6 felület, hardveresen gyorsított EGLFS/KMS
grafika, USB érintés és leválasztott LinuxCNC-alapú Automation HAL.

A közös SD-kép fizikai boot-, érintési, SSH-kulcsbeállítási, HAL-funkcionális
és rövid grafikai/Ethernet időzítési próbája sikeres. Ez kiadásra jelölt
változat: másik gépen végzett tiszta fordítás és fizikai mozgásvezérlő I/O
még nincs ellenőrizve.

| [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) | [Waveshare Zero-DISP-7A](https://www.waveshare.com/zero-disp-7a.htm) |
|:---:|:---:|
| <a href="https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/"><img src="https://www.waveshare.net/photo/development-board/Raspberry-Pi-Zero-2-W/Raspberry-Pi-Zero-2-W-details-size.jpg" alt="Raspberry Pi Zero 2 W" width="320"></a> | <a href="https://www.waveshare.com/zero-disp-7a.htm"><img src="https://www.waveshare.net/photo/accBoard/Zero-DISP-7A/Zero-DISP-7A-3.jpg" alt="Waveshare Zero-DISP-7A" width="320"></a> |

Termékfotók: [Waveshare](https://www.waveshare.net/). A képek a beszállító oldaláról töltődnek be.

## Rendszer

| Összetevő | Beállítás |
|---|---|
| Kernel | `6.12.61-ninjalinux-rt-irq1`, kizárólag PREEMPT_RT |
| IRQ-javítás | A BCM2836 ARMCTRL forgatás figyelembe veszi a housekeeping magokat |
| CPU0–1 | Rendszerfolyamatok és eszköz-IRQ-szálak |
| CPU2 | PySide6 grafikus felület |
| CPU3 | HAL; a tényleges RT-szál mért prioritása SCHED_FIFO 98 |
| Grafika | VC4 V3D 2.1, Mesa EGL/GLES, Qt EGLFS/KMS, 1024×600, 60 Hz |
| Szoftver | Buildroot 2026.08.1; Qt/PySide6 6.11.2; Python 3.14.8 |
| Ethernet | USB RTL8152; fix `192.168.0.234/24`; átjáró `192.168.0.1` |
| Tárolás | Csak olvasható root, ideiglenes fájlok RAM-ban, 1 GiB tartós `/data` |
| SD-kép | 1 678 770 176 bájt; tömörítve 65,4 MiB |

Az alap `rt` képen nincs asztali környezet, X11, Wayland, bejelentkezési terminál, Wi-Fi,
Bluetooth vagy hangkimenet. A BusyBox init közvetlenül indítja a felületet;
nincs systemd multi-user target. Az alapprofil szükséges eszközmeghajtói a kernelbe
épülnek. A HAL userspace `.so` komponensei nem kernelmodulok. A VC4 miatt
szükséges ALSA/ASoC alapok megmaradnak, a hangkimenetet a device tree tiltja.

## Mérések — fizikai Zero 2 W, 2026. október 31.

### HAL-periódushiba grafikával és USB/Ethernet-terheléssel

Mindkét próba 1 ms periódusú HAL-szálat használt, CPU3-on, SCHED_FIFO 98
prioritással. Közben folyamatos PySide6/VC4 animáció futott, és 70 MiB adat
ment át az RTL8152 Etherneten/SSH-n, körülbelül 1 MiB/s sebességgel, a mérés
55–125. másodperce között. Az RT-komponens minden ciklust összesít; a végén
a szál röviden leáll a konzisztens hisztogram kiolvasásához, majd újraindul.
A kért megfigyelés 130 s; a leállítóparancs feldolgozásával a teljes ablak
mindkét esetben körülbelül 131 s lett.

| Próba | Ciklusszám | Legnagyobb abszolút periódushiba | Átlagos abszolút periódushiba | ≥2 ms intervallum |
|---|---:|---:|---:|---:|
| Fejlesztői rendszer, javított RT + HAL | 131 023 | 45,677 µs | 1,694 µs | 0 |
| Közös RT + HAL SD-kép, friss indulás után | 131 019 | **37,708 µs** | **1,896 µs** | 0 |

| IRQ-megfigyelés ugyanezekben a próbákban | Fejlesztői rendszer | Közös SD-kép |
|---|---:|---:|
| USB IRQ-növekmény CPU0–1-en | 1 372 008 | 1 371 688 |
| Összes ARMCTRL eszköz-IRQ növekménye CPU2-n | 0 | 0 |
| Összes ARMCTRL eszköz-IRQ növekménye CPU3-on | 0 | 0 |

A tényleges eszköz-IRQ-szálak CPU0–1-en, a GUI CPU2-n, a HAL RT-szála CPU3-on
volt. A bootazonosító és a grafikus folyamat változatlan maradt.
A helyi időzítő, IPI és IRQ-work megmarad: ez nem teljes megszakításmentesség.
A `NO_HZ_FULL` és RCU offload nincs engedélyezve. A housekeeping CPU0–1
magokat működés közben online kell tartani.

[Az SD-kép nyers adatai és jelentése](docs/meresek/2026-10-31-sd-image/report.json)
· [a fejlesztői próba](docs/meresek/2026-10-31-hal-irq/report.json)

### Korábbi cyclictest alapmérés — eltérő metrika

A korábbi, magizoláció nélküli RT-kernelen négy memóriazárolt, SCHED_FIFO 80
cyclictest szál futott 600 s-ig, egyenként 1 ms intervallummal, PySide6 GPU-
animáció mellett. HAL, IRQ-patch és Ethernet-stressz nem futott.
Összesen 2 399 892 ciklus; az összes mag legnagyobb ébresztési késleltetése
**398 µs** volt.

| CPU | Legnagyobb ébresztési késleltetés | Átlagos ébresztési késleltetés |
|---|---:|---:|
| 0 | 398 µs | 14,13 µs |
| 1 | 294 µs | 12,99 µs |
| 2 | 310 µs | 11,47 µs |
| 3 | 360 µs | 11,92 µs |

A HAL abszolút periódushibája és a cyclictest ébresztési késleltetése más
mennyiség. A mérési idő, prioritás és terhelés is eltér, ezért **ezekből nem
számolható közvetlen javulási arány**. A régi mérőprogram nyers `realtime=0`
mezője a hiányzó régi sysfs fájlt használta; a futó kernel saját
konfigurációja és uname kimenete külön igazolta a PREEMPT_RT-t.
[Az alapmérés jelentése](docs/meresek/2026-10-31-rt-baseline/report.json).

### Indulás és működési próbák

- A közös SD-képen az első képkocka **8,02 s kernel-uptime** mellett jelent
  meg. Ez egyetlen boot adata, nem tartalmazza a firmware idejét; nem a
  teljes bekapcsolási idő és nem ismételt bootidő-statisztika.
- A VC4 V3D 2.1 hardveres grafika és az alsó érintési próbagomb működik;
  az érintést a felhasználó a friss SD-képen is visszaigazolta.
- Az első boot saját Ed25519 SSH-hostkulcsot készített, a FAT-partícióról
  importálta a megadott nyilvános adminisztrátori kulcsot; a belépés sikeres.
- A HAL `and2`/`timedelay` szoftveres logikája **FALSE → TRUE → FALSE**
  eredményt adott. A Python-kötés komponenslétrehozási és pinírási/olvasási
  próbája is sikeres.
- A teljes, 1,6 GiB-os tesztképet visszaolvastuk a 2 GB-os kártyáról;
  SHA256 egyezést ellenőriztünk a fizikai indítás előtt.

Ezek rövid szoftveres próbák, nem fizikai CNC-gép elfogadási tesztjei vagy
legrosszabb eseti időzítési garanciák. Hőmérséklet-olvasat nem volt. Tartós
SD-stressz, vezérelt érintési terhelés, hosszú ismételt mérések és a konkrét
I/O ellenőrzése az alkalmazás követelményei alapján további feladat.

## Fordítás

x86_64 Linux gazdagépen:

```sh
bash scripts/fetch-buildroot.sh
bash scripts/build.sh rt
```

Szükséges többek között GCC/G++, make, rsync, bison, flex, CMake, Ninja,
unzip, wget és LLVM19 fejlécek a `/usr/lib/llvm-19` alatt. A szkriptek nem
telepítenek globális csomagot. A Buildroot rögzített forrásokat és Bootlin
ARM64 GCC14.3/glibc toolchaint tölt le. A Boost1.83 fejlécek és Yapps2.2.1
forrásai a `third_party` alatt vannak; nem kell a régi SD vagy a gazdagép
LinuxCNC-telepítése. Másik gépen végzett teljes tiszta build még nem volt.

Az alap munkakönyvtár `/tmp/fastlinux-build`, amely gépújraindításkor eltűnik.
Egy tiszta fordítás nagyobb lehet a 7,8 GiB-os tmpfs-nél; válassz nagyobb helyet:

```sh
FASTLINUX_OUT=/eleg/nagy/mappa bash scripts/build.sh rt
```

Eredmény: `artifacts/fastlinux-rt.img.gz` és a hozzá tartozó SHA256-fájl.
A képen 64 MiB boot-, 512 MiB root- és 1024 MiB adatpartíció van; elfér
az ellenőrzött 2 008 023 040 bájtos kártyán. Egyetlen RT-kernelt tartalmaz.

## Első indulás

1. Írd fel a képet az SD-re; ez lecseréli a kártya tartalmát.
2. Első indulás előtt másold a saját **nyilvános** SSH-kulcsodat a FAT
   bootpartícióra `authorized_keys` néven. Privát kulcsot ne másolj rá.
3. Csatlakoztasd a kijelzőt és az RTL8152 Ethernetet, majd indítsd el a Pi-t.
   A grafikus felület közvetlenül elindul.
4. Belépés: `root@192.168.0.234` a hozzá tartozó kulccsal. Minden kártya
   saját hostkulcsot készít a `/data/ssh` alatt; a kiadási képen nincs közös
   privát hostkulcs vagy beépített fejlesztői adminisztrátori kulcs.

Megadott nyilvános kulcs nélkül a GUI működik, távoli belépés nincs.
Import csak hiányzó `/data/ssh/authorized_keys` esetén történik. Jelszavas
SSH nincs. A DNS alapértéke `84.2.44.8` és `84.2.46.8`; más hálózathoz
állítsd át a hálózati konfigurációt. Tartós fájlokat a `/data` alatt tárolj.

## Leválasztott HAL

Telepítési helye `/opt/automation-hal`, külön `ahal` felhasználóval,
saját IPC-kulcsokkal és runtime-állapottal. Kézzel indul; a GUI jelenleg
grafikai/érintési próba, nem HAL-kezelőfelület.

```sh
ninjalinux-hal start /data/hal/logic.hal
```

Az adminisztrátori indító átadja az RT- és memóriakorlátokat, majd `ahal`
felhasználóra vált. Az RT-szál CPU3-on fut. A parancs előtérben marad;
Ctrl-C leállítja a saját munkamenetét. A példában nincs fizikai mozgáskimenet.

Másik SSH-kapcsolatból:

```sh
su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal cmd show thread'
su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal python'
```

Ellenőrzések és forrásgyűjtés:

```sh
zcat /proc/config.gz | grep '^CONFIG_PREEMPT_RT=y$'
fastlinux-python-check
# A Pi-n, a szoftveres HAL-példa indítása után:
python3 pi-runtime-check.py
# A fordítógépen:
bash scripts/collect-legal-info.sh
```

A célgépi ellenőrző `scripts/pi-runtime-check.py`; futtatás előtt másold a
Pi-re. A `fastlinux-rt-check 10m` az önálló cyclictest receptet futtatja.
A HAL-mérő leállítja/újraindítja a saját szoftveres szálát; fizikai gép
vezérlése közben ez a mérési recept nem futtatható.

## Források és licencek

A saját, önállóan írt build/overlay/próbaprogram MIT licencű.
A LinuxCNC-ből származó Automation HAL vegyes GPL/Library GPL/LGPL feltételű;
a fájlonkénti licencjelölések érvényesek. A késleltetésmérő GPL-2.0-or-later.
A kernelpatchek és egyéb külső kódok megtartják az érintett eredeti kód
licencét. Részletek a kétnyelvű [licencjegyzékben](LICENSES.md).

Az EsztergaDRO külön alkalmazás, nem része ennek a repónak vagy a generikus
SD-képnek. A ninjaLinux nyilvánossá tétele nem teszi nyilvánossá az alkalmazás
privát repóját.
Lásd [LICENSE](LICENSE), [külső források](third_party/README.hu.txt),
[licenc- és forrásgyűjtési leírás](docs/LICENC-ALLAPOT.hu.txt).

A bináris kiadásra jelölt változat mellett generikus SD-kép, SHA256 és a
hozzá tartozó forráscsomag érhető el: Buildroot, alkalmazott patchek,
projektforrás, csomaglicencek és a rögzített GCC/glibc runtime-források.
A személyre szabott tesztkép, SD-mentések, helyi naplók és személyes kulcsok
nem részei a kiadásnak.

## Távoli elérés útmutatói

- [SSHFS: a Pi fájljainak csatolása Linuxról](docs/sshfs.hu.md)
- [Eredeti HALShow: kapcsolódás és az élő Pi HAL figyelése](docs/halshow.hu.md)
- [Windows: PowerShell SSH, WinSCP és WSL2 HALShow](docs/windows-remote.hu.md)

A projekt változásait a [changes.log](changes.log) tartalmazza. Az alkalmazás külön repóban, saját kezelési útmutatókkal készül.

## Választható helyi Wi-Fi / kézivezérlő-AP

Fordításkor választható: `./scripts/build.sh rt-wifi` helyi Wi-Fi klienshez, `./scripts/build.sh rt-wifi-ap` dedikált WPA2 AP-hoz és DHCP-hez távoli kézi vezérlők számára. Az alap `rt` Ethernetes marad. AP-cím: `192.168.4.1`; internetátjáró, DNS-továbbítás, bridge, NAT vagy felhős szolgáltatás nem kerül bele. A kézi vezérlők parancsprotokollja későbbi külön réteg.

[Fordítási profilok, beállítás és ellenőrzési határok](docs/wifi.hu.md). A három Buildroot-profil és a rögzített kernel konfigurációja feloldva; 14 offline teszt és a firmware hash-/aliasellenőrzése sikeres. Új teljes SD-kép és fizikai Wi-Fi/AP/RT próba még nem készült.
