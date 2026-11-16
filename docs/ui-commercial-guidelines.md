# Sports Venue Booking System - Commercial UI/UX Design System Research & Guidelines

**Date:** 20/10/2026  
**Reference Platforms:** Playo (Global), SportyNation, WeSport (VN), PlaySpace (VN), ModunSport (VN).  
**Document Purpose:** Commercial-grade UI/UX design architecture and standards that move beyond a "template / mechanical assignment" feel while maintaining 100% compliance with grading criteria and project Business Rules.

---

## 1. Analysis of Commercial Products (Market Benchmarks)

### A. Why do "mechanical assignment" interfaces feel dull?
1. **Lack of Visual Hierarchy:** Using raw data tables (`<table>`) like an Excel spreadsheet without real photos of football pitches or badminton courts.
2. **Lack of Athletic Energy:** Washed-out colors or dull grays instead of energetic, sport-oriented palettes (Sport Green, Electric Blue, Energetic Orange).
3. **Clunky Time-Slot Selection:** Forcing users to remember times or scan long lists instead of providing an intuitive Horizontal Date Strip and immediately clickable time-slot cards.
4. **Missing Social Proof & Amenity Badges:** Missing star ratings (4.8 ★), weekly booking counts, and amenity badges (Car Parking, Refreshment Canteen, Racket Rental, Night LED Floodlights).

### B. Lessons from Playo & WeSport (Commercialization)
1. **Discovery / Card-first Architecture:**
   - Users browse venues visually through **Venue Cards** featuring high-quality cover photos, venue names, court/pitch types (7-a-side artificial turf pitch, Yonex-standard badminton court), distance/district, prominent starting price badges, and clear call-to-action (CTA) buttons.
2. **Sport Filter Pills:**
   - Instead of hiding sports inside a dropdown menu, surface popular sports as interactive chips/pills with clear icons (⚽ Football, 🏸 Badminton, 🎾 Tennis, 🏀 Basketball, 🏓 Table Tennis, Pickleball).
3. **Time Slot Matrix:**
   - Differentiate slot states clearly with intuitive colors:
     - **Emerald Green:** Available - Book now.
     - **Sunset Orange:** Peak hours - Accompanied by clear price labels.
     - **Muted Grey:** Booked / Unavailable.
4. **Booking Flow & Sticky Order Summary:**
   - Design a modern receipt-style **Booking Summary Card**: summarizing total hours, per-slot unit prices, transparent cancellation policy, and a prominent, confident checkout button.

---

## 2. Standards Applied to the G9 Codebase

To ensure both commercial visual polish and **zero regressions across the automated test suite**:
1. **Search Interface ([`src/templates/search.html`](src/templates/search.html)):**
   - Provide a **Commercial Card Grid** view alongside or wrapping the data so that required `data-text` attributes, `#count`, `#results`, and `table` elements remain intact for automated checks while delivering a rich visual experience for human users in the browser.
   - Include real sports venue photos, star rating labels, and venue amenities.
2. **Venue Detail Interface ([`src/templates/venue.html`](src/templates/venue.html)):**
   - Integrate a Hero Section with a real venue photo banner, location badges, and amenities.
   - Preserve all state element IDs (`#loading`, `#error`, `#empty`, `#data`) to satisfy Milestone 3 requirements.
3. **Colors and Effects ([`src/static/style.css`](src/static/style.css)):**
   - Use a modern sports color palette, Soft 3D Shadows, and smooth hover transitions.
