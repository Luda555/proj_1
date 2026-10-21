
from datetime import date, datetime, time, timedelta


OPEN_HOUR = 9
CLOSE_HOUR = 18
DEFAULT_STEP = 30
SEARCH_DAYS = 7
MAX_RESULTS = 10


def _appointment_date(value):
    """Convert an appointment date to a date object."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    return None


def _appointment_start_time(value):
    """Convert an appointment start time to a time object."""
    if isinstance(value, time):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None

    return None


def _employee_username(employee):
    """Get a staff member's username."""
    return getattr(employee, "username", str(employee))


def _employee_rating(employee):
    """Return a valid numeric rating, or zero if unavailable."""
    try:
        rating = float(getattr(employee, "rating", 0.0))
        return rating if rating >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def get_free_slots_for_all_suitable_staff(
    appointments,
    total_duration_minutes,
    suitable_employees,
):
    """
    Return available appointment slots for suitable employees.

    Working hours: 09:00–18:00.
    Search horizon: the next seven calendar days.
    Slots start at 30-minute intervals.
    Existing Scheduled and In Progress appointments block time.
    Results are sorted by date, time, then employee rating.
    """

    if (
        isinstance(total_duration_minutes, bool)
        or not isinstance(total_duration_minutes, int)
        or total_duration_minutes <= 0
    ):
        raise ValueError(
            "Appointment duration must be a positive integer."
        )

    appointments = list(appointments)
    suitable_employees = list(suitable_employees)

    if not suitable_employees:
        return []

    duration = timedelta(minutes=total_duration_minutes)
    now = datetime.now()
    today = now.date()
    all_slots = []

    for day_offset in range(1, SEARCH_DAYS + 1):
        check_date = today + timedelta(days=day_offset)

        day_start = datetime.combine(
            check_date,
            time(OPEN_HOUR, 0),
        )
        day_end = datetime.combine(
            check_date,
            time(CLOSE_HOUR, 0),
        )

        for employee in suitable_employees:
            employee_name = _employee_username(employee)

            # Find active appointments belonging to this employee.
            employee_appointments = []

            for appointment in appointments:
                if appointment.status not in (
                    "Scheduled",
                    "In Progress",
                ):
                    continue

                appointment_date = _appointment_date(
                    appointment.date
                )

                if appointment_date != check_date:
                    continue

                if appointment.staff != employee_name:
                    continue

                start_time = _appointment_start_time(
                    appointment.start_time
                )

                if start_time is None:
                    continue

                appointment_duration = (
                    appointment.total_duration_minutes
                )

                if (
                    isinstance(appointment_duration, bool)
                    or not isinstance(appointment_duration, int)
                    or appointment_duration <= 0
                ):
                    continue

                existing_start = datetime.combine(
                    check_date,
                    start_time,
                )
                existing_end = existing_start + timedelta(
                    minutes=appointment_duration
                )

                employee_appointments.append(
                    (existing_start, existing_end)
                )

            potential_start = day_start

            while potential_start + duration <= day_end:
                potential_end = potential_start + duration

                overlaps = any(
                    potential_start < existing_end
                    and existing_start < potential_end
                    for existing_start, existing_end
                    in employee_appointments
                )

                if not overlaps:
                    rating = _employee_rating(employee)

                    all_slots.append(
                        {
                            "datetime_obj": potential_start,
                            "display": (
                                f"{check_date:%Y-%m-%d} | "
                                f"{potential_start:%H:%M} - "
                                f"{potential_end:%H:%M} "
                                f"(Master: {employee_name} "
                                f"Rating: {rating:g})"
                            ),
                            "date_str": check_date.isoformat(),
                            "time_str": potential_start.strftime(
                                "%H:%M"
                            ),
                            "employee": employee,
                            "rating": rating,
                        }
                    )

                potential_start += timedelta(
                    minutes=DEFAULT_STEP
                )

    all_slots.sort(
        key=lambda slot: (
            slot["datetime_obj"],
            -slot["rating"],
        )
    )

    return all_slots[:MAX_RESULTS]




