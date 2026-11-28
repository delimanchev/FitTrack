# Nutrition

FastAPI storitev za obroke in njihove postavke. Vsak obrok pripada uporabniku z ID-jem `sub` iz JWT. Obroki so v tabeli `meals`, postavke pa v `meal_items`. Izbris obroka odstrani tudi njegove postavke.

## API

| Metoda | Pot |
| --- | --- |
| GET, POST | `/api/meals` |
| GET, PUT, PATCH, DELETE | `/api/meals/{meal_id}` |
| POST | `/api/meals/{meal_id}/items` |
| PUT, DELETE | `/api/meals/{meal_id}/items/{item_id}` |
| GET | `/meals/summary?date=YYYY-MM-DD` (interno) |

Seznam obrokov sprejme `date`, `limit` in `offset`. Podrobnosti obroka vključujejo postavke in seštevke. `PUT` zamenja ime in datum obroka, `PATCH` pa spremeni podana polja. Postavke imajo svoje poti.

`POST /api/meals` sprejme na primer

```json
{
  "name": "Kosilo",
  "meal_date": "2026-11-28",
  "items": [
    {"name": "Riž", "quantity": 2, "calories": 130, "protein": 3, "carbs": 28, "fat": 1}
  ]
}
```

Podatki o hranilih veljajo za enoto. Dve enoti riža v primeru prispevata 260 kcal, 6 g beljakovin, 56 g ogljikovih hidratov in 2 g maščob. Storitev izračuna seštevek iz trenutno shranjenih postavk.

Ob vnosu obroka Nutrition pokliče `GET /users/{user_id}` z glavo `X-Service-Token`. User vrne `200` za obstoječega uporabnika ali `404`, če ga ni. Pri izpadu User Nutrition vrne `503` brez zapisa obroka. `400` pomeni neveljavne podatke, `401` neveljaven ali manjkajoč JWT, `403` zavrnjen dostop in `404` manjkajoč vir.

User uporablja interni povzetek z glavama `X-Service-Token` in `X-User-Id`. Druga glava vsebuje ID že prijavljenega uporabnika. Povzetek vrne `date` in `meal_count`.

## Zagon

Pred zagonom nastavimo okoljske spremenljivke.

| Spremenljivka | Vrednost |
| --- | --- |
| `DATABASE_URL` | Povezava do lastne baze `nutrition_db` |
| `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE` | Nastavitve JWT storitve User. Predviden je HS256 s ključem najmanj 32 bajtov. |
| `USER_SERVICE_URL` | Osnovni naslov storitve User |
| `NUTRITION_TO_USER_TOKEN` | Poverilnica, ki jo Nutrition pošlje storitvi User |
| `USER_TO_NUTRITION_TOKEN` | Poverilnica, ki jo Nutrition sprejme za povzetek |

Iz mape `services/nutrition` v aktivnem Python okolju

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Ob zagonu se izvede začetna migracija. OpenAPI je na `/openapi.json`, Swagger UI pa na `/docs`. Sliko zgradimo v isti mapi z `docker build -t fittrack-nutrition .`. Vsebnik posluša na vratih `8000`.

## Preizkusi

Preizkusi uporabijo ločeno PostgreSQL bazo in majhno nadomestno storitev User, ki jo zaženejo sami. Spodnji primer zaženemo iz mape `services/nutrition` v aktivnem Python okolju.

```powershell
$env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
docker run --rm -d --name fittrack-nutrition-test -p 127.0.0.1:5435:5432 `
  -e POSTGRES_PASSWORD -e POSTGRES_DB=nutrition_test postgres:16-alpine
$env:NUTRITION_TEST_DATABASE_URL = "postgresql://postgres:$($env:POSTGRES_PASSWORD)@127.0.0.1:5435/nutrition_test"
try {
    python -m unittest discover -s tests -v
} finally {
    docker stop fittrack-nutrition-test
    Remove-Item Env:NUTRITION_TEST_DATABASE_URL, Env:POSTGRES_PASSWORD
}
```
