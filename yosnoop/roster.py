import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Member:
    email: str
    display_name: str
    host_priority: int
    may_host: bool
    mixed_room_asker: bool


@dataclass(frozen=True)
class Roster:
    domain: str
    google_group: str
    members: tuple[Member, ...]

    def by_email(self, email: str) -> Member | None:
        return next((x for x in self.members if x.email == email.lower()), None)

    def by_display_name(self, name: str) -> list[Member]:
        return [x for x in self.members if x.display_name == name]


def _dupes(values):
    seen, dup = set(), set()
    for v in values:
        (dup if v in seen else seen).add(v)
    return dup


def load(path) -> Roster:
    raw = json.loads(Path(path).read_text())
    domain = raw["domain"].lower()
    members = tuple(Member(email=x["email"].lower(), display_name=x["display_name"],
                           host_priority=int(x["host_priority"]), may_host=bool(x["may_host"]),
                           mixed_room_asker=bool(x["mixed_room_asker"])) for x in raw["members"])
    for x in members:
        if not x.email.endswith("@" + domain):
            raise ValueError(f"member outside domain {domain}: {x.email}")
    for field, label in (("email", "email"), ("host_priority", "host_priority"), ("display_name", "display_name")):
        d = _dupes(getattr(x, field) for x in members)
        if d:
            raise ValueError(f"duplicate {label}: {sorted(map(str, d))}")
    return Roster(domain=domain, google_group=raw["google_group"], members=members)
