import pretalx


def schedule_to_pentabarf(schedule: pretalx.Schedule):
    return pretalx.schedule_to_pentabarf(
        schedule,
        title="BSides",
        city="Johannesburg",
        venue="Focus Rooms, 20 Heaton Lane Longlake, Johannesburg",
    )
