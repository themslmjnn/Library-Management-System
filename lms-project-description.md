# Library Management System

--- Roles
1. System admin 
2. Library admin
3. Receptionist
4. Member
5. Guest

--- Modules
1. Auth
2. Users
3. Books
4. Inventories
5. Loans
6. Subscriptions
7. Payments
8. Online reading

--- Tech Stack
1. Backend: Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, Pydantic, JWT, Pytest, Docker, ReSend, Logging & Structlog
2. Frontend: HTML, CSS, JS, ReactJS
Git & GitHub

# Users module
1. System admin
Can create users (library_admin, receptionist, member, guest), (system admin is not created through API). Get users (everyone except system admins), can sort/filter/search system admins do not appear. Get user by id (except system admins). Update users - can update users personal info (role and is_active is not changed through API). Deactivate/activate users. Update users' password (a reset link is sent to user, admin can not hardcore password)
2. Library admin
Can create members & guests. Get users (everyone except system and library admins), can sort/filter/search (system and library admins do not appear). Get users (only receptionist,member, guest). Can not update users info or password or deactivate/activate them. Can change only their account and password.
3. Receptionist
Can create members & guests. Get users (only members and guests, receptionists, admins do not appear), sort/filter/search (receptionists, admins do not appear). Get users by id (only members and guests). Can not update users info or password or deactivate/activate them. Can change only their account and password.
4. Members and guests
Can create account using public endpoint.Can update their info and password. Can deactivate their account, delete or activate their account. Get only their account.
When a staff creates account for users an invite token (link) is sent to their email. Upon activating their account they can use their profiles. For self-registered accounts activation code is sent then they can copy paste it to activate their account. When a staff creates for account for user it is registered as guest, if they activate their account they will be promoted to member. Guest can only view books. Member can loan books, view, control their account, buy subscriptions on their own using their account. Guest also can do this but only library staff has to do for them.
Question: I have endpoints where authenticated users can get their info, update without providing their id. Also admin can get his info through get_user_by_id_admin endpoint, staff can get their info using get_user_by_id_staff. Should I forbid admin and staff to get able to get their info through these endpoints and only use user/me endpoint?


# Auth module
It has 5 functions: login, log out, activate with token, activate with code, refresh token, reset password
Auth flow:
1. Admin creates account for invite token is sent to email of the user (post /user) ---> then user gets link, opens, frontend extracts token, hands it to backend (post /auth/activate_with_token) activates account ---> then login (/auth/login) --> -> then refresh token is given
2. User creates account using public endpoint, activation code is sent to their email (post /user/me) --> user gets email, copy pastes code then (post /auth/activation_with_code) activates account then login (/auth/login) -> then refresh token is given
3. Log out invalidates the session (refresh token hash, family, expires at, token version are invalidated). hardcorded log out.
4. Refresh token -> log in set refresh token (/auth/login) stores it in cookie, then (/auth/refresh_token) get cookie and gives new access token
5. Refresh token is expired, session is invalidated, user is logged out.

# Books module
Admins can create books (instances), archive, update, get all books search/filter/sort, get book by id
Others can only view all books, search/filter/sort and get book by id 


# Inventories
Admins can create inventories (how many copy of a book is added to the library), update (quantity), delete, get all, get by id
Receptionist can view total amount of copies of books, search/sort/filter, get by id

# Loans
Admins/receptionist can create loans for member/guests, return, get all and get by id
admins can delete loans, update
members and guests can create loans for their own, they can not return on their own, get their loans, get loan by id


# Subscriptions
admins can create subscriptions tiers, delete, view, update
receptionist can only view

admins, receptionist can buy subscriptions on behalf of members and guests
users can buy subscriptions on their own
they can not have two subscriptions at the same time
in order to buy a new subscription they have to terminate current one


free tier
1. montly loan limit - 5
2. concurrent loan limit - 3
3. no online reading
4. no downloading pdf
5. loan fee 10$ for each book

premium tier
1. montly loan limit - 10
2. concurrent loan limit - 5
3. online reading
4. downloading pdf
5. no loan fee
6. price 20$/month

Books pdf files are stored in s3 storage, downloading pdf is available for premium users, online reading is displayed in an interactive format

payment can be online (visa/mastercard), cash, and pay through terminal transaction number is recorded on db