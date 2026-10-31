# Opcionális Wi-Fi fordítás: helyi automatizálási hálózat

[English](wifi.md)

Az alap `rt` változat továbbra is csak Ethernetes. Mindhárom profil PREEMPT_RT
kernelt, VC4/EGLFS grafikát, USB-érintést és azonos IRQ/magizolációs javítást használ.

| Fordítás | Helyi hálózat |
|---|---|
| `./scripts/build.sh rt` | Meglévő Ethernetes, modulmentes alap |
| `./scripts/build.sh rt-wifi` | Beépített rádió kliens módban, WPA2-PSK, DHCP-cím |
| `./scripts/build.sh rt-wifi-ap` | Dedikált WPA2 AP és helyi DHCP távoli kézi vezérlőkhöz |

Az AP-profil hostapd/dnsmasq csomagot kap wpa_supplicant helyett. A kézi vezérlő
parancsprotokollját még nem tartalmazza: annak helyi hálózatát készíti elő.
Internetmegosztás, bridge, NAT, DNS-továbbítás, felhős szolgáltatás és asztali
környezet nem kerül bele. A Wi-Fi kliens DHCP-jéből csak a helyi címet és
alhálózatot vesszük át, átjárót/DNS-t nem. A meglévő Ethernet-beállítás marad.
A Zero 2 W rádiója **2,4 GHz-es**; [Raspberry Pi dokumentáció](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/getting-started/setting-up.adoc).

## Külön build és firmware

Alapértelmezett fordítási könyvtárak: `/tmp/fastlinux-build`,
`/tmp/fastlinux-build-rt-wifi`, `/tmp/fastlinux-build-rt-wifi-ap`; a képek is
külön `artifacts/` alkönyvtárba kerülnek. A `FASTLINUX_OUT` felülbírálásakor
is külön könyvtár kell profilonként. A build elutasítja a keverést: a Buildroot
nem távolít el régi csomagokat egyszerű konfigurációváltásra. Eredmény:
`fastlinux-rt[-wifi[-ap]].img.gz` és ellenőrző összeg.

A Wi-Fi fragment csak a cfg80211, brcmutil és brcmfmac vezeték nélküli
alrendszert kapcsolja modulként. A többi szükséges driver beépítve marad.
A háttérfolyamat a gyökérfájlrendszer felcsatolása után tölti be őket, amikor a
firmware már elérhető. Hálózati konfiguráció nélkül ez a szolgáltatás sem
modult, sem kapcsolódó folyamatot nem indít. A grafikus indulás nem vár
kapcsolódásra vagy DHCP-re. A Bluetooth és a hangkimenet tiltva marad.

