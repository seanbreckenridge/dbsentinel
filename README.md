A counterpart to <https://sean.fish/mal_unapproved/>. That lists entries that have yet to be approved, denied entries and deleted entries

Frontend: <https://github.com/seanbreckenridge/dbsentinel-next>

# WORK IN PROGRESS

- [x] data backend upadtes using other services
- [x] task API to connect frontend to data backend
- [x] frontend with discord login
- [x] dashboard that shows stats etc.
- [x] proxy images from MAL incase they get deleted
- [x] add command to refresh summary for entries with missing images
- [x] frontend to view approved/denied/deleted/unapproved entries
- [ ] add info on search page letting you know what each approved status means
- [ ] let page be ordered by when items were approved/deleted/denied (guess by metadata if not available)
- [ ] compare against my list to find deleted entries, request that many pages
- [ ] roles to give people more permissions
  - [ ] let users refresh data for old entries
  - [x] connect IDs to anilist (using local `URLCache`)
  - [x] integrate <https://github.com/kawaiioverflow/arm>
  - [ ] connect IDs to tmdb (manually, users can submit requests)
- [ ] API for deleted/denied/unapproved ids/names
- [ ] let user upload their MAL XML export, parse and save data from it to localStorage
  - [ ] let user find entries that are not on their list
- [ ] integrate with [notify-bot](https://github.com/seanbreckenridge/mal-notify-bot) so that sources added there get added to the website (also allow items which arent in #feed -- so this can source anything) -- only show on website through a domain allowlist
