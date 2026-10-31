ninjaLinux for Zero 2 W and Zero-DISP-7A

Ez a kiadási kép kizárólag PREEMPT_RT kernelt tartalmaz, a BCM2836 ARMCTRL
IRQ-forgatás javításával. CPU0-1: rendszer/eszköz-IRQ, CPU2: PySide6 GUI,
CPU3: manuálisan indítható önálló LinuxCNC HAL. A timer/IPI helyi marad.
Nincs asztali környezet, bejelentkezési terminál, hang, Wi-Fi vagy Bluetooth.
A PySide6 próbafelület EGLFS/KMS és VC4 OpenGL ES gyorsítást használ.

Ethernet: 192.168.0.234/24, átjáró 192.168.0.1.
SSH előkészítése az első indítás ELŐTT:
1. A saját SSH NYILVÁNOS kulcsodat másold a FAT bootpartíció gyökerébe
   authorized_keys néven. Privát kulcsot soha ne másolj a kártyára.
2. Indítsd el a Pi-t. Gépenként saját hostkulcs keletkezik a /data/ssh alatt.
3. Belépés: root@192.168.0.234, kizárólag a megadott kulccsal.
Kulcs nélkül a grafikus felület működik, távoli belépés nincs.
Az authorized_keys importálása csak akkor történik, ha /data/ssh alatt
még nincs ilyen fájl. A rendszerpartíció csak olvasható, /data tartós.

HAL szoftveres példa indítása SSH-ból (nem indul automatikusan):
  ninjalinux-hal start /data/hal/logic.hal
A HAL külön ahal felhasználóval, SCHED_FIFO módban, CPU3-on fut.
A parancs előtérben marad; Ctrl-C leállítja a saját HAL-munkamenetet.
Másik SSH-kapcsolatból parancsok és Python-kötés:
  su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal cmd show thread'
  su -p -s /bin/sh ahal -c '/opt/automation-hal/bin/ahal python'
Fizikai I/O nincs engedélyezve a példában.

RT ellenőrzés: zcat /proc/config.gz | grep '^CONFIG_PREEMPT_RT=y$'
Önálló cyclictest: fastlinux-rt-check 10m
Python ellenőrzés: fastlinux-python-check
A szoftveres HAL-próba eredménye nem fizikai CNC-gép elfogadási tesztje.
