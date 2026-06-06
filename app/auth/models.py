from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    user_id= db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique= True, nullable= False)
    password_hash= db.Column(db.String(128), nullable= False)
    role = db.Column(db.String(50), nullable= False) # e.g. SuperAdmin, store keeper, HR, accounts
    created_at= db.Column(db.DateTime, default=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ModuleAcess(db.Model):
    id=  db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    module_name = db.Column(db.String(50), nullable= False)


    