A firmware a Buildrootban már rögzített verziójú és hash-ellenőrzött
[LibreELEC-csomagból](https://github.com/LibreELEC/brcmfmac_sdio-firmware-rpi/tree/6596d332eaadd63e2413e3937715a084f61c39e2)
érkezik. Csak a Zero 2 W két rádióváltozatának 43436/43436s fájljai és szükséges
név-aliasai maradnak. A zárt firmware licence a Buildroot `legal-info`
gyűjteményében szerepel; a regulatory adatbázis és a programok saját licencűek.

## Dedikált AP a kézi vezérlőkhöz

Az `rt-wifi-ap` képet használd. Ethernet/SSH kapcsolaton hozz létre egy
700 jogosultságú `/data/wifi` könyvtárat, benne 600 jogosultságú
`hostapd.conf` fájlt. Példa; a hálózatnevet, jelszót és országot állítsd saját értékre:

```ini
interface=wlan0
driver=nl80211
country_code=HU
ieee80211d=1
ssid=ninjaLinux-Control
hw_mode=g
channel=6
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=REPLACE_WITH_YOUR_OWN_PASSWORD
ap_isolate=1
```

A jelszó 8-63 nyomtatható ASCII-karakter legyen. Valódi közös jelszó nem kerül a képbe vagy Gitbe.
AP-módban a `wpa_supplicant.conf` ne legyen aktív. Indítás:

```sh
/etc/init.d/S36wifi start
```

A Pi címe itt **192.168.4.1/24**, a kliensek a **192.168.4.20-192.168.4.100**
tartományból kapnak címet. A DHCP nem hirdet internetátjárót vagy DNS-t;
a dnsmasq DNS-szolgáltatása tiltott (`port=0`). Az alhálózat különbözik az
Ethernet `192.168.0.0/24` hálózatától. Bridge vagy továbbítás nincs beállítva.
A szolgáltatás elutasítja a nyílt vagy bridge-elt AP-konfigurációt.

A vezérlőről/PC-ről/telefonról csatlakozz az SSID-hez, majd a `192.168.4.1`
címhez. Az SSH/HALShow továbbra is a korábbi SSH-kulcsokat igényli: a Wi-Fi
jelszava önmagában nem ad belépést. Telefonon a „nincs internet” jelzésnél
válaszd a hálózaton maradást. A kliensizoláció mellett minden vezérlő eléri
a Pi-t, egymást közvetlenül nem.

Az általános DHCP/DNS indító eltávolításra kerül; a dedikált AP-folyamat indítja
a csak `wlan0`-ra kötött DHCP-t. A folyamatok CPU0-1-re kerülnek. Leállítás/
újraindítás ugyanennek az init scriptnek a `stop`/`restart` paraméterével;
ez megszakítja a Wi-Fi-kliensek kapcsolatát.

## Választható kliensprofil

Ehhez `rt-wifi` fordítás kell. A 700 jogosultságú `/data/wifi` könyvtárba
600 jogosultságú `wpa_supplicant.conf` kerüljön, saját adatokkal:

```ini
ctrl_interface=/run/wpa_supplicant
country=HU
update_config=0
network={
    ssid="YOUR_LOCAL_NETWORK"
    psk="YOUR_OWN_PASSWORD"
    key_mgmt=WPA-PSK
}
```

Ugyanaz az init script indítja. A kapott helyi cím: `ip -4 addr show dev wlan0`.
A fő útvonaltáblában a Wi-Fi alhálózati metrikája 600, így a korábbi Ethernet
útvonalai elsőbbséget élveznek. A 166-os forrásalapú tábla és a 16600-as
szabály gondoskodik arról, hogy a Wi-Fi-címre érkező kérés válasza Wi-Fi-n
menjen ki akkor is, ha a két interfész azonos LAN-on van. Wi-Fi-s alapértelmezett
útvonalat vagy DNS-módosítást nem állítunk be. Ez nem internetes tartalékkapcsolat.
A 166-os tábla/16600-as prioritás ennek a szolgáltatásnak van fenntartva.
Egyszerre csak egy Wi-Fi-konfiguráció legyen aktív; két fájlt az indító elutasít.

## Ellenőrzés és jelenlegi állapot

Napló: `/tmp/wifi.log`. Diagnosztika: `iw dev`, `ip -4 addr show dev wlan0`,
`ip rule`. Kliensállapot: `wpa_cli -i wlan0 status`. AP-bérletek:
`/run/ninjalinux-wifi-ap.leases`.

Offline ellenőrizve: mindhárom Buildroot-konfiguráció feloldása, a rögzített
kernel alap RT- és Wi-Fi-konfigurációja és a profilvalidátor; firmware-archívum
SHA-256; mindkét kártyaváltozat aliasainak épsége a ritkítás után. A tesztek
lefedik a DHCP-útvonalakat, profilok elkülönítését, az AP titkosítás/bridge
ellenőrzését, a csak helyi DHCP-t és a szolgáltatások indítását/leállítását.

**Új Wi-Fi SD-kép és fizikai Wi-Fi/AP/RT mérés még nem készült.** A jelenlegi
Pi/kártya változatlan. Teljes képfordítás, fizikai kapcsolódási/kézivezérlő-hálózati
próba, valamint aktív Wi-Fi-forgalom melletti IRQ- és HAL-időzítésmérés szükséges.
A korábbi Ethernetes késleltetési eredmények nem minősítik a Wi-Fi-s változatot.

Offline regresszió: `python3 tests/test_wifi.py`. Wi-Fi/AP kiadásnál a hozzá tartozó buildkönyvtárral gyűjtsd a licenceket/forrásokat, például: `FASTLINUX_OUT=/tmp/fastlinux-build-rt-wifi-ap ./scripts/collect-legal-info.sh`.
