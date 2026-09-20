# US04 - Search for venues

- **Issue:** #16
- **Priority:** P0
- **Points:** 5
- **Owner:** @peng543
- **Screen:** /search

## User story

As a **customer**, I want **to search for sports venues by location and sport type** so that **I can find a suitable place to play**.

## Acceptance criteria

1. Given I am on the homepage, when I search for **"Football"** in **"Cau Giay"**, then I see a list of football pitches located in Cau Giay.

2. Given I search for a location with no venues, when I submit the search, then I see the exact message **"No venues found"**.

3. Given I search for a venue or sport, when I type in letters in the search field, then the search results will change accordingly.

## Related business rules

| ID   | Rule                                                                          | Example with concrete values                                                        |
| ---- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| BR10 | Search results must match both the selected sport type and location.          | A search for **"Football"** in **"Cau Giay"** returns football pitches in Cau Giay. |
| BR11 | A search with no matching venues must return an explicit empty-state message. | Searching a location with no venues displays **"No venues found"**.                |
| BR12 | Search results must be relevant and updated as the user types.                | As an user type in letters 'badminton', the search results change to only include venues with 'badminton' in their name.

## Tasks

- [ ] Add sport type and location search fields to the homepage.
- [ ] Filter venues by both the selected sport type and location.
- [ ] Display matching venues in a searchable results list.
- [ ] Display the exact **"No venues found"** message when there are no matches.
- [ ] Add a search field that updates the results as the user types.
- [ ] Add automated tests for matching results and an empty search result.

## Note

This story is the main discovery entry point for customers. The search results should lead to the venue details and availability flow in US03.
