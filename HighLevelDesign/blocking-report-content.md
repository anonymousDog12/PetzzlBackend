# Blocking

## Functionalities

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


## Tech Design

- No need to use middleware, service layer, or django signals


### Backend Implementation (Django)
1. Blocking and Unblocking API:
   - Create API endpoints to handle blocking and unblocking actions. These will update the BlockedUser model.
   - Example:
     ```py
     def block_user(request, user_to_block_id):
         # Logic to block a user
         pass

     def unblock_user(request, user_to_unblock_id):
         # Logic to unblock a user
         pass
     ```
2. Feed and Dashboard Modification:
   - Modify the get_feed function and any other relevant queries to filter out posts from blocked users.
   - Implement logic in the dashboard view to show a message for blocked user profiles.
3. Handling Interactions:
   - For historical likes, you can create a script or function to remove likes between the blocker and the blocked users whenever a new block is created.
   - Ensure future interactions like new likes are prohibited by checking the BlockedUser model during the creation of such interactions.


### Frontend Implementation (React/Redux)

1. Update Redux State on Block/Unblock:
   - When a user blocks or unblocks another user, update the Redux state to reflect this change.
   - This will help in managing the visibility of posts and interactions on the client side.
2. Conditional Rendering:
   - Use the Redux state to conditionally render posts, dashboard information, and interaction options based on whether a user is blocked.
3. Sync with Backend:
   - Ensure that actions like blocking/unblocking are synced with the backend via API calls, and the frontend state is updated accordingly.


---

# Report Content

## Functionalities

- User can click on 3 dots on the top right corner of each post to report content
- User can also do that from post detail page
- Reported content will be immediately invisible to the current user
- Users are given further options to block
- Triggers an email to me, as well as writing it to database
- If I do decide to remove, I will notify the user by email (will implement notification system later)