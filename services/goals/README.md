# Goals

FastAPI storitev za ciljno težo, tedensko število treningov in nastavitve opomnikov. Cilj pripada uporabniku z ID-jem `sub` iz JWT. Podatki so v tabelah `goals` in `goal_reminders`. Izbris cilja odstrani tudi njegove opomnike.

## API

| Metoda | Pot |
| --- | --- |
| GET, POST | `/api/goals` |
| PUT, PATCH, DELETE | `/api/goals/{goal_id}` |
| GET | `/api/goals/{goal_id}/status` |
| POST | `/api/goals/{goal_id}/reminders` |
| PUT, DELETE | `/api/goals/{goal_id}/reminders/{reminder_id}` |

Seznam ciljev podpira `limit` in `offset`. Vsak cilj v seznamu vsebuje svoje opomnike. `PUT` zamenja podatke cilja, `PATCH` spremeni podana polja. Opomnik ima `dayOfWeek` od 1 (ponedeljek) do 7 (nedelja), `time` v obliki `HH:MM` in `enabled`, ki je privzeto `true`. Storitev shrani nastavitev opomnika.

### Izračun statusa

- **Ciljna teža** sprejme `{"goalType":"weight","target":80,"startWeightKg":90}`. Začetna teža se razlikuje od ciljne. Goals prek `GET /progress/latest` prebere `weightKg`. Izračun je `(trenutna − začetna) / (ciljna − začetna) × 100`, omejen na 0–100 %. Če Progress vrne `404`, odgovor vsebuje `weightKg: null` in `percent: null`.
- **Tedenski treningi** sprejmejo `{"goalType":"weekly_workouts","target":4}`. Goals pokliče `GET /workouts/completed?from=…&to=…` in prešteje elemente v vrnjenem seznamu treningov. Trenutna nastavitev uporablja UTC. `from` je datum ponedeljka z vključeno mejo, `to` pa datum naslednjega ponedeljka z izključeno mejo. Trije treningi pri cilju štirih vrnejo `completed: 3` in `percent: 75`.

Obe zahtevi pošljeta `X-Service-Token` in `X-User-Id`. Če odvisna storitev ni dosegljiva ali vrne nepričakovane podatke, Goals vrne `503`.

## Zagon

| Spremenljivka | Vrednost |
| --- | --- |
| `DATABASE_URL` | Povezava do lastne PostgreSQL baze `goals_db` |
| `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` | Nastavitve skupnega JWT. Predviden je HS256 s ključem najmanj 32 bajtov. |
| `PROGRESS_SERVICE_URL`, `WORKOUT_SERVICE_URL` | Osnovna naslova odvisnih storitev |
| `GOALS_TO_PROGRESS_TOKEN`, `GOALS_TO_WORKOUT_TOKEN` | Poverilnici za klica Goals → Progress in Goals → Workout |

Iz mape `services/goals` v aktivnem Python okolju in z nastavljenimi spremenljivkami

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Ob zagonu se izvede začetna migracija. OpenAPI je na `/openapi.json`, Swagger UI pa na `/docs`. Docker sliko zgradimo z `docker build -t fittrack-goals .`.

## Preizkusi

Testi uporabijo ločeno PostgreSQL bazo in sami zaženejo nadomestka za Progress in Workout. Ukaze poženemo iz mape `services/goals`.

```powershell
$env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
docker run --rm -d --name fittrack-goals-test -p 127.0.0.1:5437:5432 `
  -e POSTGRES_PASSWORD -e POSTGRES_DB=goals_test postgres:16-alpine
$env:GOALS_TEST_DATABASE_URL = "postgresql://postgres:$($env:POSTGRES_PASSWORD)@127.0.0.1:5437/goals_test"
try {
    python -m unittest discover -s tests -v
} finally {
    docker stop fittrack-goals-test
    Remove-Item Env:GOALS_TEST_DATABASE_URL, Env:POSTGRES_PASSWORD
}
```
