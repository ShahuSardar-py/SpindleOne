from app.extensions import db

class User(db.Model):
    user_id= db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique= True, nullable= False)
    password_hash= db.Column(db.String(128), nullable= False)
    created_at= db.Column(db.DateTime, default=db.func.current_timestamp())

class ModuleAcess(db.Model):
    id=  db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    module_name = db.Column(db.String(50), nullable= False)


    

