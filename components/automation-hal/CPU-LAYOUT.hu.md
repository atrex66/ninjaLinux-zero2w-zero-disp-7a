# Rögzített CPU-kiosztás Raspberry Pi-n

A magok Linux alatt nullától számozódnak. Az egyeztetett négy magos profil:

| Feladat | Linux CPU | Fizikai sorszám |
|---|---|---|
| Rendszer, háttérszolgáltatások | 0–1 | első és második |
| MagorAutomate / NinjaNodeEditor felület | 2 | harmadik |
| HAL, ciklikus szálak | 3 | negyedik |

A közös fájl: `/etc/automation-hal/cpu-layout.json`. Forrásmintája:
[packaging/cpu-layout.json](packaging/cpu-layout.json). Mindkét felület ugyanazt a
profilt olvassa; a HAL `ahal run` indítója szintén. A fájl jelenlétekor a meglévő
indítóparancsok automatikusan használják. Ha a kért mag offline, a konfiguráció
hibás vagy a cgroup nem engedi az affinitást, az indítás megáll. Nincs másik
magra való csendes átváltás. A HAL indítója az `RTAPI_CPU_NUMBER` értékét is
beállítja, így a LinuxCNC-ből átvett automatikus CPU-választás nem írja felül.

A HAL folyamat, a felügyelő és a belőlük indított feladatok CPU3-at örökölnek.
A felületek és szálaik CPU2-t örökölnek. A systemd szolgáltatásoknál az
`AllowedCPUs` cgroup-korlát a szálak későbbi affinitásmódosítását is behatárolja.
Közvetlen szkriptindításnál az affinitás ellenőrzött, de külön cgroup-korlát nincs.
A két felület egyidejű futtatása ugyanazt a CPU2-t osztja meg; EGLFS esetén a
kijelzőt egyszerre csak egy felület használja.

## Indítás

Telepített profilnál a szokásos indítók elegendők:

```sh
~/start-automation-hal.sh
~/start-ninja-node-editor.sh
~/MagorAutomate/run.sh
```

A már futó HAL mellé ne indíts második HAL-munkamenetet. A MagorAutomate HAL
systemd szolgáltatásának neve `magorautomate-hal.service`, a felületé
`magorautomate.service`.

Profil nélküli fejlesztői környezetben kifejezetten választható:

```sh
./NinjaNodeEditor/run-pinned.sh --windowed
./NinjaNodeEditor/run-pinned.sh --eglfs
/opt/automation-hal/bin/ahal run --mode sim \
  --cpu-config /útvonal/cpu-layout.json /útvonal/program.hal
```

A `run-pinned.sh` a telepített profilt, aztán a csomag mintáját, végül a szomszédos
`automation-hal/packaging` mintáját keresi. Más telepítési helyen az
`AUTOMATION_CPU_CONFIG` és `AUTOMATION_CPU_HELPER` változóval adható meg a profil
és a közös Python-helper. A profil csak telepített fájl vagy explicit indító
esetén aktív; egy kétmagos fejlesztői gépen a normál indítás továbbra is használható.

## Tartós rendszerbeállítás

A célgépen a terv megtekintése, majd alkalmazása:

```sh
python3 ~/automation-hal/tools/install_cpu_layout.py
sudo python3 ~/automation-hal/tools/install_cpu_layout.py --apply
```

Az eszköz Raspberry Pi-t, csatolt `/boot/firmware` kötetet, elérhető magokat,
telepített Automation HAL-t és cgroup v2 cpuset támogatást ellenőriz. Mentést
készít `/var/backups/automation-hal/cpu-layout-*` alá. A HAL Python-indítóját és
a CPU-helpert telepíti; HAL binárist, alkalmazásprogramot, I/O-bekötést nem cserél.
Nem módosít csomagadatbázist, nem indít szolgáltatást és nem rebootol.

A rendszerprofil:

- systemd `[Manager] CPUAffinity=0 1`: a rendszerfolyamatok indulási alapértéke;
- HAL: `CPUAffinity=3`, `AllowedCPUs=3`, `RTAPI_CPU_NUMBER=3`;
- MagorAutomate GUI: `CPUAffinity=2`, `AllowedCPUs=2`;
- kernel: `isolcpus=domain,managed_irq,2,3 irqaffinity=0,1`;
- irqbalance esetén a CPU2–3 tiltólistára kerül.

A bootparaméterek és a rendszer egészének indulási alapértéke **újraindítás után**
érvényesül. Az `isolcpus` a szokásos ütemezéstől különíti el a magokat; a
maghoz kötött kernelmunkák, IPI-k és egyes hardvermegszakítások ettől még ott
futhatnak. Ez nem jelent teljes megszakításmentességet vagy garantált jittert.
Más szolgáltatás saját, explicit CPU-beállítása felülírhatja a rendszer
alapértékét. A nagyobb biztonságot a HAL/GUI saját cpuset-korlátja adja.

