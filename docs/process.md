# Software Process Dossier: Sports Venue Booking System

## Section 1 — Chosen process and its position on the spectrum

### (a) The Model
Our team adopts a **Hybrid Process Model** combining **Incremental/Agile development** in 2-week sprints with early **UI/functional prototyping**, operating inside the **Plan-Driven milestone gates** required by the course.

One development cycle (Sprint) runs as follows:
1. **Sprint Planning**: The team selects high-priority booking features from the backlog (e.g., venue search, time-slot availability matrix, booking checkout, owner management).
2. **Feature Development**: Members implement assigned features on dedicated Git branches (e.g., building FastAPI/Node backend endpoints or React/Vue booking calendar UI) reusing existing libraries (e.g., calendar pickers, UI component libraries).
3. **Validation & Peer Review**: The author tests code locally; a teammate reviews the Pull Request for logic errors (such as booking slot overlaps) and approves it before merging into `main`.
4. **Sprint Demo & Retrospective**: The team verifies a working web increment, collects internal and instructor feedback, and updates backlog priorities for the next cycle.

### (b) Position on the Spectrum
We position our process at **80% Agile and 20% Plan-Driven**.
- **Plan-Driven (Frozen throughout semester)**: The core product vision (sports court booking platform), fundamental system architecture, and the four course milestone deadlines are strictly frozen.
- **Agile (Re-opened and adjusted each sprint)**: UI workflows, time-slot conflict handling logic, payment mock flows, venue management features, and task assignments are re-evaluated and adjusted every two weeks based on testing and feedback.

---

## Section 2 — The five diagnostic questions

1. **Requirements Stability (Volatile)**: Our requirements are volatile. Details such as slot reservation timeouts, cancellation policies, dynamic pricing for peak hours, and venue owner dashboard features will continually evolve as we test the booking user experience.
2. **Safety and Legal Impact (Low)**: The project is an academic web prototype with no safety-critical risks, real banking liabilities, or strict governmental compliance needs that would require formal change-control boards.
3. **Team Size and Distribution (Small & Co-located)**: We are a 5-member student team in the same class. Low communication overhead allows us to coordinate daily via chat and direct meetings without formal documentation handoffs.
4. **Customer Engagement (Periodic Checkpoints)**: The course instructor acts as our primary evaluator, providing feedback during weekly class sessions and milestone evaluations, complemented by usability feedback from classmates who play sports.
5. **Organizational Culture & Constraints (Milestone-driven)**: The course enforces four rigid milestone checkpoints and a fixed final demo date, creating a fixed schedule boundary within which our agile sprints operate.

---

## Section 3 — Critical thinking: risks of the opposite choice

If our team adopted a **100% Plan-Driven (Waterfall) process**:
- **Single Biggest Risk**: Late Integration and Concurrency Failure (*Big-Bang Disaster*).
- **Mechanism of Damage**: Spending the first half of the semester writing static requirement specifications and database schemas without building runnable software delays tackling complex technical challenges—such as preventing double-booking race conditions and state synchronization between the court calendar and backend. These fatal integration flaws would only be discovered near the final deadline, when refactoring database transactions or UI state is too costly and time has run out.
- **First Concrete Symptom**: At Milestone 2, the team would present static database diagrams and wireframes on paper, but have zero working calendar booking flows or functional APIs to demonstrate.

---

## Section 4 — Process rules your team commits to

1. **Mandatory Peer Review**: Every code and documentation change must reach `main` via a Pull Request reviewed and approved by at least one other team member.
2. **Two-Week Sprint Cadence**: Development proceeds in strict two-week sprints, with the product backlog re-prioritized at the start of each cycle.
3. **Scope Change Tracking**: Any modification to core booking requirements or schema designs after a sprint begins must be recorded in `docs/changelog.md`.
4. **Always-Deployable Main Branch**: The `main` branch must always remain runnable and bug-free, with consistent database seed data for testing.
