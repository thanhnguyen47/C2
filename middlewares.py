from fastapi import Request, status
from fastapi.responses import Response, RedirectResponse
from database.auth import verify_access_token, get_current_user

# middleware: check access_token before run into api
async def check_access_token(request: Request, call_next):
    # ignore /login and /static, ...
    if request.url.path in ["/login", "/", "/favicon.ico", "/register", "/verify"] or request.url.path.startswith("/static") or request.url.path.startswith("/api/v1") or request.url.path.startswith("/ddos-bot/beacon"):
        return await call_next(request)
    try:
        token = request.cookies.get("access_token")
        print("token: ", token)
        user = None
        if token:
            user = verify_access_token(token)
            print("user: ", user)
        if not token or not user:
            reason = "No token" if not token else "Invalid or expired token"
            print("Redirecting to login, reason: ", reason)
            response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            response.set_cookie(
                key="access_token",
                value="",
                httponly=True,
                secure=False, # replace = True in practice (HTTPS)
                max_age=0,
                samesite="lax"
            )
            return response
        
        request.state.user = await get_current_user(user)
        # after all check, run into api
        response: Response =  await call_next(request)
        return response
    except Exception as e:
        print("middleware: ", e)
        # delete cookie if verify is error
        response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value="",
            httponly=True,
            secure=False, # replace = True in practice (HTTPS)
            max_age=0,
            samesite="lax"
        )
        return response
    

# middleware: add secure headers after handle request in apis
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    if isinstance(response, Response) and not isinstance(response, RedirectResponse):
        # response.headers["Content-Security-Policy"] = (
        #     "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        # )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "deny"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response