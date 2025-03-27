from fastapi import Request, status, Response
from database.auth import verify_access_token

# middleware: check access_token before run into api
async def check_access_token(request: Request, call_next):
    # ignore /login and /static, ...
    if request.url.path in ["/login", "/"] or request.url.path.startswith("/static") or request.url.path.startswith("/api/v1"):
        return await call_next(request)
    try:
        token = request.cookies.get("access_token")
        if not token or not verify_access_token(token):
            response = Response(status_code=status.HTTP_302_FOUND)
            response.set_cookie(
                key="access_token",
                value="",
                httponly=True,
                secure=False, # replace = True in practice (HTTPS)
                max_age=0,
                samesite="lax"
            )
            response.headers["Location"] = "/login"
            return response
    except:
        # delete cookie if verify is error
        response = Response(status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value="",
            httponly=True,
            secure=False, # replace = True in practice (HTTPS)
            max_age=0,
            samesite="lax"
        )
        response.headers["Location"] = "/login"
        return response
    # after all check, run into api
    return await call_next(request)

# middleware: add secure headers after handle request in apis
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

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