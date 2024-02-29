# Post Comment

## Functionalities

- Any logged-in user can comment on any post, unless they are blocked or blockee (in that case they should not have seen the posts in the first place)
- But comment should be posted as "pet", not as human user.
- Comment itself can have likes (I wonder if this can be done later, depending on how complicated it is)
- [Future] Comment reply mechnism
  - No "nested" comment. So when reply, we have @<pet_id>, but not hierachical reply like reddit
    - Later for hte UI maybe we can restrict the layers to be 2

- [Future] - Add comment filtering

Content Safety: 
- Report comment
- Hide comment
- Block user from comment

Other options

- Delete comment (for now, can omitediting)

## Glossary

- Post Reactions
  - These refers to "like" button, but NOT comments
- Post Comments
- Comment Reactions
  - These refers to reactions to comment

These can be a bit vague. Wonder if there are better phrases


## UI Reminders

- Pagination
- Expand / Collapse


## DB Design


**Post Comments**

- Comment ID
- Pet Profile ID 
- Post ID
- Content
- Created At
- Updated At

**Comment Reactions** (a separating django app from comment)
- Will add later
