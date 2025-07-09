# User-based login details

When logging in the very first user sees modal dialog `Select session` and must choose an experimental session. As long as one user is logged in, the consecutive users do not see this modal dialog.

## Multiple users:

Any number of users can be logged in at the same time if:
* they belong to the same `session`
* they are **staff**.

Users, who are not part of the proposal, can not log in. After unsuccessful login attempt the user should see the message: “Authentication failed”.

The first logged in user automatically becomes an **user in control**. The other users are **observers**.

The **user in control** is able to force logout other users.

**Observers** can remain logged in even if the **user in control** logs out.

The **user in control** can change session without signing out. The users can only see the sessions they have in common - to which all logged-in users belong to. Hence, the list of available sessions displayed is the same for every user. Example:

    User 1 has access to sessions A B C
    User 2 has access to sessions A B
    User 3 has access to session A
    All of them are logged in and see only session A.
    If user 3 logs out, user 1 and 2 will see sessions A and B.
    If only user 1 stays logged in, all the sessions are visible.

## Control:

It should be clear who is **in control** (hostname of the machine should be included to indicate whether it is remote or on the beamline) and who the **observers** are.

Users can ”ask for control” or "take control". The **user in control** can accept or deny the request.

There is a parameter named: TIMEOUT_GIVES_CONTROL which, if enabled, triggers a timeout (30 seconds) after the control request and. If there has been no deny signal in the meantime, the request is accepted automatically. In the current version of MXCuBE, this feature is disabled by default.

The **user in control** is able to "give control" to any other user.

If the **user in control** logs out this role is not passed to any other (logged-in) user. Once logged out the "user in control" is unassigned and the next user that logs in becomes the "user in control". If no new user appears upon re-logging of the former **user in control**, he/she is still in control.

## New login:

A new login occurs when the same user logs into MXCuBE and then opens it again in a separate tab, window, browser, or on another computer.

Currently, two scenarios can occur:

* If the user opens MXCuBE again within **the same browser session** by opening multiple public tabs/windows or multiple private tabs/windows in the same browser, the browser sends the MXCuBE session cookie to the back-end. As a result, the user is automatically logged in within the same  MXCuBE "user session". In this case, the new login inherits all session data, including queues, drawn points, control state etc.

* If the user opens MXCuBE in a **separate browser session**, by opening windows in different browser modes - public vs. private, browser profiles, different browsers or computers, the browser has no MXCuBE session cookie to send. Consequently, the user lands on the login page and must log in again. Once logged in, MXCuBE creates a new "user session" and quits the previous one. There can be only one user session per user at any given time.

## User with **staff** privileges

They can always:
* Login - they do not need to be part of any session, and this is not checked during login procedure. After logging in, they see the `Select session` modal with the list of sessions they belong to. They could choose any session from this list, or if they type in a number or keyword, they can search through full list of sessions, including ones they do not belong to, and they can select each one.
* Logout any user (including the **user in control**).
* Move experimental session timewise - reschedule it.
* Move experimental session beamline-wise.

## Improper logout (without sign out button):

Closing the browser window with a logged-in user might be caused by unpredictable scenarios such as losing internet connection or browser crash, or there might be an automatic data collection over the night. Therefore, only the HTTP session data is cleared, according to the web session expiration time. However, queue, points etc. are not removed or cleared. After logging back in, these data are restored.

Closing the browser without using the sign-out button when user experiments are about to finish must be explicitly resolved by local intervention. Local intervention allows for properly logging out the user and activating the upcoming session.
