from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator


GoalType = Literal["weight", "weekly_workouts"]
PositiveNumber = Annotated[float, Field(gt=0, le=1000, strict=True, allow_inf_nan=False)]
ReminderTime = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]


class GoalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goalType: GoalType
    target: PositiveNumber
    startWeightKg: PositiveNumber | None = None

    @model_validator(mode="after")
    def check_target(self):
        if self.goalType == "weight":
            if self.startWeightKg is None or self.startWeightKg == self.target:
                raise ValueError("A weight goal needs a starting weight different from its target")
        elif not self.target.is_integer() or self.startWeightKg is not None:
            raise ValueError("A weekly workout goal needs a whole number and no starting weight")
        return self


class GoalPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goalType: GoalType | None = None
    target: PositiveNumber | None = None
    startWeightKg: PositiveNumber | None = None


class ReminderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dayOfWeek: Annotated[int, Field(ge=1, le=7, strict=True)]
    time: ReminderTime
    enabled: StrictBool = True


class Reminder(ReminderInput):
    id: int


class Goal(GoalInput):
    id: int
    reminders: list[Reminder]


class WeightStatus(BaseModel):
    goalId: int
    target: float
    weightKg: float | None
    percent: float | None


class WorkoutStatus(BaseModel):
    goalId: int
    target: int
    completed: int
    percent: float
