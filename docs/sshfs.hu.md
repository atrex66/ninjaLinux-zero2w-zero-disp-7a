# SSHFS: távoli fájlok Linuxról

Magyar · [English](sshfs.md) · [Windowsos elérés](windows-remote.hu.md)

Az SSHFS a Pi fájlrendszerét helyi könyvtárként csatolja a PC-re. Fájlkezelésre való; az élő HAL-pinek figyeléséhez a külön [HALShow útmutató](halshow.hu.md) tartozik. A két eszköz egymástól függetlenül használható.

## Előfeltételek

A PC-re `sshfs` szükséges (Debian/Ubuntu: `sudo apt install sshfs`), továbbá működő kulcsos SSH-belépés a `root@192.168.0.234:22` címre. Az SD-re előkészített nyilvános kulcshoz tartozó saját privát kulcsot használd; az első belépést a [fő README](../README.hu.md) írja le.

Először sima SSH-val lépj be. Az első kérdésnél megbízható forrás alapján ellenőrizd a gépkulcs ujjlenyomatát:

```sh
ssh -i "$HOME/.ssh/id_ed25519" -o IdentitiesOnly=yes root@192.168.0.234
```

Kilépés: `exit`. A mostani készüléken az SFTP-segéd itt található: `/data/tools/sftp-server`. Ezt külön meg kell adni, mert a minimális SSH-kiszolgáló nem biztosít automatikusan szokásos SFTP-alrendszert.

```sh
ssh -i "$HOME/.ssh/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes root@192.168.0.234 \
  'test -x /data/tools/sftp-server'
```

A segéd meglétét a működő Pi-n 2026. október 31-én ellenőriztük. Külön telepített eszköz: az eredeti **v0.1.0-rc1 SD-kép nem feltétlenül tartalmazza**. Hiánya esetén a célarchitektúrának megfelelő segéd telepítendő; az SSH-belépés önmagában még nem igazolja az SFTP-t.

## Csak olvasható csatolás

Hozz létre üres helyi könyvtárat. A `mountpoint` ellenőrzés után csak akkor csatolj, ha az még nincs használatban; ugyanarra a könyvtárra ne rakj egymásra több csatolást.

```sh
mkdir -p "$HOME/mnt/ninjaLinux"
mountpoint "$HOME/mnt/ninjaLinux"
```

```sh
sshfs root@192.168.0.234:/ "$HOME/mnt/ninjaLinux" \
  -o ro,reconnect,idmap=user \
  -o IdentityFile="$HOME/.ssh/id_ed25519" \
  -o IdentitiesOnly=yes,StrictHostKeyChecking=yes \
  -o ServerAliveInterval=15,ServerAliveCountMax=3 \
  -o sftp_server=/data/tools/sftp-server
```

A PC fájlkezelőjében a `$HOME/mnt/ninjaLinux` könyvtárat nyisd meg. A `/data` tartósan írható terület, a Pi gyökérfájlrendszere normálisan csak olvasható. A fenti `ro` csatolás a `/data` írását is tiltja ezen a nézeten keresztül.

## Leválasztás és hibakeresés

Zárd be a csatolást használó fájlokat és terminálokat, majd:

```sh
fusermount3 -u "$HOME/mnt/ninjaLinux"
```

Régebbi FUSE esetén `fusermount -u` lehet a parancs. Hibánál előbb a sima SSH-t próbáld. A „Subsystem request failed” és az azonnali bontás gyakran hiányzó vagy ki nem választott SFTP-segédre utal. Az üres helyi könyvtár nem igazolja a csatolást; ellenőrizd a `mountpoint`/`findmnt` kimenetét.

Szándékos szerkesztéshez csak az alkalmazás írható könyvtárát csatold, `ro` nélkül. A fájlmentés önmagában nem tölti újra a HAL-t és nem indítja újra az alkalmazást. Privát SSH-kulcs és gépspecifikus futásidejű állapot ne kerüljön Gitbe.

## Csak a DRO írható könyvtárának csatolása

Másik üres csatolási pontot használj. Ez írható fájlelérést ad; előbb készíts mentést, és futó alkalmazást ne írj felül részletekben.

```sh
mkdir -p "$HOME/mnt/EsztergaDRO"
mountpoint "$HOME/mnt/EsztergaDRO"
# Continue only if not mounted / Csak akkor folytasd, ha nincs csatolva.
sshfs root@192.168.0.234:/data/apps/eszterga-dro "$HOME/mnt/EsztergaDRO" \
  -o reconnect,idmap=user,IdentitiesOnly=yes,StrictHostKeyChecking=yes \
  -o IdentityFile="$HOME/.ssh/id_ed25519" \
  -o sftp_server=/data/tools/sftp-server
# Unmount / Leválasztás:
fusermount3 -u "$HOME/mnt/EsztergaDRO"
```
