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

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Items App"

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Authorization

@app.route('/login')
def showLogin():
    if 'username' not in login_session:
        logged_in = False
    else:
        logged_in = True 
        return redirect(url_for('catalog'))

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state, logged_in=logged_in)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' "> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = json.loads(login_session.get('credentials'))
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('catalog'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# App files

@app.route('/')
@app.route('/catalog/')
def catalog():
    """
    Home page
    """
    if 'username' not in login_session:
        logged_in = False
    else:
        logged_in = True 

    categories = session.query(Category).order_by(asc(Category.name))
    latest_items = session.query(Item, Category).filter(Item.category_id == Category.id).order_by(desc(Item.id)).limit(10).all()

    return render_template('catalog.html', categories=categories, latest_items=latest_items, logged_in=logged_in)


@app.route('/catalog/<string:category_name>/items/')
def categoryItems(category_name):
    """
    Display items by category
    """
    if 'username' not in login_session:
        logged_in = False
    else:
        logged_in = True 

    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=category.id).all()
    items_amount = len(items)
    # return category_id
    return render_template('category-items.html', items=items,
            items_amount=items_amount, category_name=category_name,
            categories=categories, logged_in=logged_in)


@app.route('/catalog/<string:category_name>/<string:item_name>/')
def categoryItem(category_name, item_name):
    """
    Displays a single item
    """

    if 'username' not in login_session:
        logged_in = False
    else:
        logged_in = True 
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(category_id=category.id).filter_by(name=item_name).one()
    return render_template('category-item.html', item=item, logged_in=logged_in)


@app.route('/catalog/item/new/', methods=['GET', 'POST'])
def addItem():
    """
    Adds a new Catalog item to a specific category
    """

    if 'username' not in login_session:
        logged_in = False
        return redirect('/login')
    else:
        logged_in = True 

    if request.method == 'POST':
        if request.form['name']:
            new_item = Item(name=request.form['name'], description=request.form['description'], category_id=request.form['category'])
            session.add(new_item)
            session.commit()
            return redirect(url_for('catalog'))
        else:
            categories = session.query(Category).order_by(asc(Category.name))
            return render_template('add-item.html', categories=categories
                    , logged_in=logged_in)
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('add-item.html', categories=categories
                , logged_in=logged_in)


@app.route('/catalog/<string:item_name>/edit/', methods=['GET', 'POST'])
def editItem(item_name):
    """
    Edit an existing item
    """

    if 'username' not in login_session:
        logged_in = False
        return redirect('/login')
    else:
        logged_in = True 

    item = session.query(Item).filter_by(name=item_name).one()
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
            return render_template('edit-item.html',
                    categories=categories, item=item, logged_in=logged_in)

    else:
        return render_template('edit-item.html',
                categories=categories, item=item, logged_in=logged_in)


@app.route('/catalog/<string:item_name>/delete/', methods=['GET', 'POST'])
def deleteItem(item_name):
    """
    Deletes an Item
    """

    if 'username' not in login_session:
        logged_in = False
        return redirect('/login')
    else:
        logged_in = True 

    item = session.query(Item).filter_by(name=item_name).one()
    if request.method == 'POST':
        session.delete(item)
        flash('%s Successfully Deleted' % item.name)
        return redirect(url_for('catalog'))
    else:
        return render_template('delete-item.html', item=item, logged_in=logged_in)


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
    app.run(host='0.0.0.0', port=8000)
