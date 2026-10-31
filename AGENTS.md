# ninjaLinux – rendszerhatár és alkalmazásfejlesztési szabályok

Ez a fájl a teljes repóra és a ninjaLinux célrendszerrel kapcsolatos munkára
vonatkozik. Alkalmazásfejlesztéskor a következő rendszerhatár kötelező.
Az alkönyvtárak útmutatói ezt nem lazíthatják fel. A `ui-tools/AGENTS.md`
a Designer-elemek fejlesztéséhez további részletszabályokat ad.

## Mi ez a rendszer?

- Raspberry Pi Zero 2 W + Waveshare Zero-DISP-7A, 1024×600 kijelző és érintés.
- Buildroot-alapú, gyors indulású, dedikált készülékrendszer; csak PREEMPT_RT
  kernelváltozatok. Nem általános, csomagkezelővel bővítendő desktop Linux.
- A gyökérfájlrendszer csak olvasható. A belső, tartós, írható alkalmazásterület
  a `/data`; a `/run` és `/tmp` ideiglenes, újraindításkor elvesző RAM-terület.
- Python/PySide6, Qt Widgets, hardveresen gyorsított EGLFS/KMS, Mesa VC4.
  A célgépen elérhető Qt-modulok és a PC-s Designer exportkorlátai:
  `ui-tools/profile.json`, `ui-tools/AGENTS.md`, `package/python-pyside6/`.
- A leválasztott, LinuxCNC-alapú Automation HAL a rendszer része, alaphelye
  `/opt/automation-hal`. Ez nem egy teljes LinuxCNC-telepítés.
- A jelenlegi CPU-kiosztás: rendszer/IRQ/hálózat CPU0–1, UI CPU2, HAL CPU3.
  Az IRQ-izoláció, RT-limit, prioritás, watchdog és ütemezés a platform része.
- Az SSH csak karbantartási lehetőség. Publikus adminisztrátori kulcs nélkül
  is indulnia kell a rendszernek és az alkalmazásnak.
- Opcionális, fordításkor választható képességek: helyi Wi-Fi/AP, USB-cartridge,
  saját bootlogó, igény szerint induló böngészős `/data` fájlkezelő.
  Nincs internetes szolgáltatás vagy internetfüggő alkalmazásindítás.
- Az EsztergaDRO külön, privát projekt. Forrását, gépspecifikus konfigurációját,
  binárisát és adatait nem szabad ebbe a nyilvános repóba másolni.

## Kötelező tilalom alkalmazásfejlesztéskor

**Alkalmazásfejlesztés, hibajavítás, függőségpótlás, telepítés vagy tesztelés
miatt a rendszerkomponenseket semmiképpen sem szabad megváltoztatni.**
Az alkalmazásra adott megbízás nem jelent rendszerfejlesztési engedélyt.

Különösen tilos:

- A kernel, firmware, DTB/overlay, bootpartíció, `config.txt`, `cmdline.txt`,
  SD-partíciók, gyökérfájlrendszer vagy rendszerkép módosítása/újraírása.
- A `/boot`, `/etc`, `/usr`, `/bin`, `/sbin`, `/lib`, `/lib64` és a rendszer
  `/opt` komponenseinek módosítása, cseréje vagy ezek alá telepítés.
  Ide tartozik az `/opt/automation-hal` minden fájlja, a HAL mag és SDK is.
- A Qt/PySide, Mesa/EGL/KMS, Python-rendszerkörnyezet, libc, BusyBox,
  SSH, hálózat, rendszerindító/supervisor vagy gépi szolgáltatások átírása.
- CPU-/IRQ-affinitás, RT-prioritás/limit, IPC-kulcstér, felhasználók,
  watchdog, USB-/hálózati driver vagy fizikai I/O-kiosztás átállítása.
- A gyökérpartíció írhatóvá visszacsatolása; overlay/bind mount vagy symlink
  használata a védett rendszerfájlok megkerülésére/elfedésére.
- Globális `pip install`, csomagtelepítés, `ldconfig`, globális PATH,
  PYTHONPATH, LD_LIBRARY_PATH vagy Qt pluginútvonal módosítása.
- A platformforrások (`board/`, `configs/`, `package/`,
  `components/automation-hal/`, rendszerépítő `scripts/`, Buildroot `vendor/`)
  átírása azért, hogy az alkalmazás működjön. Ne legyen ilyen „mellékes javítás”.

