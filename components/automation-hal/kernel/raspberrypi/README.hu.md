# Raspberry Pi ARMCTRL IRQ-izolációs patch

A patch a Pi Zero 2 W-n megfigyelt problémát célozza: a Raspberry Pi
downstream kernel ARMCTRL megszakításelosztója az izolált CPU2–3-ra is
továbbít perifériás megszakításokat. A módosítás a `HK_TYPE_DOMAIN`
housekeeping maszkot is figyelembe veszi a célmag kiválasztásakor.

**Állapot: teljes kernel és 1910 modul elkészült; a Pi-n a bootpróba és a
háromféle terhelés előtte–utána HAL-mérése sikeresen lefutott.** A patchelt
futásokban CPU2–3-on az ARMCTRL IRQ-növekmény nulla. A periódushiba javult,
de kiugrások maradtak. A részletes eredmények:
[éles teszt és mérés](../../../latency-results/irq-patch-live-20261017/RESULTS.hu.md).
A `6.18.50-ahalirq1` tesztkernel futva maradt; a normál következő boot az eredeti
kernelt választja. [Telepített fájlok és visszaállítás](../../../kernel-tests/ahalirq1/README.hu.md).

## Pontos célverzió

- Gép: Raspberry Pi Zero 2 W; 32 bites userspace, 64 bites RT kernel.
- Futó kernel: `6.18.50+rpt-rpi-v8-rt`.
- Debian csomag: `1:6.18.50-1+rpt1`.
- A telepített kernel changelogjában megadott forráscommit:
  [`cff533aec2fa601846766b32ff57204e0a61bed7`](https://github.com/raspberrypi/linux/commit/cff533aec2fa601846766b32ff57204e0a61bed7).
- Módosított fájl: `drivers/irqchip/irq-bcm2836.c`.
- Forrásának eredeti SHA-256 értéke:
  `526bd57f27e4238bce9be61f2da4b4a6079dc87f16603a067d7e0c32ffeeb32f`.

A vizsgált újabb `rpi-6.18.y` commitban
(`234188315037848e5b07d65b85d38edc64095caa`) a driver és a szükséges
izolációs API forrása azonos volt. A fordítási ellenőrzés a fenti **6.18.50-es**
forrásból készült.

## Működés és határok

A meglévő célgépi beállítás elegendő:

```text
isolcpus=domain,managed_irq,2,3 irqaffinity=0,1
```

A patch szempontjából az `isolcpus=domain,2,3` rész határozza meg a tiltott
magokat. Szükséges a `CONFIG_CPU_ISOLATION=y`; ezt a Pi konfigurációjában
ellenőriztem. A rendszer CPU0–1-en, a felület CPU2-n, a HAL CPU3-on marad.

- A négy hardveres célmagot a jelenlegi cél utáni magtól körben vizsgálja.
  Az aktív, domain housekeeping magok közül választ.
- A jelenlegi célmagot is vizsgálja: ha ez az egyetlen megfelelő mag,
  azon tartja a megszakításokat.
- Ha nincs aktív housekeeping mag, aktív magra esik vissza. Ilyenkor a
  megszakítások kiszolgálása elsőbbséget kap az izolációval szemben.
- Aktív mag hiányában nem írja át a célregisztert.
- A regiszter IRQ-célon kívüli bitjeit, köztük a FIQ-cél bitjeit megőrzi.
- Nem foglal memóriát, nem várakozik és nem naplóz az IRQ-útvonalon.

Ez az ARMCTRL **közös perifériás IRQ-útvonalát** módosítja: az USB mellett
például a kijelző megszakításaira is hat. Nem ad külön IRQ-nkénti
`smp_affinity` támogatást; az `irqaffinity=` önmagában nem vezérli ezt a
patch-et. A `nohz_full` és a cpuset szerinti izolálás önmagában szintén nem
helyettesíti az itt használt domain maszkot. Az ARM lokális timer- és
IPI-megszakításait nem tiltja le.

A szűrés az IRQ-forgató függvény meghívásakor lép működésbe; nem módosítja a
firmware induló IRQ-célját. Nem vezet be új CPU-hotplug migrációs mechanizmust,
és az aktív maszk kiolvasásával egyidejű magleállítást sem szinkronizálja.
A CPU0–1 magokat a HAL futása alatt tartsuk online. A CPU-k leállítását külön
hardverteszttel és szükség esetén további hotplug-javítással kell kezelni.

## Alkalmazás a kernelforrásra

Az alábbi parancsok a fejlesztői gép elérési útját használják. A Pi-n ennek
megfelelője `/home/magor/automation-hal/kernel/raspberrypi`.

```sh
PATCH_DIR=/home/ninja/c64zero/automation-hal/kernel/raspberrypi
KERNEL_SRC=/path/to/linux-cff533aec2fa601846766b32ff57204e0a61bed7

# A bemeneti forrást nem módosító teszt; saját ideiglenes másolaton dolgozik.
python3 "$PATCH_DIR/test_irq_rotation.py" "$KERNEL_SRC"

git -C "$KERNEL_SRC" apply --check \
  "$PATCH_DIR/0001-irqchip-bcm2836-respect-domain-isolation.patch"
git -C "$KERNEL_SRC" apply \
  "$PATCH_DIR/0001-irqchip-bcm2836-respect-domain-isolation.patch"
```

Fordítási ellenőrzés Clang/LLVM 19-cel, a Pi-ről kimásolt konfigurációból:

```sh
KERNEL_BUILD=/path/to/separate-kernel-build
mkdir -p "$KERNEL_BUILD"
cp /path/to/config-6.18.50+rpt-rpi-v8-rt "$KERNEL_BUILD/.config"
make -C "$KERNEL_SRC" O="$KERNEL_BUILD" ARCH=arm64 LLVM=-19 HOSTCC=gcc olddefconfig
make -C "$KERNEL_SRC" O="$KERNEL_BUILD" ARCH=arm64 LLVM=-19 HOSTCC=gcc \
  -j4 drivers/irqchip/irq-bcm2836.o
```

A szükséges host eszközök közé tartozik a make, GCC, Clang/LLVM/LLD 19,
flex, bison, m4 és bc. A helyi ellenőrzés hiányzó eszközeit csak `/tmp` alá
csomagoltam ki; rendszertelepítés nem történt. Az `olddefconfig` a bemeneti
konfigurációt a használt fordítóhoz igazítja; az eltéréseket megőriztem.

Az objektumfájl önmagában nem telepíthető kernelmodul. Aktiváláshoz teljes,
egyedi verziónevű tesztkernelt és a hozzá tartozó modulokat kell készíteni.
Az eredeti kernelt és annak bootbeállításait meg kell őrizni. Az USB-s
Ethernet miatt a bootpróbához előkészített helyi/SD-kártyás visszaállítás kell.
Az [install-test-kernel.py](install-test-kernel.py) a már elkészített egyedi
kernelcsomaghoz külön `tryboot.txt`-t és visszaállító időzítőt készít.
A normál `config.txt`-t nem módosítja, és önállóan nem indít újra.

Forrásbeli visszavonás:

```sh
git -C "$KERNEL_SRC" apply -R --check \
  "$PATCH_DIR/0001-irqchip-bcm2836-respect-domain-isolation.patch"
git -C "$KERNEL_SRC" apply -R \
  "$PATCH_DIR/0001-irqchip-bcm2836-respect-domain-isolation.patch"
```

## Elvégzett ellenőrzések – 2026-10-17

- A patch a pontos célforrásra alkalmazható; a visszavonás bájtra pontosan
  visszaállítja az eredetit.
- A teszt a tényleges C függvényt emeli ki és fordítja le, szimulált
  regiszterrel és aktív/housekeeping maszkokkal.
- 8192 eset izolációval és 8192 eset izoláció nélküli API-viselkedéssel:
  minden négymagos aktív/housekeeping maszk, minden induló célmag és nyolc
  felső regiszterbit-minta. Emellett mindkét módban 128 ismételt IRQ-forgatás.
- A módosítatlan driver a CPU1 → CPU2 izolációs regresszióteszten elbukik;
  a javított átmegy.
- Kernel `checkpatch.pl --no-tree --no-signoff`: 0 hiba, 0 figyelmeztetés.
- A módosított driver ARM64 objektuma sikeresen lefordult, az átvett RT
  konfigurációból, Clang 19.1.7-tel.

Az eredeti forrásellenőrzések eredményei és konfigurációeltérései a
[validation](validation) könyvtárban vannak. Ennek manifestje a telepítés
előtti állapotot rögzíti. A később elvégzett teljes fordítás, bootpróba és
hardveres mérések külön a fenti éles teszt jelentésében szerepelnek.

## A Pi-próba elfogadási feltételei

1. A tesztkernel alatt ellenőrizni kell a kernelverziót, az izolált CPU2–3-at,
   valamint a HAL és a felület tényleges CPU-affinitását.
2. Üresjáratban és USB/Ethernet-terhelés közben a `/proc/interrupts` két
   pillanatképe közti **növekményt** kell vizsgálni. A releváns ARMCTRL IRQ-k
   CPU0–1-en növekedjenek, CPU2–3-on ne. A boot óta összegzett számlálók
   önmagukban nem bizonyítják a patch hibáját vagy sikerét. Az IRQ-sorszámok
   változhatnak; a drivernevek alapján kell azonosítani őket.
3. Ellenőrizni kell az Ethernetet, a kijelzőt, az USB eszközöket, majd amikor
   a felhasználó rendelkezésre áll, a valódi érintéses működést is.
4. Ugyanazzal a HAL-próbával, ciklusidővel, governorral, bemelegítéssel és
   azonos mérési hosszal kell összevetni a javítás előtti és utáni jittert.
   A szokásos mérés közben ne fusson nagy adatforgalmú trace-kiolvasás.
5. Ha az IRQ-izoláció jó, de kiugrások maradnak, azokat külön kell feltárni;
   az eddigi mérés nem bizonyította, hogy minden tüskét ez a mechanizmus okoz.

Előzmény: [kiugrásvizsgálat](../../../latency-results/spike-study-20261017/RESULTS.hu.md)
és [CPU-kiosztás](../../CPU-LAYOUT.hu.md).
