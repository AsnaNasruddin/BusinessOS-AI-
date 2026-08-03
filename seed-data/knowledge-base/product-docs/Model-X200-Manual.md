# Acme Robotics Model X200 — Product Manual

*Knowledge base: Product Docs*

*(Condensed for demo purposes — the real Document row this represents is
listed as 2.1 MB / ~88 chunks in the seeded frontend data, i.e. a full
multi-chapter PDF manual. This file is representative source content:
enough real structure and detail for RAG chunking to behave sensibly, not a
literal 40-page manual.)*

## 1. What's in the Box

- Model X200 unit
- Charging dock
- Power adapter
- 2× replacement filters
- Quick start card

## 2. Setup

1. Place the charging dock against a wall with at least 1.5 ft of clearance
   on either side.
2. Power on the unit; the status ring pulses blue during startup.
3. Open the Acme companion app, select "Add Device," and follow the
   in-app pairing flow (2.4GHz Wi-Fi only — the X200 does not support 5GHz
   networks).
4. Run the guided home mapping pass before first use. This takes 10–20
   minutes depending on home size and improves both cleaning coverage and
   security-patrol routing.

## 3. Modes

- **Clean mode** — standard floor cleaning, runs on a schedule or on demand.
- **Patrol mode** — the unit moves through mapped rooms on a rotating
  schedule, using its front camera for light home-security monitoring.
  Patrol and Clean cannot run simultaneously.
- **Quiet hours** — user-configurable window during which the unit will not
  start Clean or Patrol mode automatically (manual start still works).

## 4. Maintenance

- **Filters** — replace every 2–3 months under normal use; the app will
  prompt when suction drops below expected levels. Filters are a consumable
  and not covered by warranty past 90 days (`Warranty-Terms.md`).
- **Brushes** — clean weekly by removing visible hair/debris; replace every
  6 months. Also a consumable.
- **Sensors** — wipe the front camera and floor-facing sensors with a dry
  microfiber cloth monthly. Do not use liquid cleaners on the sensor array.

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Won't leave the dock | Battery below 15% | Let it charge fully before use |
| Patrol mode camera feed is dark | Lens obstruction or low light | Clean the lens; patrol mode needs ambient light — it is not a night-vision camera |
| Frequent disconnects from app | 5GHz network selected | Reconnect to a 2.4GHz network |
| Self-test fails with code E-04 | Sensor calibration drift | Run Settings → Diagnostics → Recalibrate; if it persists, this is a warranty matter |

## 6. Safety

- IPX4 splash resistance only — not submersible. Liquid damage beyond IPX4
  is excluded from the standard warranty (`Warranty-Terms.md`).
- Keep away from stairs without a mapped virtual boundary configured in the
  app; the X200 does not have stair-drop sensors before the home-mapping
  pass is complete.
- If the unit reports overheating, smells of burning, or emits smoke: power
  off immediately, unplug the dock, and contact support — this is a safety
  escalation, not a standard troubleshooting case (`Escalation-Scripts.md`).

## Related Documents

- `Model-X200-FAQ.md` — shorter-form common questions
- `Warranty-Terms.md` — what maintenance issues are and aren't covered
