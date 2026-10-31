A 64 GB-os Raspbian SD /home/magor/NinjaLatency projektjéből változatlanul
átvett ninja_latency.comp és COPYING. Licenc: GPL-2.0-or-later.
Az eredeti SD-t nem módosítottuk. Az ARM64 modult a saját HAL SDK-val
fordítjuk: bash scripts/build-latency.sh (előtte scripts/build-hal.sh).

A komponens minden HAL-ciklus periódushibáját összesíti. Nem azonos a
cyclictest ébresztési késleltetésével. A hisztogram 2 us széles rekeszeket
használ; az utolsó rekesz minden >=254 us abszolút hibát tartalmaz.
A konzisztens végső kiolvasáshoz a szoftveres próbaszál röviden leáll,
majd újraindul. Fizikai gépvezérlés közben ez a mérési recept nem futtatható.
