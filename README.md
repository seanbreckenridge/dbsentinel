A counterpart to <https://sean.fish/mal_unapproved/>. That lists entries that have yet to be approved, denied entries and deleted entries

This is a work in progress, but the basics are up at <https://dbsentinel.sean.fish/search>

Incomplete setup instructions:

- Check [app/settings.py](app/settings.py) for the required environment variables
- `pipenv install --dev`
- [`checker_mal`](https://github.com/Hiyori-API/checker_mal) could be running on the same machine, if you want to keep an updated anime/manga ID list locally:
  - Can fill out `usernames.txt` with peoples list to check for new entries
  - If you have a `animelist.xml` file to use for `python3 main.py mal estimate-deleted-xml`, you can put it in `data/animelist.xml`
- `pipenv run prod`

### TODO:

- [ ] refresh data based on popularity/last updated date
- [ ] frontend in pheonix
  - [ ] moderators/trusted users
    - [ ] parse reasons for denials/deletions from thread/allow users to input
    - [ ] add frontend button to refresh data for entries
  - [ ] dashboard that shows stats etc.
  - [ ] frontend to view approved/deleted/denied/unapproved entries
  - [ ] add info on search page letting you know what each approved status means
  - [ ] let page be ordered by when items were approved/deleted/denied (guess by metadata if not available)
  - [ ] sort by media type, member count
  - [ ] dark mode
  - [ ] connect IDs to tmdb (manually, users can submit requests)
- [ ] API for deleted/denied/unapproved ids/name
- [ ] upload full API dump periodically to a public URL (w ids/names)
- [ ] let user upload their MAL XML export, parse and save data from it to localStorage
- [ ] let user find entries that are not on their list
- [ ] integrate with [notify-bot](https://github.com/seanbreckenridge/mal-notify-bot) so that sources added there get added to the website (also allow items which arent in #feed -- so this can source anything) -- only show on website through a domain allowlist
