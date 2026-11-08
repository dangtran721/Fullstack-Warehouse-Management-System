from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.security import create_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User,UserRole

@pytest.fixture()
def c():
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(e);f=sessionmaker(bind=e);s=f();a=User(username='admin',email='a@x.com',password_hash=hash_password('Password1'),role=UserRole.ADMIN);u=User(username='staff',email='s@x.com',password_hash=hash_password('Password1'),role=UserRole.STAFF);s.add_all([a,u]);s.commit();at,_=create_token(subject=a.id,token_type='access',expires_delta=timedelta(minutes=5));st,_=create_token(subject=u.id,token_type='access',expires_delta=timedelta(minutes=5));s.close()
 def db():
  x=f()
  try:yield x
  finally:x.close()
 app.dependency_overrides[get_db]=db
 with TestClient(app) as x:yield x,{'Authorization':f'Bearer {at}'},{'Authorization':f'Bearer {st}'}
 app.dependency_overrides.clear();Base.metadata.drop_all(e)
def ids(c):
 a=c[1];cat=c[0].post('/api/v1/categories',headers=a,json={'name':'c'}).json()['id'];u=c[0].post('/api/v1/units',headers=a,json={'name':'unit','code':'U'}).json()['id'];p=c[0].post('/api/v1/products',headers=a,json={'sku':'P','name':'p','category_id':cat,'unit_id':u}).json()['id'];w1=c[0].post('/api/v1/warehouses',headers=a,json={'code':'W1','name':'one'}).json()['id'];w2=c[0].post('/api/v1/warehouses',headers=a,json={'code':'W2','name':'two'}).json()['id'];sup=c[0].post('/api/v1/suppliers',headers=a,json={'code':'S','name':'s'}).json()['id'];imp=c[0].post('/api/v1/imports',headers=a,json={'warehouse_id':w1,'supplier_id':sup,'lines':[{'product_id':p,'quantity':'5'}]}).json()['id'];c[0].post(f'/api/v1/imports/{imp}/confirm',headers=a);return w1,w2,p
def test_transfer_adjustment_alert(c):
 w1,w2,p=ids(c);body={'source_warehouse_id':w1,'destination_warehouse_id':w2,'lines':[{'product_id':p,'quantity':'3'}]};o=c[0].post('/api/v1/transfers',headers=c[2],json=body).json()['id'];assert c[0].post(f'/api/v1/transfers/{o}/confirm',headers=c[2]).status_code==200;assert c[0].post(f'/api/v1/transfers/{o}/confirm',headers=c[2]).status_code==409
 bad=c[0].post('/api/v1/transfers',headers=c[1],json={**body,'lines':[{'product_id':p,'quantity':'3'}]}).json()['id'];assert c[0].post(f'/api/v1/transfers/{bad}/confirm',headers=c[1]).status_code==409
 assert c[0].post('/api/v1/adjustments',headers=c[2],json={'warehouse_id':w2,'product_id':p,'quantity_delta':'1','reason':'count'}).status_code==403
 assert c[0].post('/api/v1/adjustments',headers=c[1],json={'warehouse_id':w2,'product_id':p,'quantity_delta':'-4','reason':'count'}).status_code==409
 assert c[0].put(f'/api/v1/inventory/{w2}/{p}/threshold',headers=c[1],json={'min_quantity':'3'}).status_code==200
 assert len(c[0].get('/api/v1/alerts/low-stock',headers=c[2]).json())==1

def test_transfer_and_movement_history(c):
 w1,w2,p=ids(c); body={'source_warehouse_id':w1,'destination_warehouse_id':w2,'lines':[{'product_id':p,'quantity':'2'}]}
 transfer=c[0].post('/api/v1/transfers',headers=c[2],json=body).json()['id']
 assert c[0].get('/api/v1/transfers',headers=c[2]).json()[0]['id']==transfer
 assert c[0].get('/api/v1/transfers',headers=c[2],params={'warehouse_id':w2,'status':'DRAFT'}).json()[0]['id']==transfer
 assert c[0].post(f'/api/v1/transfers/{transfer}/confirm',headers=c[2]).status_code==200
 adjustment=c[0].post('/api/v1/adjustments',headers=c[1],json={'warehouse_id':w2,'product_id':p,'quantity_delta':'1','reason':'count'}); assert adjustment.status_code==201
 transfer_movements=c[0].get('/api/v1/inventory-movements',headers=c[2],params={'movement_type':'TRANSFER','product_id':p}).json()
 adjustment_movements=c[0].get('/api/v1/inventory-movements',headers=c[2],params={'movement_type':'ADJUSTMENT','warehouse_id':w2}).json()
 assert len(transfer_movements)==2 and {item['warehouse_id'] for item in transfer_movements}=={w1,w2}
 assert len(adjustment_movements)==1 and adjustment_movements[0]['quantity_delta']=='1.000'
