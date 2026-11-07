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
from app.models.user import User, UserRole

@pytest.fixture()
def client():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool); Base.metadata.create_all(engine); factory=sessionmaker(bind=engine)
    s=factory(); admin=User(username="admin",email="admin@x.com",password_hash=hash_password("Password1"),role=UserRole.ADMIN); staff=User(username="staff",email="staff@x.com",password_hash=hash_password("Password1"),role=UserRole.STAFF); s.add_all([admin,staff]);s.commit()
    at,_=create_token(subject=admin.id,token_type="access",expires_delta=timedelta(minutes=5)); st,_=create_token(subject=staff.id,token_type="access",expires_delta=timedelta(minutes=5));s.close()
    def db():
        x=factory()
        try: yield x
        finally: x.close()
    app.dependency_overrides[get_db]=db
    with TestClient(app) as c: yield c,{"Authorization":f"Bearer {at}"},{"Authorization":f"Bearer {st}"}
    app.dependency_overrides.clear(); Base.metadata.drop_all(engine)

def setup(c):
    a=c[1]; cat=c[0].post('/api/v1/categories',headers=a,json={'name':'goods'}).json()['id']; unit=c[0].post('/api/v1/units',headers=a,json={'name':'piece','code':'PCS'}).json()['id']; product=c[0].post('/api/v1/products',headers=a,json={'sku':'P1','name':'Product','category_id':cat,'unit_id':unit}).json()['id']; wh=c[0].post('/api/v1/warehouses',headers=a,json={'code':'WH1','name':'Warehouse'}).json()['id']; sup=c[0].post('/api/v1/suppliers',headers=a,json={'code':'SUP1','name':'Supplier'}).json()['id']; return wh,sup,product

def test_import_confirm_idempotency_cancel_and_inventory(client):
    wh,sup,p=setup(client); body={'warehouse_id':wh,'supplier_id':sup,'lines':[{'product_id':p,'quantity':'10.500'}]}
    created=client[0].post('/api/v1/imports',headers=client[2],json=body); assert created.status_code==201
    oid=created.json()['id']; assert client[0].get('/api/v1/inventory',headers=client[2]).json()==[]
    assert client[0].post(f'/api/v1/imports/{oid}/confirm',headers=client[2]).status_code==200
    assert client[0].post(f'/api/v1/imports/{oid}/confirm',headers=client[2]).status_code==409
    assert client[0].get('/api/v1/inventory',headers=client[2]).json()[0]['quantity']=='10.500'
    draft=client[0].post('/api/v1/imports',headers=client[1],json=body).json()['id']; assert client[0].post(f'/api/v1/imports/{draft}/cancel',headers=client[1]).status_code==204; assert client[0].post(f'/api/v1/imports/{draft}/confirm',headers=client[1]).status_code==409

def test_export_staff_stock_rule_admin_negative_and_rollback(client):
    wh,sup,p=setup(client); imp=client[0].post('/api/v1/imports',headers=client[1],json={'warehouse_id':wh,'supplier_id':sup,'lines':[{'product_id':p,'quantity':'5'}]}).json()['id']; client[0].post(f'/api/v1/imports/{imp}/confirm',headers=client[1])
    body={'warehouse_id':wh,'lines':[{'product_id':p,'quantity':'6'}]}; order=client[0].post('/api/v1/exports',headers=client[2],json=body).json()['id']; assert client[0].post(f'/api/v1/exports/{order}/confirm',headers=client[2]).status_code==409
    assert client[0].get('/api/v1/inventory',headers=client[1]).json()[0]['quantity']=='5.000'
    admin_order=client[0].post('/api/v1/exports',headers=client[1],json=body).json()['id']; assert client[0].post(f'/api/v1/exports/{admin_order}/confirm',headers=client[1]).status_code==200
    assert client[0].get('/api/v1/inventory',headers=client[1]).json()[0]['quantity']=='-1.000'