Hiányzó platformképesség esetén dokumentáld a konkrét akadályt és az
alkalmazáson belüli lehetőségeket. Ha csak rendszerbővítéssel oldható meg,
azon a részen állj meg: ehhez külön, kifejezett rendszerfejlesztési feladat
szükséges. Ne folytasd rendszermódosítással vagy a fenti tilalmak megkerülésével.
Kifejezetten megrendelt ninjaLinux-platformfejlesztés külön feladatként
kezelendő, nem az alkalmazástelepítés részeként.

## Az alkalmazás teljes egészében a /data alatt legyen

Normál, belső tárolós alkalmazás javasolt helye:

```text
/data/apps/<app>/
  start.sh             alkalmazássaját indító
  bin/                 saját programok, segédfolyamatok
  python/              saját Python-modulok és csomagok
  lib/                 alkalmazássaját, célgéppel kompatibilis könyvtárak
  ui/                  felület/exportált Python-kód
  assets/              képek, ikonok, fontok, fordítások
  hal/                 saját .hal fájlok, loadusr programok, komponensforrások
  rtlib/               saját RT-modulok tárolása; lásd a betöltési korlátot alább
  config/              alkalmazássaját konfiguráció
  state/               tartós állapot, szerszámtábla stb.
  cache/
  logs/
  src/                 ha a forrás is a készüléken szükséges
  licenses/            továbbadott függőségek licencfájljai
  README.md
  AGENTS.md            alkalmazássaját fejlesztési szabályok
```

Minden saját bináris, modul, asset, függőség, konfiguráció és tartós állapot
maradjon az alkalmazás könyvtárában. A már telepített rendszerkönyvtárakat
használhatja változtatás nélkül; az „önálló alkalmazás” nem jelenti a libc,
Qt vagy HAL mag lemásolásának/cseréjének szükségességét.

- Az indító csak saját gyermekfolyamatának állítsa be a szükséges környezetet.
  HOME/XDG könyvtárait is az alkalmazáshoz tartozó `/data` könyvtárakra irányítsa.
  Ne módosítsa a shellprofilokat vagy a rendszer indítószkriptjét.
- Natív kód AArch64, az adott ninjaLinux toolchain/ABI szerint készüljön.
  Egy tetszőleges Debian/armhf/amd64 csomag nem helyettesíti ezt.
- Python natív bővítményhez a cél Python-verziója/ABI-ja is számít. Hiányzó
  függőséget a PC-n/cross-buildben csomagolj az app mellé; ne a célgépen pótold
  a globális Pythonba. Qt Designer/QtUiTools nem feltétele a célgépi futásnak.
- `/tmp/<app>-…` és `/run/<app>/…` csak átmeneti socket/PID/zár/ideiglenes
  fájl helye lehet. Ide ne kerüljön telepített appkomponens vagy tartós adat.
- Csak az alkalmazás saját fájljain változtass tulajdonost/jogosultságot.
  A HAL-t futtató `ahal` felhasználónak a szükséges app/HAL könyvtárakhoz
  célzott olvasási/belépési jog kell. Ne használj `chmod 777`-et vagy a teljes
  `/data` tulajdonosának rekurzív átállítását.
- Az alkalmazás saját konfigurációja módosítható; egy másik app állapotát,
  `/data/ssh` kulcsait vagy platformkonfigurációt ne írd át mellékhatásként.
- Az app adjon saját indítót. Automatikus indításhoz csak a ténylegesen létező,
  dokumentált platformfelületet használd. Ha a jelenlegi indító nem támogatja
  a kívánt appválasztást, ne patcheld meg: jelezd külön platformigényként.

## HAL-komponensek: mi tölthető a /data alól?

### HAL-konfiguráció és userspace komponens: igen

A `ninjalinux-hal start /data/apps/<app>/hal/main.hal` egy saját konfigurációt
indíthat a meglévő runtime-mal, `ahal` felhasználóként. Ezt csak kifejezetten
engedélyezett indításkor szabad végrehajtani; egy futó gépi HAL-t ne állíts le.
A `.hal` fájlok, `source`-olt részek és gépi konfigurációk lehetnek `/data` alatt.
A beépített alapértelmezett konfiguráció a `/data/hal/logic.hal`.

A saját `loadusr` program/binary/Python-kód szintén lehet az app könyvtárában.
Példa egy már engedélyezett HAL-konfiguráció részletére:

```hal
# A program tényleges komponensneve legyen my_app_bridge, és jelezzen ready-t.
loadusr -Wn my_app_bridge /opt/automation-hal/bin/ahal python /data/apps/my-app/hal/my_app_bridge.py
```

