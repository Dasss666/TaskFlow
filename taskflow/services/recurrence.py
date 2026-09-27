from calendar import monthrange
from datetime import date, timedelta

HORIZON_DAYS = 90


def _next_month(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _next_occurrence(current: date, recurrence: str) -> date:
    if recurrence == "daily":
        return current + timedelta(days=1)
    if recurrence == "weekly":
        return current + timedelta(days=7)
    if recurrence == "monthly":
        return _next_month(current)
    return current


def materialize_recurring_tasks(database, horizon_days: int = HORIZON_DAYS) -> int:
    today = date.today()
    horizon = today + timedelta(days=horizon_days)
    created = 0

    for template in database.recurring_templates():
        current = date.fromisoformat(template["due_date"])
        while True:
            current = _next_occurrence(current, template["recurrence"])
            if current > horizon:
                break
            if current < today:
                continue
            if database.occurrence_exists(template["id"], current.isoformat()):
                continue

            database.add_task(
                title=template["title"],
                description=template["description"],
                due_date=current.isoformat(),
                start_time=template["start_time"],
                end_time=template["end_time"],
                priority=template["priority"],
                category=template["category"],
                tags=template["tags"],
                recurrence="none",
                recurrence_source_id=template["id"],
            )
            created += 1

    return created
