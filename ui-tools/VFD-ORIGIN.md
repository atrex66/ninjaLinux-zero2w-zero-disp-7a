# VFD appearance and source origin / Megjelenés és forráseredet

The Qt widget adapts the existing local Hunor 721 web simulator's fourteen
segment coordinates, glyph-to-stroke mapping and turquoise appearance from
`Hunor/rp2350/web/index.html`, inspected on 2026-10-31.

Source snapshot SHA-256: `8199116f8a49f80f4fc6a5579241d9a7e6cb2ae5432131538476f314f46a504c`.

The QPainter renderer, scaling, paint cache, Qt properties, numeric formatting,
Designer integration and generic `+`/overflow `#` glyphs are new MIT toolkit
code. The original simulator source was not changed and is not a build/runtime
dependency. No controller, web transport, Arduino or MAX6921 code is imported.

The simulator records an FG209M2 shape reference to
[tehniq3/VFD_FG209M2_2MAX6921](https://github.com/tehniq3/VFD_FG209M2_2MAX6921).
This is retained as visual-reference attribution, not a claim that this widget
implements that controller or the original Hunor character PROM. In particular,
`:` retains the simulator's hourglass-shaped symbol; it is not a normal colon.
The decimal point is independent of the fourteen strokes. A comma with a tail
and selectable numeric decimal separator are new generic toolkit additions.

A Qt-widget a meglévő helyi Hunor 721 webes szimulátor 14 szegmensének
koordinátáit, karakter–szegmens megfeleltetését és türkizzöld megjelenését
veszi alapul. A vizsgált forrás és hash fent szerepel.

A Qt-rajzolás, méretezés, gyorsítótár, tulajdonságok, számformázás és
Designer-integráció új MIT eszközkód. Az eredeti szimulátort nem módosítottuk,
és nem kell a fordításhoz/futáshoz. Vezérlő-, kommunikációs vagy Arduino-kód
nem került át. Az FG209M2-hivatkozás megjelenési referencia; nem bizonyítja
az eredeti Hunor karakter-PROM-mal való teljes egyezést.
A `:` jel a szimulátor homokóra alakú karaktere, a tizedespont külön jelzés.
A szárral rajzolt vessző és a választható tizedeselválasztó új eszközfunkció.
