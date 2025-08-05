"""
HTML templates for OAuth authentication flows.
Centralized template management to reduce duplication.
"""


def get_base_style() -> str:
    """Get common CSS styles for all forms."""
    return """
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .primary-btn { background: #007bff; color: white; }
        .primary-btn:hover { background: #0056b3; }
        .success-btn { background: #28a745; color: white; }
        .success-btn:hover { background: #1e7e34; }
        .link-section { margin-top: 20px; text-align: center; }
        .link-section a { color: #007bff; text-decoration: none; }
        .error { color: red; }
    """


def generate_login_form(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    response_type: str = "code",
) -> str:
    """Generate the OAuth login form."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MealMCP Authorization</title>
        <style>{get_base_style()}</style>
    </head>
    <body>
        <h2>Authorize MealMCP Access</h2>
        <p>The application <strong>{client_id}</strong> wants to access your MealMCP data.</p>

        <form method="post" action="/authorize">
            <input type="hidden" name="response_type" value="{response_type}">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">

            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>

            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit" class="primary-btn">Authorize</button>
        </form>

        <div class="link-section">
            <p>Don't have an account? <a href="/register_user?{_build_oauth_params(client_id, redirect_uri, scope, state, code_challenge, code_challenge_method)}">Register here</a></p>
        </div>
    </body>
    </html>
    """


def generate_register_form(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Generate the user registration form."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Register for MealMCP</title>
        <style>{get_base_style()}</style>
    </head>
    <body>
        <h2>Create MealMCP Account</h2>

        <form method="post" action="/register_user">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">

            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>

            <div class="form-group">
                <label for="email">Email (optional):</label>
                <input type="email" id="email" name="email">
            </div>

            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>

            <div class="form-group">
                <label for="confirm_password">Confirm Password:</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
            </div>

            <button type="submit" class="success-btn">Register</button>
        </form>

        <div class="link-section">
            <p>Already have an account? <a href="/authorize?{_build_oauth_params(client_id, redirect_uri, scope, state, code_challenge, code_challenge_method, 'code')}">Login here</a></p>
        </div>
    </body>
    </html>
    """


def generate_error_page(
    error_message: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    """Generate an error page with retry link."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Registration Error</title>
        <style>{get_base_style()}</style>
    </head>
    <body>
        <h2>Registration Failed</h2>
        <p class="error">{error_message.replace('"', "&quot;")}</p>
        <div class="link-section">
            <a href="/register_user?{_build_oauth_params(client_id, redirect_uri, scope, state, code_challenge, code_challenge_method)}">Try Again</a>
        </div>
    </body>
    </html>
    """


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
    from urllib.parse import urlencode

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
