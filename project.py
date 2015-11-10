from flask import Flask, render_template, request, redirect, jsonify, url_for, flash

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
@app.route('/catalog/')
def catalog():
    """
    Home page
    """
    categories = session.query(Category).order_by(asc(Category.name))
    latest_items = session.query(Item, Category).filter(Item.category_id == Category.id).order_by(desc(Item.id)).limit(10).all()

    return render_template('catalog.html', categories=categories, latest_items=latest_items)


@app.route('/catalog/<string:category_name>/items/')
def categoryItems(category_name):
    """
    Display items by category
    """
    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=category.id).all()
    items_amount = len(items)
    # return category_id
    return render_template('category-items.html', items=items,
            items_amount=items_amount, category_name=category_name,
            categories=categories)


@app.route('/catalog/<string:category_name>/<string:item_name>/')
def categoryItem(category_name, item_name):
    """
    """
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(category_id=category.id).filter_by(name=item_name).one()
    return render_template('category-item.html', item=item)


@app.route('/catalog/item/new/', methods=['GET', 'POST'])
def addItem():
    """
    Adds a new Catalog item to a specific category
    """
    if request.method == 'POST':
        if request.form['name']:
            new_item = Item(name=request.form['name'], description=request.form['description'], category_id=request.form['category'])
            session.add(new_item)
            session.commit()
            return redirect(url_for('catalog'))
        else:
            categories = session.query(Category).order_by(asc(Category.name))
            return render_template('add-item.html', categories=categories)
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('add-item.html', categories=categories)


@app.route('/catalog/<string:item_name>/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(item_name, item_id):    
    """
    Edit an existing item
    """

    item = session.query(Item).filter_by(id=item_id).one()
    categories = session.query(Category).order_by(asc(Category.name))

    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
            item.description = request.form['description']
            item.category_id = request.form['category']
            session.add(item)
            session.commit()
            return redirect(url_for('catalog'))

        else:
            return render_template('edit-item.html', categories=categories, item=item)

    else:
        return render_template('edit-item.html', categories=categories, item=item)


@app.route('/catalog/<string:item_name>/delete/')
def deleteItem(item_name):
    return render_template('delete-item.html')


#JSON
@app.route('/catalog/categories/JSON/')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[category.serialize for category in categories])


@app.route('/catalog/category/<int:category_id>/JSON/')
def categoryJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    return jsonify(category=category.serialize)


@app.route('/catalog/category/<int:category_id>/items/JSON/')
def categoryItemsJSON(category_id):
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(items=[item.serialize for item in items])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
