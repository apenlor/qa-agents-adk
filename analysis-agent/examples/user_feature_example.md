## Golden Example: User-Facing Feature

This example shows how to handle a user-centric feature request, often found in less formal documents or meeting notes.

---

#### Input Text:

```text
User Profile Picture Upload

Users are asking for a way to upload their own profile pictures. The feature should be accessible from their account 
settings page. We need to support the usual formats like JPEG and PNG. Let's put a file size limit of 5MB to be safe. 
After a successful upload, the new picture should show up on their profile and in the site header right away.
```

#### Generated Output:

Implement a feature that allows registered users to upload a profile picture from their account settings.
The system should support common image formats (JPEG, PNG), enforce a 5MB file size limit, and immediately display
the new picture across the user's profile and site header.

**Acceptance Criteria:**

* GIVEN a logged-in user is on their account settings page
* WHEN the user clicks the 'Upload Picture' button
* THEN a file selection dialog should open.
* AND WHEN the user selects a valid JPEG or PNG file under 5MB
* THEN the upload is successful and the new picture is displayed on their profile.
* AND THEN the user's avatar in the site header is updated to the new picture.
* AND WHEN the user selects a file larger than 5MB
* THEN an error message indicating the file size limit is shown.
* AND WHEN the user selects an unsupported file type (e.g., GIF)
* THEN an error message indicating invalid format is shown.