# Távoli elérés Windowsról

[English](windows-remote.md) · [SSHFS](sshfs.hu.md) · [HALShow](halshow.hu.md)

A Pi címe `192.168.0.234/24`, a StepperNinjáé `192.168.0.235`. A PC-ről elérhető hálózati út kell a Pi-hez, jellemzően ugyanazon a helyi hálózaton. A leírást a hivatalos dokumentáció alapján ellenőriztük; Windows gépen élő átvételi próba még nem történt.

Böngészőből, SSH-kulcs nélkül is kezelhető a `/data`, ha az opcionális
[igény szerint induló fájlkezelő](file-explorer.hu.md) engedélyezve van.

## Terminál: PowerShell és OpenSSH

PowerShellben:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" root@192.168.0.234
```

Olyan privát kulcsot válassz, amelynek nyilvános párja már engedélyezve van a Pi-n. A képen a jelszavas belépés tiltott. Első belépéskor a gépkulcs ujjlenyomatát egy már megbízható kapcsolaton ellenőrizd, mielőtt elfogadod. A Windowsra az **OpenSSH Client** kell; SSH-szervert nem kell telepíteni. Ha nincs `ssh`, a Windows Beállítások opcionális szolgáltatásai között telepítsd a klienst. [Microsoft: SSH Windows Terminalból](https://learn.microsoft.com/en-us/windows/terminal/tutorials/ssh).

Egy új PC-kulcs önmagában nem ad belépést. Új nyilvános kulcsot a működő kapcsolat megtartása mellett adj a Pi `/data/ssh/authorized_keys` fájljához, a meglévő sorok és jogosultságok megőrzésével. Privát kulcs ne kerüljön a Pi-re. [Microsoft: kulcskezelés](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement).

## Fájlok: WinSCP

1. Új **SFTP** kapcsolat: gép `192.168.0.234`, port `22`, felhasználó `root`.
2. Advanced → SSH → Authentication: válaszd ki a privát kulcsot. OpenSSH kulcsnál a WinSCP felajánlhat PuTTY formátumú átalakítást; az így készült privát kulcs is a PC-n maradjon.
3. Advanced → Environment → SFTP: az SFTP server mezőbe `/data/tools/sftp-server` kerüljön. Ehhez az egyedi szerverhez kapcsold ki az SCP-visszaesést.
4. Ellenőrizd a gépkulcsot és csatlakozz. A DRO helye `/data/apps/eszterga-dro/`, a tartós HAL-bekötés a `machine.hal`, a beállítások a `state/` alatt vannak.

Az SFTP-segéd külön lett telepítve a jelenlegi teszt-Pi-re; régebbi alapképen hiányozhat. SFTP/SSHFS használat előtt ennek rendelkezésre kell állnia. A gyökérfájlrendszer rendszerint csak olvasható, a `/data` írható. Szerkesztés előtt tölts le mentést. Futó alkalmazás fájljait ne írd felül részletekben; a `state/generated.hal` automatikusan újragenerálódik, ezért nem tartós szerkesztési hely.

Források: [WinSCP egyedi SFTP-szerver](https://winscp.net/eng/docs/ui_login_sftp), [WinSCP privát kulcs beállítása](https://winscp.net/eng/docs/ui_login_authentication).

## Az eredeti HALShow WSL2 alatt

WSL2 és WSLg segítségével az eredeti Linuxos Tk HALShow Windows-ablakban jelenhet meg. A Microsoft ehhez Windows 10 build 19044 vagy újabb, illetve Windows 11 rendszert ír elő. WSL1 nem biztosítja ezt a grafikus integrációt. [Microsoft WSL grafikus alkalmazások](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps).

Új telepítéshez rendszergazdai PowerShellben:

```powershell
wsl --install -d Ubuntu
wsl --update
```

Ha kéri, indítsd újra a Windowst. Ezután az Ubuntu termináljában:

```sh
sudo apt update
sudo apt install git python3-tk bwidget openssh-client
```

A Pi SSH-kapcsolatát **a WSL-en belül is** állítsd be, ellenőrzött gépkulccsal. Saját Windowsos privát kulcs átvételekor másold a WSL `~/.ssh/` könyvtárába, és adj neki `600` jogosultságot. Ne közvetlenül a `/mnt/c/` alól használd megengedő NTFS-jogosultságokkal. Jelszóval védett kulcshoz a nézőprogram nem interaktív kapcsolata miatt SSH-agent kell. Előbb az `ssh root@192.168.0.234` belépés működjön WSL-ből.

Szerezd be a ninjaLinux repót a GitHub-hozzáféréseddel (jelenleg privát), majd:

```sh
cd ninjaLinux-zero2w-zero-disp-7a
./components/automation-hal/tools/remote-halshow/run.sh \
  --host 192.168.0.234 --user root \
  --identity "$HOME/.ssh/id_ed25519" --known-hosts "$HOME/.ssh/known_hosts"
```

A Show/Watch kezelését és a korlátokat a külön [HALShow-leírás](halshow.hu.md) magyarázza. Helyi LinuxCNC-telepítés nem szükséges. A GitHub-hozzáférés és a Pi SSH-kulcsa külön jogosultság. A WSL-es SSHFS Linux-oldali csatolás; szokásos Windowsos fájlböngészéshez a WinSCP ajánlott.

## Mit kapsz ezekkel?

Az SSH terminált, az SFTP/SSHFS fájlelérést, a HALShow csak olvasható HAL-diagnosztikát ad. Az EGLFS-képen nincs telepített RDP/VNC asztalszerver; ezek a kapcsolatok nem tükrözik és nem érintik távolról a DRO képernyőjét. Internetes eléréshez külön biztonságos hálózati kapcsolatot, például VPN-t kell kialakítani.