A read-only rendszerwrapper itt változtatás nélkül használt függőség; a saját
program a `/data` alatt marad. A kliens a futó HAL-t birtokló felhasználó/IPC
környezetét használja. Egy userspace Python-folyamat nem válik realtime
komponenssé attól, hogy HAL-pineket ad. A realtime időzítést igénylő feladatot
nem szabad észrevétlenül GUI/Python ciklusra áttenni.

### Saját realtime .so modul: igen, explicit --rtlib könyvtárral

A kiegészített platform támogatja az alkalmazássaját RTAPI `.so` modulokat.
A régi kiadott image-eknél ezt ne feltételezd automatikusan. A modul az adott
ninjaLinux SDK-val és AArch64 toolchainnel készüljön, a megfelelő ABI/IPC szerint;
a `halcompile --compile` kimenetét másold az app saját `rtlib/` könyvtárába.
Ne használd a rendszerprefixbe telepítő `halcompile --install` parancsot.

```sh
ninjalinux-hal start /data/apps/my-app/hal/main.hal \
  --rtlib /data/apps/my-app/rtlib
```

A `.hal` fájlban `loadrt my_component`, nem teljes fájlútvonal szerepel.
A `--rtlib` ismételhető. A rendszer meglévő moduljai mindig elsőbbséget
élveznek, `hal_lib` csak rendszerből jöhet. Saját modul legyen közönséges
fájl, ne symlink; a modulnévben `/` és `..` tiltott. A launcher kizárólag az
explicit könyvtárakból állít elő belső keresési útvonalat, az örököltet törli.
A könyvtárak a munkamenet indításakor rögzülnek. A saját `.so` nem kernelmodul.

Ez a támogatás nem engedély az `/opt/automation-hal` vagy bármely más
rendszerkomponens átírására. Ne másold a saját modult rendszermappába,
ne hozz létre oda symlinket, ne cseréld le a betöltőt az app kedvéért.
Másik RT-binary hibáját se kezeld rendszerfile-cserével. Részletek és
ellenőrzési határok: `docs/hal-app-modules.hu.md`.

## USB-cartridge a /data alatt

A cartridge a `/data/cartridges/<kötet>` alá csatolódik: nem fedi el a belső
`/data` tartalmát. Az app összes saját komponense a pendrive-on maradhat,
beleértve a `rtlib/` könyvtárat is. Az app használja a
`NINJALINUX_CARTRIDGE_ROOT` változót, ne égessen be `sdX` eszköznevet.

A készítő az `autostart.json` fájlban adja meg a `writable` értéket.
Írható módban HOME/XDG az USB-n lévő `.ninjalinux-state` alatt marad;
csak olvasható módban RAM-ba kerül. A RT-modulok betöltéséhez elég az olvasás.
Ne irányítsd át a cartridge tartós állapotát a belső SD-re a készítő kifejezett
döntése nélkül. Részletek: `docs/usb-cartridge.hu.md`.

A felismerés nem indít automatikusan HAL-t. A saját app indítója a meglévő
`ninjalinux-hal start ... --rtlib ...` felületet használhatja, megfelelő
engedélyezés mellett; ne állítson le vagy cseréljen le másik élő HAL-t.

## Ellenőrzés és átadás

Először PC-n, offscreen vagy eldobható, izolált környezetben tesztelj.
A host/Pi LinuxCNC/HAL IPC-jét, élő gépi munkamenetét és I/O-ját ne használd
próbaterületnek. Célgépi telepítésnél a változó fájlok listája kizárólag
alkalmazássaját `/data` útvonalakat tartalmazhat; a cartridge-tárolás szabálya fent van.
A futó HAL, alkalmazás vagy készülék leállítása/újraindítása nem automatikus
része egy forrásmódosításnak. Bootloop vagy káros regresszió után ne próbálkozz
újabb telepítéssel/firmware-rel; egyeztetett helyreállítási feladat kell.

Az átadás írja le: mi változott az appban, hova kerül, mivel ellenőrizted,
és mi nincs célgépen igazolva. A PC-s siker nem fizikai I/O- vagy RT-bizonyíték.
Ne commitolj kulcsot, tokent, gépi állapotot vagy privát alkalmazásforrást.
A README-k és a `changes.log` következetesen különböztessék meg a forrást,
a lefordított image-et és a valóban telepített/kipróbált állapotot.
