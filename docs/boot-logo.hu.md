# Saját bootlogó

**[English](boot-logo.md)**

A PNG/SVG logó a **fordítógépen** alakul át 1024×600 képpé, majd a PSplash
programba épül. A Pi-nek ehhez sem SVG-renderelőre, sem induláskori
képfájl-dekódolásra nincs szüksége. A logó opcionális; az alapértelmezett
kép változatlan marad.

## Fordítás

```sh
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.png" ./scripts/build.sh rt
# SVG-ből ugyanaz:
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.svg" ./scripts/build.sh rt
# USB-cartridge támogatással együtt:
NINJALINUX_USB_AUTOSTART=1 \
NINJALINUX_BOOT_LOGO="$PWD/examples/boot-logo/ninjalinux.png" ./scripts/build.sh rt
```

Saját képhez a változó értéke a saját PNG/SVG elérési útja legyen.
A kapcsoló a `rt-wifi` és `rt-wifi-ap` profilokkal is használható.
A mellékelt minta a felhasználó ninja-szemes vektorlogójának fehér kitöltésű,
fekete hátterű változata. [PNG](../examples/boot-logo/ninjalinux.png) ·
[SVG](../examples/boot-logo/ninjalinux.svg).

A fordítógépen Python 3 és Pillow kell (`python3-pil` Debianon).
SVG-hez `rsvg-convert` (`librsvg2-bin`) vagy ImageMagick is szükséges.
A PNG-változathoz nem kell SVG-renderelő. Az átalakító megőrzi az arányokat,
középre igazít, a maradék területet és az átlátszóságot feketével tölti ki.
A legpontosabb eredményhez készíts eleve 1024×600-as képet; SVG-ben a
feliratokat alakítsd görbévé, ha nem akarsz a fordítógép fontjaitól függni.

A logós változat külön könyvtárba és képfájlba kerül:
`/tmp/fastlinux-build-logo`, `artifacts/fastlinux-rt-logo.img.gz`.
USB-vel együtt a végződés `-usb-logo`. Eltérő addonbeállításhoz külön
`FASTLINUX_OUT` szükséges. Ha ugyanabban a logós buildkönyvtárban megváltozik
a kép, a script újrafordíttatja a PSplash csomagot. A logó megváltoztatásához
új rendszerkép kell; a cartridge-ok által indított alkalmazások ettől
függetlenül cserélhetők.

## Mikor jelenik meg?

A korai userspace init `S12boot-logo` lépése indítja, a framebuffer
(`/dev/fb0`) elérhetősége után, még a Qt/Python alkalmazás előtt.
Ez nem a firmware legelső bekapcsolási képkockája: a kernel és a kijelző
inicializálása előbb megtörténik. Nincs hozzáadott minimális megjelenítési
idő vagy animáció. A Qt indulása előtt a framebuffer-rajzoló leáll.
A pontos megjelenési idő és a KMS/Qt átadás fizikai próbája még hátravan;
folyamatos, villanásmentes átadás nincs hardveren igazolva.

## Hibánál maradjon ki

- Hiányzó, nem olvasható, hibás vagy nem támogatott forráskép esetén a script
  figyelmeztet és **logó nélkül folytatja** a fordítást. A hiányzó host oldali
  konverter is ezt eredményezi. A forráskép legfeljebb 16 MiB lehet;
  az SVG-renderelőre 10 másodperces időkorlát van.
- A kész logó a program része: bootkor nincs külön PNG/SVG fájlolvasás.
- Az init nem várja meg a bootlogó-folyamatot. Framebuffer nélkül a háttérben
  legfeljebb 5 másodpercig próbálkozik, vagy a UI indulásáig.
- Sikertelen rajzolóindításnál egyszerűen kilép. A UI előtti leállítás
  legfeljebb körülbelül 0,3 másodpercig vár; a felület újraindítása nem indítja
  újra a bootlogót. A bootlogó-init minden esetben sikerrel tér vissza.

Ez a hibakezelés a logó hiányát/hibáját kezeli; nem nyomja el a rendszer
más, valódi fordítási hibáit.

## Diagnosztika és ellenőrzés

```sh
cat /tmp/boot-logo.log
ls /run/ninjalinux-boot-logo
```

A logó nem tárol állapotot az SD-n; az ideiglenes állományok `/run` alatt vannak.
A rajzoló `psplash -n`, konzol/VT-váltás nélkül; nincs folyamatjelző vagy
indítási felirat. Az eredeti PSplash GPL-2.0-or-later licence és a Buildroot
forrás-/licencgyűjtése érvényes rá; a saját scriptek a repo licence szerintiek.

Offline ellenőrzés: `python3 -m unittest discover -s tests` (Pillow szükséges).
PNG-méretezés/átlátszóság, SVG-renderelés, hibás/hiányzó kép és a rajzoló
indítás/leállítási versenyhelyzetei tesztelve, valódi framebuffer nélkül.
Buildroot Kconfig-feloldás ellenőrizve. Teljes logós image-fordítás, fizikai
Pi-indítás és RT-időzítésmérés még nincs.
