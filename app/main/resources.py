from flask import render_template, jsonify, request
from app.main.models import User, Room, BlacklistToken, UserSchema, RoomSchema
from flask_restful import Resource, reqparse
from app.db import db
from pymongo.errors import DuplicateKeyError
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required,
                                get_jwt_identity, get_raw_jwt)

parser = reqparse.RequestParser()
parser.add_argument('username',
                    help='This field cannot be blank',
                    required=True)
parser.add_argument('password',
                    help='This field cannot be blank',
                    required=True)
user_schema = UserSchema()


class AllUsers(Resource):
    def get(self):
        cur = db.find_all({}, 'users')
        users = []
        for doc in cur:
            users.append(user_schema.dump(doc)['username'])
        return users

    def delete(self):
        User.delete()
        return {'message': 'deleted all users'}


class Register(Resource):
    def post(self):
        data = parser.parse_args()
        # First, does the requested user account exist?
        new_user = User(data['username'])
        if not User.find_user(new_user):
            new_user.set_password(data['password'])
            db.create(user_schema.dump(new_user), 'users')
            # JWT stuff
            access_token = create_access_token(identity=data['username'])
            refresh_token = create_refresh_token(identity=data['username'])

        else:
            return {'error': 'Username already exists'}, 500

        return {
            'success': data['username'] + ' added!',
            'access_token': access_token,
            'refresh_token': refresh_token
        }, 200


class UserLogin(Resource):
    def post(self):
        data = parser.parse_args()
        db_user = User.find_user(User(data['username']))
        if not db_user:
            return {
                'message': 'User {} doesn\'t exist'.format(data['username'])
            }
        # same password?
        # print('****', user_schema.load(db_user))
        if user_schema.load(db_user).check_password(data['password']):
            access_token = create_access_token(identity=data['username'])
            refresh_token = create_refresh_token(identity=data['username'])
            return {
                'message': 'Login successful',
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        else:
            return {"message": "Login unsuccessful"}


class UserLogoutAccess(Resource):
    @jwt_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            blacklisted_token = BlacklistToken(jti)
            blacklisted_token.add()

            return {'message': 'Access token has been revoked'}, 200
        except:
            return {
                'message': 'Something went wrong with access token on logout'
            }, 500


class UserLogoutRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            blacklisted_token = BlacklistToken(jti)
            blacklisted_token.add()
            return {'message': 'Refresh token has been revoked'}, 200
        except:
            return {
                'message': 'Something went wrong with refresh token on logout'
            }, 500


class TokenRefresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        return {'access_token': access_token}


class TestResource(Resource):
    @jwt_required
    def get(self):
        return {'answer': 42}