A megoldás nem módosítja a ciklusidőt vagy az RT prioritást. A CPU2/CPU3 felosztás
saját mérés nélkül nem bizonyít alacsonyabb késleltetést.

## Ellenőrzés és visszaállítás

```sh
systemctl show magorautomate-hal.service magorautomate.service \
  -p MainPID -p CPUAffinity -p AllowedCPUs -p ControlGroup
cat /sys/devices/system/cpu/isolated
cat /proc/cmdline
```

A tényleges folyamat **minden szálát** a `/proc/PID/task/*/status` fájlok
`Cpus_allowed_list` mezőjén ellenőrizd; a `ps` aktuális CPU-ja önmagában nem bizonyít
rögzítést. A szolgáltatás cgroupjának `cpuset.cpus.effective` fájlja mutatja a
kernel által kikényszerített korlátot.

```sh
sudo python3 ~/automation-hal/tools/install_cpu_layout.py \
  --restore /var/backups/automation-hal/cpu-layout-PONTOS_MENTES
```

A visszaállítás a mentett rendszerfájlokat állítja helyre; utána újraindítás kell.
A forrásbeli indítók a profil eltávolítása után a korábbi, kötetlen működésre
váltanak. A CMake-csomag újrafordítva tartalmazza az új CPU-helpert; a korábban
elkészült `.deb` fájlok nem frissülnek automatikusan.

Források: [systemd CPU- és cpuset-szabályok](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml),
[kernel izolációs paraméterek](https://docs.kernel.org/admin-guide/kernel-parameters.html),
[irqbalance CPU-tiltólista](https://github.com/Irqbalance/irqbalance/blob/master/irqbalance.1).

## Célgépi ellenőrzés – 2026-10-17

A `magor@192.168.0.171` Pi Zero 2 W-n (Raspbian 13 armhf userspace,
6.18.50+rpt-rpi-v8-rt aarch64 PREEMPT_RT kernel) telepítve és újraindítás után
ellenőrizve:

- `/sys/devices/system/cpu/isolated`: `2-3`;
- PID 1 affinitás: `0-1`, IRQ alapmaszk: `3` (hex, azaz CPU0–1);
- HAL szolgáltatás effektív cpuset: `3`; mind a négy megfigyelt szál CPU3;
- a HAL ciklikus szála SCHED_FIFO alatt fut;
- MagorAutomate effektív cpuset: `2`; mind az öt megfigyelt GUI-szál CPU2;
- az egyéb megfigyelt userspace folyamatok főszálai CPU0–1-en voltak;
- mindkét szolgáltatás aktív; a kilenc CPU-konfigurációs teszt PC-n és Pi-n is sikeres.

Részletes mérési pillanatkép: `~/installation-logs/cpu-layout-after-boot.json`.
A rendszerfájlok visszaállítási mentése:
`/var/backups/automation-hal/cpu-layout-20261017-140033-770492`.
A forrásindítók korábbi változatai: `~/installation-backups/cpu-layout-source-20261017`.
A futó HAL program a meglévő, hardverkimenetek nélküli demó maradt. Ezek az
ellenőrzések affinitást és ütemezési módot bizonyítanak, nem fizikai mozgást vagy
új terheléses jittereredményt.

### Utólag mért IRQ-korlát a Pi Zero 2 W-n

A 2026-10-17-i kernelnyomkövetésben USB/perifériás IRQ-k CPU3-on is futottak,
miközben az USB IRQ-k kért affinitása CPU0–1 volt. A HAL/GUI cpuset továbbra is
érvényes; ez önmagában nem szigeteli el a hardveres megszakításoktól a HAL magját.
A Raspberry Pi kernelág BCM2836 IRQ-kódja az aktív magok között forgatja a
perifériás IRQ-kat. A teljes mérés, az ideiglenes performance és érintőpaneles
próba, valamint a visszaállítás bizonyítékai:
[kiugrásvizsgálat](../latency-results/spike-study-20261017/RESULTS.hu.md).

Ehhez elkészült a [BCM2836 IRQ-izolációs kernelpatch](kernel/raspberrypi/README.hu.md),
amely az IRQ-forgatáskor figyelembe veszi az `isolcpus=domain` maszkot.
A teljes kernel és moduljai elkészültek, a `6.18.50-ahalirq1` tesztkernel
éles Pi-próbája sikeres. Automatikus órajellel, fix 1 GHz-en és hálózati
terhelés mellett is nulla volt az ARMCTRL IRQ-növekmény CPU2–3-on.
A periódushiba javult, de nem minden kiugrás szűnt meg.
[Részletes előtte–utána mérés](../latency-results/irq-patch-live-20261017/RESULTS.hu.md).
A tesztkernel futva maradt; az eredeti bootkonfiguráció megmaradt,
normál újraindításkor az eredeti kernel indul.
