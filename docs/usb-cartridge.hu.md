# USB alkalmazás-cartridge

**[English](usb-cartridge.md)**

Opcionális fordítási kiegészítő: a bekapcsoláskor csatlakoztatott pendrive
`autostart.json` fájlja alapján indul az alkalmazás. Ugyanaz az SD-rendszer
használható több külön alkalmazáshoz. Nincs telepítés vagy másolás a rendszerre.

## Rendszerkép készítése

```sh
NINJALINUX_USB_AUTOSTART=1 ./scripts/build.sh rt
# Wi-Fi profilhoz ugyanígy: rt-wifi vagy rt-wifi-ap
```

Az alapértelmezett, addon nélküli fordítás változatlan. A kiegészítő külön
buildkönyvtárat és képfájlt használ: `/tmp/fastlinux-build-usb`,
`artifacts/fastlinux-rt-usb.img.gz`. Eltérő addonbeállításhoz külön
`FASTLINUX_OUT` szükséges. Nem kapcsol be Wi-Fi-t vagy internetmegosztást.

A kapcsoló `BR2_PACKAGE_NINJALINUX_USB_AUTOSTART=y`; a build script a
`board/fastlinux/usb-autostart.fragment` fájlt is hozzáadja. Ez beépített
USB mass-storage/SCSI lemezkezelést és UTF-8 FAT-fájlneveket engedélyez.
Kézi Buildroot-konfiguráláskor a kapcsoló **és** a fragment szükséges.
A meglévő, korábban kiadott SD-kép ettől még nem kapja meg a funkciót:
addonként fordított új rendszerkép kell. A pendrive ezután cserélhető az SD
újraírása nélkül.

## Pendrive előkészítése

FAT32, MBR partíciós táblával ajánlott; ext4 és közvetlenül a teljes
USB-lemezre írt fájlrendszer is kezelhető. exFAT és NTFS nem támogatott.
A FAT32 Windowsból közvetlenül szerkeszthető.

Másold az [examples/usb-cartridge](../examples/usb-cartridge) mappa
**tartalmát** a pendrive gyökerébe:

```text
autostart.json
app/
  main.py
```

A minta teljes képernyős PySide6-feliratot jelenít meg. Saját alkalmazásra
cserélheted, illetve a Designer-eszközök exportját is ide teheted.
Az alkalmazásnak a rendszerben elérhető Python-/Qt-modulokat kell használnia;
a pendrive nem telepít függőségeket.

```json
{
  "version": 1,
  "writable": true,
  "type": "python3",
  "program": "app/main.py",
  "args": [],
  "cwd": "app"
}
```

- `version`: jelenleg `1`.
- `writable`: `true` esetén írható cartridge és azon tárolt beállítások;
  `false` vagy hiányzó mező esetén csak olvasható cartridge, RAM-állapottal.
  A mellékelt minta `true` értéket használ.
- `type`: `python3` vagy `native`.
- `program`: a pendrive gyökeréhez viszonyított programfájl.
- `args`: opcionális szöveges argumentumlista, shell-feldolgozás nélkül.
- `cwd`: opcionális munkakönyvtár, szintén a pendrive gyökeréhez képest;
  alapból `.`. A példában az alkalmazás saját mappájában indul.

Natív programhoz `"type": "native"` és pl. `"program": "app/panel"` kell.
A bináris AArch64 Linuxra, a ninjaLinux könyvtáraival kompatibilisen
készüljön. ext4-en legyen futtatható. A Python-programhoz nem kell futtatási bit.
Az útvonalak nem léphetnek ki a pendrive-ról. A JSON UTF-8 kódolású, BOM nélkül.

## Bekapcsolás és használat

1. Kikapcsolt gépnél dugd be a cartridge-ot. A Zero 2 W egyetlen USB host
   csatlakozóján a kijelző érintése és az Ethernet is osztozhat: megfelelő
   USB hub és tápellátás kell a további pendrive-hoz.
2. Kapcsold be a gépet. Az init egyszer, a felület indítása előtt keres.
   A felismerési ablak 3 másodperc; a fájlrendszerek csatolási próbái ezen
   felül is időt igényelhetnek. A tényleges bootidő még mérendő.
3. Pontosan egy érvényes cartridge esetén annak alkalmazása indul. Ha nincs,
   hibás a leíró/programútvonal, vagy több érvényes cartridge található,
   a szokásos beépített felület indul. Hibás/nem kiválasztott kötetek lecsatolódnak.
