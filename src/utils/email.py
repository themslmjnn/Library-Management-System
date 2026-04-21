def send_invite_email(email: str, invite_token: str) -> None:
    print(f'Email: {email}')
    print(f'Invite token: {invite_token}')


def send_account_activation_code(email: str, code: str) -> None:
    print(f'Email: {email}')
    print(f'Activation code: {code}')