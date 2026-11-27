# FitTrack

FitTrack je študentski projekt pri predmetu SUA za načrtovanje treningov, beleženje obrokov in telesnih meritev ter spremljanje osebnih ciljev. React frontend dostopa do šestih mikrostoritev prek API Gatewaya.

**Stanje Naloge 2:** razvoj se začenja. Ta README določa načrt, API pogodbe in predvideni lokalni zagon. Ukazi za zagon aplikacije bodo izvedljivi, ko bodo storitve in `compose.yaml` pripravljeni.

[GitHub Issues](https://github.com/delimanchev/FitTrack/issues) · [Kanban za Nalogo 2](https://github.com/users/AnjaTodorov/projects/7/views/1)

## Ekipa in razvojni obseg

| Mikrostoritev | Kaj upravlja | Odgovorna oseba | Ogrodje | Baza PostgreSQL | Issue |
| --- | --- | --- | --- | --- | --- |
| User | Račune, prijavo, JWT in uporabniške nastavitve | Andrej Delimanchev (`@delimanchev`) | ASP.NET Core Web API | `user_db` | [#3](https://github.com/delimanchev/FitTrack/issues/3) |
| Exercise | Katalog vaj in mišičnih skupin | Andrej | ASP.NET Core Web API | `exercise_db` | [#5](https://github.com/delimanchev/FitTrack/issues/5) |
| Workout | Načrtovanje, izvedbo in zgodovino treningov | Andrej | ASP.NET Core Web API | `workout_db` | [#4](https://github.com/delimanchev/FitTrack/issues/4) |
| Nutrition | Obroke, sestavine, kalorije in makrohranila | Anastasija Todorov (`@AnjaTodorov`) | FastAPI | `nutrition_db` | [#7](https://github.com/delimanchev/FitTrack/issues/7) |
| Progress | Telesno težo, obsege in zgodovino meritev | Anastasija | NestJS | `progress_db` | [#6](https://github.com/delimanchev/FitTrack/issues/6) |
| Goals | Osebne cilje, nastavitve opomnikov in izračun napredka | Anastasija | FastAPI | `goals_db` | [#8](https://github.com/delimanchev/FitTrack/issues/8) |

Andrej pripravi tudi Docker Compose, YARP (ASP.NET Core) in osnovo React + Vite s prijavo ter treningi. Anastasija pripravi preostale zaslone in vodi integracijsko testiranje. Oba pregledata pogodbe, prispevata k frontendu in izvedeta demonstracijo.

[Uskladitev API pogodb](https://github.com/delimanchev/FitTrack/issues/1) · [Priprava Docker Compose](https://github.com/delimanchev/FitTrack/issues/2) · [Konfiguracija API Gatewaya](https://github.com/delimanchev/FitTrack/issues/9) · [Priprava frontenda za prijavo in treninge](https://github.com/delimanchev/FitTrack/issues/10) · [Priprava zaslonov za prehrano, napredek in cilje](https://github.com/delimanchev/FitTrack/issues/12) · [Preverjanje REST pogodb in klicev](https://github.com/delimanchev/FitTrack/issues/11) · [Priprava demonstracije in preverjanje pogojev oddaje](https://github.com/delimanchev/FitTrack/issues/13)

Naloga 1 je za zaledje predvidela ASP.NET Core. Za zahtevo Naloge 2 po treh ogrodjih načrt zaledja uporablja ASP.NET Core, FastAPI in NestJS. Razširjene API pogodbe in dodatne povezave so opisane spodaj.

## REST API

Frontend kliče poti `/api/*` prek gatewaya. V tabeli so poti za gateway in mikrostoritev enake. Vsaka vrstica vsebuje dve različni operaciji vsake zahtevane metode. `{id}` označuje identifikator glavnega vira ustrezne storitve.

| Storitev | GET × 2 | POST × 2 | PUT × 2 | DELETE × 2 |
| --- | --- | --- | --- | --- |
| User | `/api/users/me`<br>`/api/users/me/preferences` | `/api/auth/register`<br>`/api/auth/login` | `/api/users/me`<br>`/api/users/me/preferences` | `/api/users/me`<br>`/api/users/me/preferences` |
| Exercise | `/api/exercises`<br>`/api/exercises/{id}` | `/api/exercises`<br>`/api/muscle-groups` | `/api/exercises/{id}`<br>`/api/muscle-groups/{groupId}` | `/api/exercises/{id}`<br>`/api/muscle-groups/{groupId}` |
| Workout | `/api/workouts`<br>`/api/workouts/{id}` | `/api/workouts`<br>`/api/workouts/{id}/exercises` | `/api/workouts/{id}`<br>`/api/workouts/{id}/exercises/{itemId}` | `/api/workouts/{id}`<br>`/api/workouts/{id}/exercises/{itemId}` |
| Nutrition | `/api/meals?date=…`<br>`/api/meals/{id}` | `/api/meals`<br>`/api/meals/{id}/items` | `/api/meals/{id}`<br>`/api/meals/{id}/items/{itemId}` | `/api/meals/{id}`<br>`/api/meals/{id}/items/{itemId}` |
| Progress | `/api/progress`<br>`/api/progress/latest` | `/api/progress`<br>`/api/progress/body-measurements` | `/api/progress/{id}`<br>`/api/progress/body-measurements/{measurementId}` | `/api/progress/{id}`<br>`/api/progress/body-measurements/{measurementId}` |
| Goals | `/api/goals`<br>`/api/goals/{id}/status` | `/api/goals`<br>`/api/goals/{id}/reminders` | `/api/goals/{id}`<br>`/api/goals/{id}/reminders/{reminderId}` | `/api/goals/{id}`<br>`/api/goals/{id}/reminders/{reminderId}` |

- Ohrani `PATCH /api/users/me`, `PATCH /api/workouts/{id}`, `PATCH /api/meals/{id}` in `PATCH /api/goals/{id}` iz Naloge 1. `PUT` zamenja celoten zapis, na katerega kaže pot. Za zaključek treninga uporabi `PATCH /api/workouts/{id}`.
- Za izbiro, vnos in pregled dodanih virov predvidi še `GET /api/muscle-groups` in `GET /api/progress/body-measurements`. Podrobnosti treninga oziroma obroka vrnejo tudi postavke. Seznam ciljev vsebuje nastavitve opomnikov. Cilji hranijo nastavitve opomnikov v lastni bazi.
- Izbris uporabniških nastavitev ponastavi profil na privzete nastavitve. Izbris zapisa z lastnimi podrejenimi postavkami odstrani tudi te postavke v isti transakciji. Izbris mišične skupine, ki jo uporablja vaja, vrne `409`.
- Uporabi `201` pri ustvarjanju, `200` za branje, prijavo in posodobitve ter `204` ob uspešnem brisanju. Obravnavaj `400` za neveljavne podatke, `401` za manjkajočo ali neveljavno prijavo, `403` za nedovoljen dostop, `404` za manjkajoč vir, `409` za konflikt in `503` za nedosegljivo odvisnost.
- Javna registracija ustvari vlogo `USER`. Za spremembe kataloga je potrebna vloga `ADMIN`. Storitve preverijo podpis, izdajatelja, občinstvo, rok veljavnosti JWT in pravice. Za lastne podatke uporabijo `sub` iz JWT. Dodaj lokalni način priprave testnega administratorja prek okoljske konfiguracije.

### Klici med storitvami

Interni klici uporabljajo imena storitev v omrežju Compose in spodnje poti brez predpone `/api`. Klicatelj pošlje storitveno poverilnico, prejemnik pa preveri identiteto in dovoljenje klicatelja. Pri uporabniških poizvedbah se posreduje tudi podatek o uporabniku, pridobljen iz preverjene identitete uporabnika. Gateway usmerja javne poti, interne obravnave pa berejo lastno bazo brez povratnega klica.

| Klicatelj → prejemnik | Interna zahteva | Kdaj se izvede |
| --- | --- | --- |
| Workout → Exercise | `GET /exercises/{exerciseId}` | Pri dodajanju ali zamenjavi vaje v treningu |
| Nutrition → User | `GET /users/{userId}` | Pri vnosu obroka |
| Progress → User | `GET /users/{userId}` | Pri vnosu meritve |
| Goals → Progress | `GET /progress/latest` | Pri izračunu napredka proti ciljni teži |
| Goals → Workout | `GET /workouts/completed?from=…&to=…` | Pri izračunu tedenskega števila zaključenih treningov |
| User → Nutrition | `GET /meals/summary?date=…` | `GET /api/users/me/overview` prikaže število današnjih obrokov |
| Exercise → Progress | `GET /progress/latest` | `GET /api/exercises/{id}/energy-estimate?minutes=…` oceni porabo energije glede na MET, trajanje in težo |
| Workout → Progress | `GET /progress/latest` | Ob zaključku treninga se shrani zadnja teža, če obstaja |

Zadnje tri povezave dopolnjujejo Nalogo 1. Tako vsaka od šestih storitev sama pokliče vsaj eno storitev, ki jo razvija drugi član. Za HTTP klice nastavi časovno omejitev. Manjkajoča meritev je veljaven primer. Workout zaključi trening brez teže, Goals prikaže status brez podatka o teži, Exercise za oceno porabe vrne `404`. Ob izpadu nujne odvisnosti vrni `503` in prepreči delni zapis.

## Navodila za razvijalce

### Prvi koraki

1. V Kanbanu prevzemi dodeljeno nalogo in jo premakni iz **Todo** v **In Progress**. Skupaj najprej uskladita strukturo zahtev in odgovorov, primere napak, storitveno avtentikacijo ter meje tedenskega intervala in časovni pas.
2. Namesti Git ter Docker Desktop ali Docker Engine z vtičnikom Compose. Za razvoj zunaj Dockerja namesti .NET SDK za User, Exercise, Workout in gateway, Python za Nutrition in Goals ter Node.js z npm za Progress in frontend. Različice zakleni v projektnih datotekah in Docker slikah.
3. Kloniraj repozitorij. Pred spremembami ustvari vejo iz `main`. V PR dodaj `Closes #<številka>` in prosi drugega člana za pregled pogodb ter lokalnega zagona.

```powershell
git clone https://github.com/delimanchev/FitTrack.git
cd FitTrack
git switch -c feat/goals
```

### Predvidena struktura in lokalni zagon

```text
frontend/            React + Vite
gateway/             YARP
services/            user/, exercise/, workout/, nutrition/, progress/, goals/
openapi/             pogodbe ali izvozi med razvojem po potrebi
tests/               ponovljivi integracijski preizkusi
docs/                dodatni razvojni in demonstracijski zapiski
.env.example         vzorec lokalne konfiguracije
compose.yaml         storitve, baze, omrežje in trajna hramba
```

Ko bosta pripravljena `.env.example` in Compose, nastavi lokalne vrednosti v `.env` za podatkovne baze, ključe za JWT, storitvene poverilnice in objavljena vrata. V Compose konfiguraciji naj ima vsaka mikrostoritev svojo bazo PostgreSQL, svojega uporabnika baze in lastne migracije. Objavi vrata frontenda in gatewaya. Podatkovne baze in servisna vrata naj ostanejo v omrežju Compose.

```powershell
Copy-Item .env.example .env
# Izpolni lokalne vrednosti v .env.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f goals
# Ko končaš z delom, ustavi okolje in ohrani podatke.
docker compose down
```

Predvideni lokalni vstopni točki sta frontend na `http://localhost:5173` in gateway na `http://localhost:8080`. Vsaka storitev neposredno izpostavi `GET /openapi.json` na svojem internem HTTP vmesniku. Preveri ga iz Compose omrežja ali prek začasne lokalne preslikave vrat. V specifikaciji opiši sheme, avtentikacijo in primere napak. Preveri, da se dokumentacija ujema z dejansko implementacijo.

### Pogoji za zaključek storitve

- [ ] Delujejo vsaj 2 GET, 2 POST, 2 PUT in 2 DELETE po matriki. Preizkušena sta tudi napačen vhod in nedovoljen dostop.
- [ ] Storitev uporablja svojo bazo PostgreSQL, migracije in omejeno število povezav. Filtriranje in strani pri večjih seznamih se izvedeta v bazi.
- [ ] Storitev ima lasten Dockerfile in `.dockerignore`. Slika uporablja primerno majhno osnovo ali večstopenjsko gradnjo in vsebuje izvajalne odvisnosti.
- [ ] Delujeta lasten `/openapi.json` in najmanj en neposreden klic storitve drugega člana. Preizkušeni so uspeh, dovoljenja in odziv na izpad.
- [ ] Zagon iz svežega klona in predvideni primer sta potrjena s Compose. Pred premikom v **Done** drugi član pregleda PR, koda pa je združena.

## Testiranje, demonstracija in oddaja

Z lokalnim Compose preizkusita najmanj 48 zahtevanih operacij, vseh osem internih povezav, zavrnitev dostopa do tujih podatkov, potekel JWT, neznano vajo, neveljavno težo, ponovljen zaključek in izpad odvisnosti. Primerjajta šest dokumentov OpenAPI z izvajanjem ter preverita ponovno uporabo podatkov po ponovnem zagonu.

Na demonstraciji se registrirajta, izberita vajo, sestavita in zaključita trening, dodajta obrok in tehtanje ter ustvarita cilj teže in tedenski cilj treningov. Prikažita, kako Goals pridobi podatke iz Progress in Workout ter kako posamezne storitve uporabljajo svoje baze.

Rok za Nalogo 2 je dva tedna po predstavitvi. Točen datum in način oddaje preverita v eŠtudiju.
