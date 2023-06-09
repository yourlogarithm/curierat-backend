from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from classes.database_provider import DatabaseProvider
from dependencies import get_current_active_user
from security.access_level import AccessLevel
from security.register_form import RegisterForm
from security.user import User
from security.registered_user import RegisteredUser


class UsersRouter:
    router = APIRouter()

    @staticmethod
    @router.get('/users')
    async def get_all_users(current_user: Annotated[User, Depends(get_current_active_user)]):
        return list(DatabaseProvider.users().find({}, {'_id': 0, 'password': 0}))

    @staticmethod
    @router.get('/users/{username}')
    async def read_users_me(username, current_user: Annotated[User, Depends(get_current_active_user)]):
        if current_user.access_level >= AccessLevel.Moderator:
            user = RegisteredUser.get(username)
            if user:
                return user
            raise HTTPException(status_code=404, detail='User not found')
        elif current_user.username != username:
            raise HTTPException(status_code=403, detail='Forbidden')
        return current_user

    @staticmethod
    @router.post('/users/add')
    async def add_user(regiser_form: RegisterForm, current_user: Annotated[User, Depends(get_current_active_user)]):
        # only admins can add moderators and admins, moderators can add users with lower access level
        if current_user.access_level < AccessLevel.Moderator or (current_user.access_level == AccessLevel.Moderator and regiser_form.access_level >= AccessLevel.Moderator):
            raise HTTPException(status_code=403, detail='Forbidden')
        if DatabaseProvider.users().find_one({'username': regiser_form.username}):
            raise HTTPException(status_code=400, detail='Username already registered')
        DatabaseProvider.users().insert_one(regiser_form.to_user().dict())
        return {'message': 'User added'}

    @staticmethod
    @router.delete('/users/delete/{username}')
    async def delete_user(username: str, current_user: Annotated[User, Depends(get_current_active_user)]):
        if current_user.access_level < AccessLevel.Moderator:
            raise HTTPException(status_code=403, detail='Forbidden')
        user = RegisteredUser.get(username)
        if user.access_level >= AccessLevel.Moderator and current_user.access_level < AccessLevel.Admin:
            raise HTTPException(status_code=403, detail='Forbidden')
        if DatabaseProvider.users().delete_one({'username': username}).deleted_count == 0:
            raise HTTPException(status_code=404, detail='User not found')
        return {'message': 'User deleted'}
