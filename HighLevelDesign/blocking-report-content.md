# Blocking

## Functionalities

- Block can be initiated from
  - User Dashboard, with the ... from header section
  - After user wants to click on report from
    - Feed page
    - Other user post detail page


Dashboard
- After blocking, on user dashboard only pet id, pet name, and profile pic will be shown
- Mutually true


- Blocking a user will block ALL the pet profiles owned by that user
- To manage blocked users, user can see the list in settings, and un-block a user
- Need to wait 48 hours to re-block a user
- List will show "<pet_id> and associated profiles"


Feed Visibility
- Blocked users' posts won't show up on Feed
- Mutually true


Interactions --- Mutually true
- Historical likes [Updated on 1/6/24]
  - ~~Historical likes will be mutually removed~~ 
  - Historical likes will be preserved; nothing gets deleted from the database.
  - For authenticated users, the liker list for each post excludes pet profiles that the user has blocked.
  - For unauthenticated users, the liker list includes all pet profiles that have liked the post.
  - This approach ensures interaction data integrity and adapts to the user's privacy preferences. If a user unblocks another, their previously hidden likes will reappear in the liker list, thus no data is lost.

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
- User can also do that from post detail page, also 3 dots


- Categorization of Reports: Allow users to categorize their reports (e.g., spam, harassment, inappropriate content). This can help in prioritizing and managing reports.


- Confirmation Message: After a user reports a post, displaying a confirmation message can reassure them that their report has been filed.

- Reported content will be immediately invisible to the current user


- Users are given further options to block
- Triggers an email to me, as well as writing it to database



- If I do decide to remove, I will notify the user by email (will implement notification system later)
