from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Amount = Annotated[float, Field(ge=0, le=1_000_000, strict=True, allow_inf_nan=False)]


class MealInput(BaseModel):
    name: Name
    meal_date: date


class MealPatch(BaseModel):
    name: Name | None = None
    meal_date: date | None = None


class ItemInput(BaseModel):
    name: Name
    quantity: Annotated[float, Field(gt=0, le=1_000_000, strict=True, allow_inf_nan=False)]
    calories: Amount
    protein: Amount
    carbs: Amount
    fat: Amount


class MealCreate(MealInput):
    items: list[ItemInput] = Field(default_factory=list, max_length=100)


class Item(ItemInput):
    id: int


class MealSummary(MealInput):
    id: int


class NutritionTotals(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float


class Meal(MealSummary):
    items: list[Item]
    totals: NutritionTotals


class DailySummary(BaseModel):
    date: date
    meal_count: int
