# User-based login details

When logging in the very first user sees modal dialog `Select session` and must choose an experimental session. As long as one user is logged in, the consecutive users do not see this modal dialog. Pressing  outside the modal or closing with `X` causes  unsuccessful login and landing back on the login page.

## Multiple users:

Any number of users can be logged in at the same time if:
* they belong to the same proposal,
* they are **staff**.

Users, who are not part of the proposal, can not login. After unsuccessful login attempt the user should see the message: “Authentication failed”.

The first logged in user automatically becomes an **active user**. The **active user** is **in control** and the other users are **observers**.

The **active user** should be able to force logout **observers**, except **staff**.

**Observers** can remain logged in even if the **active user** logs out.

The **active user** can change proposal without signing out. This automatically log out any **observers** that are not part of the new proposal, except **staff**. Users can only choose proposals they belong to.

## Control:

It should be clear who is **in control** (hostname of the machine should be included to know if its remote or on the beamline) and who are the **observers**.

**Observers** can ”ask for control”, **active user** can give or deny control.

There is a timeout so an **observer** does not stay waiting for the control forever. After the timeout the user will get control (if there was no deny signal from **active user**). This feature is enabled by default, but can be disabled.

**Staff** can always “take control” or “ask for control”, even if the “get control after time out” feature is disabled.

The **active user** should be able to give control to any specific user (**observer** or **staff**).

If the **active user** logs out, any of the **observers** can ”ask for control”, and this user will immediately become the **active user**.

## New login:

Meaning: login of already logged in user in another browser, browser tab or window, computer, etc.

Already logged users (whether they are **active**, **observers** or **staff**) can always make a new login.

New login inherits all session data such as queues, control status, drawn points etc.

After new login the old one is quit silently and immediately.

## User with **staff** privileges

They can always:
* Login - they do not need to be part of any proposal (it does not need to be checked to let them login). After login they see the `Select session` modal with the list of proposals they belong to. They could choose any proposal from it. If they type in a number or keyword they search through full list of proposals (even the ones they do not belong to) and they can select each one.
* Logout any user (**active** or **observer**).
* Take and move control from user to another one.
* Change proposal without logging out.
* Restart the server

## Sessions:

If user login and there is session MXCuBE will use it – applies to **staff** members and common users.

If user login and there is no sesion the MXCuBE creates new one applies to **staff** members and common users.

If they change proposal what happens with the session is covered above.

## Improper logout (without sign out button):

Closing or crashing browser of last logged in user activates an “idle timeout” (15 minutes for example as default value). If there is any **active user** or **observer** still logged in, the timeout will not be activated.

After the idle timeout, user data (points, queues etc.) is lost.

If the user logs in again before the end of the “idle timeout”,  this data will be still available (this covers closing MXCuBE by mistake).

If the **active user** logged out improperly, the **observers** can “ask for control” and it will be given to them after certain time (mentioned in 3.3.) since there is no “deny” signal from the **active user**.

Users who are not part of the proposal need to wait for the idle timeout to pass until the formerly **active user's** data is cleaned. After that time any user can login.

**Staff** can kick out any idle user (or restart the server) so that the formerly **active user**’s data is cleaned, and any user can login immediately. Restarting  server causes logging out every user.
