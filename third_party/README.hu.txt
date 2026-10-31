Fordítási forrásfüggőségek, az eredeti 64 GB-os Raspbian SD-ről másolva:

boost/boost-headers-1.83.0.tar.gz: /usr/include/boost teljes könyvtár,
változatlan fájltartalmakkal, normalizált tar metaadatokkal. A fordításnak
csak a fejlécek kellenek. Verzió: boost/version.hpp; SHA256: SHA256SUMS.
Az eredeti csomag licencnyilvántartása: boost/COPYRIGHT (BSL-1.0 és a
fájlonként felsorolt kivételek). A fejlécek saját szerzői megjegyzései
megmaradtak. Ez a forráscsomag a projekt része, nem gépfüggő cache.

yapps/yapps/*.py: /usr/lib/python3/dist-packages/yapps öt Python-forrása,
2.2.1 verzió. A Debian csomag MIT licencszövege: yapps/COPYRIGHT.
A helyi build ezeket használja; a gazdagép Python-környezetét nem módosítja.
