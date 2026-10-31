# Licenses / Licencek

## English

ninjaLinux is a collection of separately licensed components. The root
[MIT license](LICENSE) covers the project's independently authored build
scripts, overlays and demo, excluding third-party-derived code. It does not
relicense Linux, HAL, Qt, firmware or the complete SD image.

| Component | Applicable terms |
|---|---|
| Original standalone ninjaLinux scripts/overlay/demo | MIT; [LICENSE](LICENSE) |
| Linux kernel and its patches | Kernel GPL-2.0-only overall; retain individual file notices and exceptions. Patches follow the modified code's terms. |
| LinuxCNC-derived Automation HAL | Mixed per-file GPL/Library GPL/LGPL; [original notice](components/automation-hal/vendor/COPYING.more), [source hashes](components/automation-hal/vendor-manifest.json) |
| HAL library `hal_lib.c` | GNU Library GPL version 2, as stated in its source header; [full text](LICENSES/LGPL-2.0.txt) |
| HAL/RTAPI interfaces including `rtapi.h` | LGPL version 2.1 where stated; [full text](LICENSES/LGPL-2.1.txt) |
| Other HAL tools/components and original HALShow | Original file headers apply, including GPL v2 or GPL v2-or-later where stated; [GPL v2 text](LICENSES/GPL-2.0.txt) |
| `ninja_latency` measurement component | GPL-2.0-or-later; [source declaration](components/ninja-latency/ninja_latency.comp) |
| Buildroot | GPL-2.0-or-later for Buildroot, with upstream terms for package patches |
| Qt/PySide, Mesa graphics, BusyBox, runtime libraries, firmware and other packages | Each package's license, exceptions and redistribution conditions, recorded by the matching build's legal-info manifests and original notices |
| Copied Boost headers and Yapps sources | Their retained original notices; [dependency provenance](third_party/README.hu.txt) |

[StandaloneHAL](https://github.com/atrex66/StandaloneHAL) is also published
separately. That repository's new packaging license does not replace the
per-file licenses of the HAL snapshot included here.

EsztergaDRO source, binaries and machine configuration are not included in this
repository or the generic ninjaLinux image. It remains a separate project.

### Source and binary releases

Keep original copyright/license notices and identify modifications to upstream
code. For binary distributions, supply the corresponding source, patches and
build/install scripts required by the applicable licenses, together with the
relevant license texts and notices. LGPL and firmware conditions must also be
checked for the exact versions and distribution method; a root MIT file is
not a substitute for these obligations.

Use `scripts/collect-legal-info.sh` and the pinned toolchain-source collection.
See [collection notes](docs/LICENC-ALLAPOT.hu.txt). Buildroot legal-info has
known collection limits: review its README and warnings, the actual release
file list and any externally supplied runtime libraries. Existing versioned
release assets retain their own recorded source commit; this documentation
update does not rebuild or replace those assets.

Primary references: [kernel licensing](https://www.kernel.org/doc/html/latest/process/license-rules.html),
[Buildroot legal-info](https://buildroot.org/downloads/manual/manual.html#legal-info),
[MIT text](https://opensource.org/license/mit).

## Magyar

A ninjaLinux külön licencek alatt álló összetevők gyűjteménye. A gyökérben lévő
[MIT licenc](LICENSE) a saját, önállóan írt buildszkriptekre, overlayre és
demóra vonatkozik, a külső kódból származó részek kivételével. Nem írja felül
a Linux, HAL, Qt, firmware vagy a teljes SD-kép licencfeltételeit.

- **Saját önálló kód:** MIT.
- **Linux kernel és patchek:** a kernel egészére GPL-2.0-only; a fájlonkénti
  feltételek és kivételek megmaradnak. A patch az érintett kód licencét követi.
- **Automation HAL:** fájlonként vegyes GPL/Library GPL/LGPL. A `hal_lib.c`
  GNU Library GPL v2, a `rtapi.h` LGPL v2.1 jelölésű; a többi fájlnál az
  eredeti fejléc dönt. Nem helyes az egész HAL-ra egységes GPL-2.0-or-later
  jelölést alkalmazni. Az eredeti [COPYING.more](components/automation-hal/vendor/COPYING.more)
  és a [forráshashek](components/automation-hal/vendor-manifest.json) megmaradnak.
- **HALShow és más HAL-eszközök:** az eredeti fájlfejlécek szerinti GPL-feltételek.
- **ninja_latency:** GPL-2.0-or-later.
- **Buildroot:** GPL-2.0-or-later, a csomagpatcheknél az érintett eredeti feltételek.
- **Qt/PySide, Mesa grafika, BusyBox, runtime-könyvtárak, firmware és egyéb
  csomagok:** a pontos verzióhoz tartozó saját licencek és továbbadási feltételek.
- **Boost/Yapps:** a megőrzött eredeti jelölések; [forráseredet](third_party/README.hu.txt).

A teljes GPL v2, Library GPL v2 és LGPL v2.1 szöveg a `LICENSES/` könyvtárban
is megtalálható. A külön nyilvános StandaloneHAL repó új csomagolásának licence
nem módosítja az itt található HAL-forrás fájlonkénti feltételeit.

Az EsztergaDRO forrása, binárisa és gépkonfigurációja nem része ennek a repónak
vagy a generikus ninjaLinux-képnek. Az alkalmazás külön projekt marad.

Bináris kiadáskor meg kell őrizni az eredeti jelöléseket, és a vonatkozó
licencek szerint biztosítani kell a megfelelő forrást, patcheket,
fordítási/telepítési szkripteket és licencszövegeket. Az LGPL és a firmware
feltételeit is a tényleges verzió és továbbadási mód alapján kell ellenőrizni.

A `scripts/collect-legal-info.sh` és a rögzített toolchain-forrásgyűjtés segít;
[részletek](docs/LICENC-ALLAPOT.hu.txt). A legal-info README figyelmeztetéseit,
a kiadási fájllistát és a külső runtime-könyvtárakat külön ellenőrizni kell.
A korábbi verziózott kiadások saját forrás-commithoz tartoznak; ez a
dokumentációs módosítás nem fordítja újra és nem cseréli le a csatolmányokat.
