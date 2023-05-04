from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from classes.database import DatabaseProvider
from classes.form import Form
from classes.route import Route
from classes.package import Package
from dependencies import get_current_active_user
from security.access_level import AccessLevel
from security.user import User

router = APIRouter()

_BASE_ACCESS_LEVELS = AccessLevel.OFFICE,
_PRIVILEGED_ACCESS_LEVELS = AccessLevel.OFFICE, AccessLevel.ADMIN


@router.post("/packages/calculate_price")
async def calculate_price(form_: Form, current_user: Annotated[User, Depends(get_current_active_user)]):
    if current_user.access_level not in _BASE_ACCESS_LEVELS + _PRIVILEGED_ACCESS_LEVELS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return Package.get_price(form_)


@router.post("/packages/add")
async def package(package_: Package, current_user: Annotated[User, Depends(get_current_active_user)]):
    if current_user.access_level not in _BASE_ACCESS_LEVELS + _PRIVILEGED_ACCESS_LEVELS:
        raise HTTPException(status_code=403, detail="Forbidden")
    current_timestamp = datetime.now()
    routes = Route.get_best_routes(package_.office, package_.destination, current_timestamp)
    if len(routes) == 0:
        raise HTTPException(status_code=404, detail="No route found")
    best = next(route for route in routes if route.current_weight + package_.weight <= route.transport.max_weight)
    if best is None:
        raise HTTPException(status_code=400, detail="No transport available")
    best.add_package(package_)
    return str(best.id)


@router.get("/packages/{username}")
async def package(username: str, current_user: Annotated[User, Depends(get_current_active_user)]):
    if current_user.access_level not in _PRIVILEGED_ACCESS_LEVELS:
        raise HTTPException(status_code=403, detail="Forbidden")
    packages = list(DatabaseProvider.routes().aggregate([
        {"$match": {"packages.username": username}},
        {"$unwind": "$packages"},
        {"$match": {"packages.username": username}},
    ]))
    return packages


@router.get("/packages/close_packages/{route_id}/{destination}")
async def close_packages(route_id: str, destination: str, current_user: Annotated[User, Depends(get_current_active_user)]):
    if current_user.access_level < AccessLevel.MODERATOR and current_user.access_level != AccessLevel.COURIER:
        raise HTTPException(status_code=403, detail="Forbidden")
    return str(DatabaseProvider.routes().update_one(
        {"_id": route_id},
        {"$set": {"packages.$[elem].closed": True}},
        array_filters=[{"elem.destination": destination}]
    ).upserted_id)
