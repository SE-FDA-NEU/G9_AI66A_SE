# US03 - View venue details and availability

- **Issue:** #17
- **Priority:** P0
- **Points:** 5
- **Owner:** @peng543
- **Screen:** /venue 

## User story

As a **customer**, I want **to view the details and availability of a venue** so that **I can decide when to book it**.

## Acceptance criteria

1. Given I am viewing a specific venue, when I select the date `20/09/2026`, then I see all available and booked time slots for that day, including their current status.

2. Given I am viewing a venue, when I click on the gallery, then I can see photos of the venue's facilities.



## Related business rules

| ID  | Rule                                                                  | Example with concrete values                                                                    |
| --- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| BR8 | Availability must be displayed for the date selected by the customer. | Selecting `20/09/2026` shows the available and booked slots for `20/09/2026`, not another date. |
| BR9 | Venue gallery photos must represent the selected venue's facilities.  | Opening the gallery for Venue A shows photos belonging to Venue A.                              |

## Tasks

- [ ] Display the selected venue's name, location, facilities, and other available details.
- [ ] Add a date selector for viewing daily availability.
- [ ] Display every time slot with an available or booked status.
- [ ] Add a gallery that displays photos for the selected venue.
- [ ] Add automated tests for date-based availability and the venue gallery.

## Note

This story supports the booking flow by giving customers enough information to choose a suitable venue and time slot before making a reservation.
