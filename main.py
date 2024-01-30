#!/usr/bin/env python3
from datetime import date

import requests

import devconf


def main():
    devconf_2022 = devconf.Config(
        sessionize_id="p87oviq3",
        use_archive=True,
        events=[
            devconf.EventConfig(
                name="Cape Town",
                short_name="capetown",
                day=date(2022, 4, 5),
            ),
            devconf.EventConfig(
                name="Virtual",
                short_name="virtual",
                day=date(2022, 4, 7),
            ),
            devconf.EventConfig(
                name="Johannesburg",
                short_name="joburg",
                day=date(2022, 4, 7),
            ),
        ],
    )
    devconf_2023 = devconf.Config(
        sessionize_id="3hwiocdj",
        use_archive=True,
        events=[
            devconf.EventConfig(
                name="Cape Town",
                short_name="capetown",
                day=date(2023, 5, 23),
                archive_day=date(2023, 5, 28),
            ),
            devconf.EventConfig(
                name="Pretoria",
                short_name="pretoria",
                day=date(2023, 5, 25),
                archive_day=date(2023, 5, 28),
            ),
        ],
    )
    devconf_2024 = devconf.Config(
        sessionize_id="b0tah92u",
        use_archive=False,
        events=[
            devconf.EventConfig(
                name="Cape Town",
                short_name="capetown",
                day=date(2024, 5, 9),
            ),
            devconf.EventConfig(
                name="Johannesburg",
                short_name="joburg",
                day=date(2024, 5, 7),
            ),
        ],
    )

    # for config in [devconf_2022, devconf_2023, devconf_2024]:
    for config in [devconf_2024]:
        for event_config in config.events:
            event = devconf.get_event(
                config,
                event_config,
            )
            out = devconf.event_to_pentabarf(event)

            loc = event_config.name.lower().replace(" ", "-")
            with open(
                f"schedules/devconf-{event_config.day.year}-{loc}.pentabarf.xml",
                "w",
            ) as f:
                f.write(out.to_xml())


if __name__ == "__main__":
    main()
