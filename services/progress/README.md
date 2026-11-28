# Progress

Storitev NestJS za telesno težo in obsege. Vse meritve so v tabeli `measurements`. Stolpec `kind` loči težo od obsegov, `user_id` pa določa lastnika. Datum je koledarski datum v obliki `YYYY-MM-DD`.

## API

| Metoda | Pot |
| --- | --- |
| GET, POST | `/api/progress` |
| GET | `/api/progress/latest` |
| PUT, DELETE | `/api/progress/{id}` |
| GET, POST | `/api/progress/body-measurements` |
| PUT, DELETE | `/api/progress/body-measurements/{measurementId}` |
| GET | `/progress/latest` (interno) |

`POST /api/progress` sprejme `{"weightKg": 85.5, "measuredAt": "2026-11-28"}`. Pri obsegu telo zahteve vsebuje `area`, `circumferenceCm` in `measuredAt`. `PUT` zamenja podatke meritve. Seznama podpirata `limit` in `offset`. Zadnja teža je teža z najnovejšim datumom. Pri enakih datumih se uporabi zadnji vnos.

Javne poti uporabijo `sub` iz JWT. Pred vsakim novim vnosom Progress pokliče `GET /users/{userId}` z glavo `X-Service-Token`. User vrne `200` ali `404`. Če User ni dosegljiv, Progress vrne `503` brez zapisa meritve.

Goals, Exercise in Workout kličejo `/progress/latest` s svojo poverilnico `X-Service-Token` in glavo `X-User-Id` za ID uporabnika. Pot vrne `id`, `weightKg` in `measuredAt` ali `404`, če tehtanja še ni.

## Zagon

| Spremenljivka | Vrednost |
| --- | --- |
| `DATABASE_URL` | Povezava do lastne PostgreSQL baze `progress_db` |
| `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` | Nastavitve skupnega JWT. Predviden je HS256 s ključem najmanj 32 bajtov. |
| `USER_SERVICE_URL` | Osnovni naslov storitve User |
| `PROGRESS_TO_USER_TOKEN` | Poverilnica za zahteve Progress → User |
| `GOALS_TO_PROGRESS_TOKEN`, `EXERCISE_TO_PROGRESS_TOKEN`, `WORKOUT_TO_PROGRESS_TOKEN` | Poverilnice za interni dostop do zadnje teže |
| `PORT` | Vrata storitve. Privzeto `8000`. |

Iz mape `services/progress` z Node.js 24 in nastavljenimi okoljskimi spremenljivkami

```powershell
npm ci
npm run build
npm start
```

Ob zagonu se izvede začetna migracija. Swagger UI je na `/docs`, dokument OpenAPI pa na `/openapi.json`. Sliko zgradimo z `docker build -t fittrack-progress .`.

## Preizkusi

Preizkusi zaženejo Progress in nadomestno storitev User. Uporabijo ločeno PostgreSQL bazo. Ukaze poženemo iz mape `services/progress` po `npm ci`.

```powershell
$env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
docker run --rm -d --name fittrack-progress-test -p 127.0.0.1:5436:5432 `
  -e POSTGRES_PASSWORD -e POSTGRES_DB=progress_test postgres:16-alpine
$env:PROGRESS_TEST_DATABASE_URL = "postgresql://postgres:$($env:POSTGRES_PASSWORD)@127.0.0.1:5436/progress_test"
try {
    npm test
} finally {
    docker stop fittrack-progress-test
    Remove-Item Env:PROGRESS_TEST_DATABASE_URL, Env:POSTGRES_PASSWORD
}
```
