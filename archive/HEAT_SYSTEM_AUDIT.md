# AFewBuds — Heat / Reeves completion audit

Scope: the supplied **v0.7.9-beta.2** source. The heat/Reeves function bodies remain
unchanged in the couch / away-care **v0.7.9-beta.3** build. Source paths below refer
to `scripts/main.gd` in beta.2; beta.3 has shifted line numbers.

**Verdict: implemented, but not complete enough to sign off or skip past.**
This is a gameplay-code audit, not real-world law-enforcement guidance.

## Implemented and exercised

The main scene has an active heat meter gated behind Chapter 2, heat gain/reduction,
a first Reeves door visit at 60 heat, an accept/negotiation/refusal UI, and a recurring
arrangement. The ordinary payment interval is three in-game days. Current protection
reduces added heat to 75% of the unprotected amount and stops while overdue.
Explicit missed-payment actions escalate risk and warnings. Qualifying later-day
raid rolls can cause inventory/cash/reputation loss, close the storefront, put staff
off duty and impose a one-game-day lockdown. Quiet exit and final payoff routes exist.
Paused gameplay and daily closeout do not advance the heat/day simulation.

Representative source functions: `_add_heat` (1298), `_update_heat_over_time` (1327),
`_check_reeves_trigger` (7424), `_start_reeves_door_visit` (7446),
`_start_reeves_arrangement` (7569), `_miss_reeves_payment` (7611),
`_roll_enforcement_raid` (7662), `_trigger_raid_event` (7675),
`_reeves_final_payoff` (7724), `_reeves_quiet_exit` (7737).

## Four reproduced defects

### 1. Chapter 3 can complete without meeting Reeves
**Source:** `_story_chapter_three_complete`, lines 6347–6358.
The visible story objective asks for Reeves, but the completion predicate checks
business/friend/sales/heat requirements without testing `reeves_met` or an equivalent
resolved encounter. A fixture meeting the other conditions with `reeves_met = false`
returned complete. The completion rule and displayed objectives need one definition;
a refusal path should also count as a resolved encounter, not force a paid deal.

### 2. Ignoring an overdue Reeves knock bypasses the normal missed-payment path
**Source:** `_customer_waited_too_long`, lines 7802 onward, versus
`_miss_reeves_payment`, lines 7611–7623.
The Reeves timeout adds 10 enforcement-risk points and starts his departure, but does
not record the missed payment or consistently set the raid-warning day. Reproduced
with risk at 55, an active overdue arrangement and no warning: ignoring him takes risk
above 60 while misses remain zero and `raid_warning_day` remains -1. A common resolved
outcome path should distinguish the first offer from an overdue payment and record
one missed-payment outcome per due period, including timeout or refusal.

### 3. Repeated early payments charge for the same next due date
**Source:** `_pay_reeves_due`, lines 7589–7609.
The function charges the full amount and increments payment statistics, then assigns
`game_day + 3` every time. Two early payments on the same day both spend cash and
count as payments without the second extending the next deadline. Either limit an
early payment to one permitted period or extend from the already-paid-through day;
make the displayed result match the choice. Deduplicate accidental repeated input.

### 4. Day-start status overwrites the raid-loss notice
**Source:** `_settle_daily_report`, lines 1206 onward, calls
`_roll_enforcement_raid` before assigning its routine Day Started status text.
An actual triggered raid changed inventory/cash and wrote its enforcement notice,
then the day-start code replaced that notice. The heat-event log still retains it;
this is not a claim that every record disappears. Consequential losses need a
persistent acknowledged report/summary rather than a transient overwritten message.

## Additional scope gap, not disguised as a runtime defect

The current raid is a data/status event, **not a completed visible raid sequence**.
It removes ceil(25% of stored stock) per product, clamps reserved stock, takes cash
up to `300 + round(heat) * 8`, reduces reputation by 10 and changes operation state.
The tested raid leaves live plant records unchanged. It does not implement animated
agents entering, searching the room or physically seizing crops/equipment. Those
parts should not be represented as already built.

## Validation and next acceptance criteria

The four defects were reproduced using the original function bodies in the supplied
Godot WebAssembly runtime. They are recorded separately from passing regression
assertions in `tests/couch_care_runtime_results.json`; they remain unfixed in beta.3.
Before rivals: align Chapter 3 objectives; unify first-offer/refusal/overdue/timeout
outcomes; make payments period-safe; retain a visible raid report; then test accept,
refuse, timeout, unaffordable payment, two misses, raid recovery, quiet exit, final
payoff, and pause/reload at each transition on an actual phone. Decide the desired
visible raid scene separately rather than silently equating a status event to one.
