from fastapi import HTTPException, Request


def reject_unknown_query_params(request: Request, allowed: set[str]) -> None:
    unknown = set(request.query_params) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise HTTPException(
            status_code=422,
            detail=f"Parámetros de consulta no admitidos: {names}",
        )
