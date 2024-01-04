# Blocking

Functionalities: 

- User can click on 3 dots on the top right corner of each post to block
- User can also go to a particular dashboard to block
- Blocking a user will block ALL the pet profiles owned by that user
- To manage blocked users, user can see the list in settings, and un-block a user
- Need to wait 48 hours to re-block a user
- List will show "<pet_id> and associated profiles"


Feed Visibility
- Blocked users' posts won't show up on Feed

Dashboard
- If somehow user lands on a blocked user's dasboard page, no posts will show and it should say blocked

Interactions
- Historical likes will be mutually removed
- Future interactions (likes) will be prohibited


# Report Content

Functionalities:

- User can click on 3 dots on the top right corner of each post to report content
- User can also do that from post detail page
- Reported content will be immediately invisible to the current user
- Users are given further options to block
- Triggers an email to me, as well as writing it to database
- If I do decide to remove, I will notify the user by email (will implement notification system later)
