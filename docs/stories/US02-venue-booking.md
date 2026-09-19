# US02 - Venue booking

- **Issue:** #18
- **Priority:** P0
- **Points:** 8
- **Owner:** @peng543
- **Screen:** /booking
## User story

As a **customer**, I want **to book a venue for a specific time slot** so that **I can secure my playing time**.

## Acceptance criteria

1. Given I have selected the available `18:00-19:00` time slot on `20/09/2026`, when I confirm the booking and proceed, then the slot becomes unavailable to other customers and I receive a booking confirmation.

2. Given another customer has just booked the selected `18:00-19:00` time slot, when I try to proceed, then the booking is rejected and I see the exact message **"This time slot is no longer available"**.

3. Given that the venue has no more slots available, when I try to book a slot, then the booking is rejected and I see the exact message **"This venue is no longer available"**.
## Related business rules

| ID  | Rule                                                                       | Example with concrete values                                                                     |
| --- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| BR5 | A confirmed time slot can belong to only one booking.                      | After one customer confirms the `18:00-19:00` slot, a second customer cannot book the same slot. |
| BR6 | The system must check slot availability again before confirming a booking. | If the slot becomes booked between selection and confirmation, the second booking is rejected.   |
| BR7 | A venue can be booked only if it has available slots.                     | If a venue has 6 slots and all of them are booked, it cannot be booked again.                  |


## Tasks

- [ ] Display available time slots and allow a customer to select one.
- [ ] Confirm the booking and mark the selected time slot as unavailable.
- [ ] Recheck availability before confirmation and show the exact conflict message.
- [ ] Send or display a booking confirmation after a successful booking.
- [ ] Display fully booked venues as unavailable.
- [ ] Add automated tests for successful booking and concurrent booking attempts.


## Note

This story depends on venue availability and customer authentication. It is a core booking flow because a customer must reserve a specific slot before the venue can be used.