4. Későbbi bedugás nem indít programot és nem vált alkalmazást. Cseréhez
   kapcsold ki a gépet. A futó alkalmazás alól ne húzd ki a pendrive-ot.

Felismerés közben minden kötet csak olvasható. A kiválasztott cartridge
`writable: true` esetén újracsatolódik írhatóan (`rw,nodev,nosuid`);
a többi kötetre a kereső nem ír. Az alkalmazás közvetlenül a pendrive-ról fut,
a meglévő EGLFS/KMS környezetet és UI CPU-hozzárendelést használja. Kilépés
vagy összeomlás után a supervisor ugyanazt az alkalmazást indítja újra,
két másodperc várakozással. Hibás alkalmazás kikerülhető cartridge nélküli
indítással. Sikertelen írható csatolás vagy állapotkönyvtár-létrehozás esetén
a beépített alkalmazás indul.

Írható módban a `HOME` a pendrive `.ninjalinux-state` könyvtára; az XDG cache,
config és data ennek `cache`, `config`, `data` alkönyvtára. A szokásos Qt
QSettings/XDG-beállítások így **a cartridge-on maradnak**, nem a belső `/data`
alatt. A program saját, kifejezetten `/data/...` útvonalra írt fájljait ez
nem irányítja át. Az app használjon QSettings-t, XDG-könyvtárakat vagy a saját
cartridge-mappáját. Írható pendrive-ot szabályosan állíts le, mielőtt kihúzod.

`writable: false` esetén a kötet `ro,nodev,nosuid` marad. FAT-on UTF-8
fájlnevekkel, ext4-en napló-visszajátszás nélkül (`noload`); használj tisztán
lecsatolt ext4 kötetet. A HOME/XDG-könyvtárak ilyenkor `/run/ninjalinux-usb-app/home`
alatt RAM-ban vannak és újraindításkor elvesznek. Python egyik módban sem ír
`.pyc` fájlokat. A gyökérpartíció továbbra is csak olvasható, az addon nem
telepít alkalmazást és nem módosítja a belső `/data` konfigurációját. A rendszer
szokásos szolgáltatásai (pl. SSH-kulcsok kezelése) ettől függetlenül működnek.
Ez nem alkalmazás-sandbox: a cartridge a jelenlegi UI felhasználójával,
rootként fut. Saját, megbízható alkalmazás-cartridge-ot használj.

## Elérési út és realtime modulok

A kiválasztott USB-kötet `/data/cartridges/volume-sdX…` alá csatolódik,
nem a belső `/data` tetejére. A vezérlőállapot (`selected.json`, `scanned`)
továbbra is RAM-ban, `/run/ninjalinux-usb-app` alatt van. Az app megkapja a
`NINJALINUX_CARTRIDGE_ROOT` változót a tényleges kötettel; ezt használja,
ne konkrét eszköznevet. A saját `rtlib/` innen is betölthető a támogatott
`--rtlib` opcióval: [realtime modulok](hal-app-modules.hu.md).
A böngészős fájlkezelő a csatolt kötetet is látja. A `writable` beállítás
továbbra is a cartridge készítőjének döntése.

## Diagnosztika és ellenőrzés

SSH-n:

```sh
cat /tmp/usb-app.log
cat /run/ninjalinux-usb-app/selected.json
cat /tmp/fastlinux-ui.log
mount | grep ninjalinux-usb-app
```

A `selected.json` hiánya beépített alkalmazást jelent. A `scanned` jelző csak
az ismételt felismerést akadályozza meg az adott boot során; nem tartós beállítás.
A kereső kizárólag USB mögötti `sd*` blokkeszközökkel foglalkozik, az SD-kártya
partícióit nem keresi cartridge-ként.

Offline tesztek: `python3 -m unittest discover -s tests`. Ellenőrzött a JSON,
útvonalak, shell nélküli argumentumok, egyszeri felismerés, több cartridge
elutasítása, csatolási hibák kezelése, RAM-könyvtárak és indítás. A mount/exec
műveletek a tesztekben helyettesítettek. Buildroot Kconfig-feloldás ellenőrizve;
addon rendszerkép-fordítás, fizikai USB-boot és RT-terhelésmérés még nincs.
