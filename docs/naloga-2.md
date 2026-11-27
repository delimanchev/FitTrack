# Naloga 2 – Razvoj osnovne verzije mikrostoritev

[FitTrack](../README.md) · [Kanban](https://github.com/users/delimanchev/projects/6/views/2) · [Uskladitev pogodb](https://github.com/delimanchev/FitTrack/issues/1)

## Načrt dela

Načrt za Nalogo 1 je za vse zaledne storitve predvidel ASP.NET Core. Za Nalogo 2 uporabljamo tri ogrodja. Andrejeve storitve uporabljajo ASP.NET Core Web API, Nutrition in Goals uporabljata FastAPI, Progress pa NestJS.

- **Andrej** poleg svojih storitev pripravi [Docker Compose](https://github.com/delimanchev/FitTrack/issues/2), [API Gateway](https://github.com/delimanchev/FitTrack/issues/9) in [frontend za prijavo in treninge](https://github.com/delimanchev/FitTrack/issues/10).
- **Anastasija** poleg svojih storitev pripravi [frontend za prehrano, napredek in cilje](https://github.com/delimanchev/FitTrack/issues/12) in vodi [integracijsko testiranje](https://github.com/delimanchev/FitTrack/issues/11).
- Skupaj uskladiva API pogodbe, avtentikacijo in časovne intervale ter pripraviva [demonstracijo in oddajo](https://github.com/delimanchev/FitTrack/issues/13).

[Matrika REST API](../README.md#rest-api) določa dve operaciji vsake zahtevane metode na storitev. Klici User → Nutrition, Exercise → Progress in Workout → Progress dopolnjujejo pet klicev iz Naloge 1. Vsaka storitev tako sama kliče vsaj eno storitev drugega člana.

## Pogoji za zaključek storitve

- [ ] Delujejo vsaj 2 GET, 2 POST, 2 PUT in 2 DELETE po matriki. Preizkušena sta tudi napačen vhod in nedovoljen dostop.
- [ ] Storitev uporablja svojo bazo PostgreSQL, migracije in omejeno število povezav. Filtriranje in strani pri večjih seznamih se izvedeta v bazi.
- [ ] Storitev ima lasten Dockerfile in `.dockerignore`. Slika uporablja primerno majhno osnovo ali večstopenjsko gradnjo in vsebuje izvajalne odvisnosti.
- [ ] Delujeta lasten `/openapi.json` in najmanj en neposreden klic storitve drugega člana. Preizkušeni so uspeh, dovoljenja in odziv na izpad.
- [ ] Zagon iz svežega klona in predvideni primer sta potrjena s Compose. Pred premikom v **Done** drugi član pregleda PR, koda pa je združena.

## Testiranje, demonstracija in oddaja

Z lokalnim Compose preizkusiva najmanj 48 zahtevanih operacij in vseh osem internih povezav. Pokrijeva tudi zavrnitev dostopa do tujih podatkov, potekel JWT, neznano vajo, neveljavno težo, ponovljen zaključek treninga in izpad odvisnosti. Šest dokumentov OpenAPI primerjava z dejanskim delovanjem in preveriva ohranitev podatkov po ponovnem zagonu.

Demonstracija zajema registracijo, izbiro vaje, sestavo in zaključek treninga, vnos obroka in tehtanja ter oba tipa ciljev. Prikaževa, kako Goals pridobi podatke iz Progress in Workout ter kako storitve uporabljajo svoje baze.

Rok za oddajo je dva tedna po predstavitvi. Točen datum in način oddaje preveriva v eŠtudiju.
