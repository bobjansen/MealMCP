"""
OAuth template rendering with external HTML/CSS files.
Cleaner separation of concerns.
"""

import os
from urllib.parse import urlencode
from string import Template


def _build_oauth_params(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    response_type: str = "code",
) -> str:
    """Build OAuth parameter string for URLs."""
    params = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    return urlencode(params)


def _load_template(template_name: str) -> str:
    """Load template file from templates directory."""
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "oauth", f"{template_name}.html"
    )
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Template {template_name}.html not found at {template_path}"
        )


def generate_login_form(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    response_type: str = "code",
) -> str:
    """Generate the OAuth login form using template."""
    template_content = _load_template("login")
    template = Template(template_content)

    oauth_params = _build_oauth_params(
        client_id, redirect_uri, scope, state, code_challenge, code_challenge_method
    )

    return template.substitute(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        response_type=response_type,
        oauth_params=oauth_params,
    )


def generate_register_form(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Generate the user registration form using template."""
    template_content = _load_template("register")
    template = Template(template_content)

    login_params = _build_oauth_params(
        client_id,
        redirect_uri,
        scope,
        state,
        code_challenge,
        code_challenge_method,
        "code",
    )

    return template.substitute(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        login_params=login_params,
    )


def generate_error_page(
    error_message: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Generate an error page with retry link using template."""
    template_content = _load_template("error")
    template = Template(template_content)

    retry_params = _build_oauth_params(
        client_id, redirect_uri, scope, state, code_challenge, code_challenge_method
    )

    return template.substitute(
        error_message=error_message.replace('"', "&quot;"),
        retry_params=retry_params,
    )
