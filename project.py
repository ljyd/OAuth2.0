from flask import Flask, render_template, request, redirect,jsonify, url_for, flash
from flask import session
import random, string

from google.oauth2 import id_token
from google.auth.transport import requests
import json
from flask import make_response
import requests as theRequests

from database_setup import app, db, Restaurant, MenuItem


#Connect to Database and create database session
'''
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
'''

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

# Create anti-forgery state token
@app.route('/login')
def showLogin():
  state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                  for x in range(32))
  session['state'] = state
  return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    token = request.data
    print('Request is: %r' % request)
    print('Data from login.html: %r' % token)


    try:
        # Upgrade the authorization code into a credentials object
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

        print('idinfo is: %r' %idinfo)

        if idinfo['iss'] != 'accounts.google.com':
            raise ValueError('Wrong issuer.')

        g_id = idinfo['sub']
    except ValueError:
        response = make_response(
            json.dumps('Invalid token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response


    stored_access_token = session.get('access_token')
    stored_g_id = session.get('g_id')
    if stored_access_token is not None and g_id == stored_g_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    session['access_token'] = token
    session['g_id'] = g_id

    session['username'] = idinfo['name']
    session['picture'] = idinfo['picture']
    session['email'] = idinfo['email']

    output = ''
    output += '<h1>Welcome, '
    output += session['username']
    output += '!</h1>'
    output += '<img src="'
    output += session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % session['username'])
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():

    access_token = session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    '''
    print('In gdisconnect access token is %r' % access_token.decode("utf-8"))
    print('User name is: ')
    print(session['username'])
    print('session is %r' % session)
    result = theRequests.post('https://accounts.google.com/o/oauth2/revoke',
                  params={'token': access_token.decode("utf-8")},
                  headers = {'content-type': 'application/x-www-form-urlencoded'})
    print('result is: %r' % result.content)
    if result.status_code == '200':
    '''
    del session['access_token']
    del session['g_id']
    del session['username']
    del session['email']
    del session['picture']
    flash('Successfully disconnected.')
    return redirect(url_for('showRestaurants'))
    '''
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    '''



#JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    items = MenuItem.query.filter_by(restaurant_id = restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    Menu_Item = MenuItem.query.filter_by(id = menu_id).one()
    return jsonify(Menu_Item = Menu_Item.serialize)

@app.route('/restaurant/JSON')
def restaurantsJSON():
    restaurants = Restaurant.query.all()
    return jsonify(restaurants= [r.serialize for r in restaurants])


#Show all restaurants
@app.route('/')
@app.route('/restaurant/')
def showRestaurants():
  restaurants = Restaurant.query.order_by(Restaurant.name.asc())
  return render_template('restaurants.html', restaurants = restaurants)

#Create a new restaurant
@app.route('/restaurant/new/', methods=['GET','POST'])
def newRestaurant():
  if request.method == 'POST':
      newRestaurant = Restaurant(name = request.form['name'])
      db.session.add(newRestaurant)
      flash('New Restaurant %s Successfully Created' % newRestaurant.name)
      db.session.commit()
      return redirect(url_for('showRestaurants'))
  else:
      return render_template('newRestaurant.html')

#Edit a restaurant
@app.route('/restaurant/<int:restaurant_id>/edit/', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
  editedRestaurant = Restaurant.query.filter_by(id = restaurant_id).one()
  if request.method == 'POST':
      if request.form['name']:
        editedRestaurant.name = request.form['name']
        flash('Restaurant Successfully Edited %s' % editedRestaurant.name)
        return redirect(url_for('showRestaurants'))
  else:
    return render_template('editRestaurant.html', restaurant = editedRestaurant)


#Delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods = ['GET','POST'])
def deleteRestaurant(restaurant_id):
  restaurantToDelete = Restaurant.query.filter_by(id = restaurant_id).one()
  if request.method == 'POST':
      db.session.delete(restaurantToDelete)
      flash('%s Successfully Deleted' % restaurantToDelete.name)
      db.session.commit()
      return redirect(url_for('showRestaurants', restaurant_id = restaurant_id))
  else:
      return render_template('deleteRestaurant.html',restaurant = restaurantToDelete)

#Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = Restaurant.query.filter_by(id = restaurant_id).one()
    items = MenuItem.query.filter_by(restaurant_id = restaurant_id).all()
    return render_template('menu.html', items = items, restaurant = restaurant)
     


#Create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/',methods=['GET','POST'])
def newMenuItem(restaurant_id):
  if request.method == 'POST':
      newItem = MenuItem(name = request.form['name'], description = request.form['description'], price = request.form['price'], course = request.form['course'], restaurant_id = restaurant_id)
      db.session.add(newItem)
      db.session.commit()
      flash('New Menu %s Item Successfully Created' % (newItem.name))
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
  else:
      return render_template('newmenuitem.html', restaurant_id = restaurant_id)

#Edit a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):

    editedItem = MenuItem.query.filter_by(id = menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        db.session.add(editedItem)
        db.session.commit() 
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id = restaurant_id, menu_id = menu_id, item = editedItem)


#Delete a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods = ['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
    itemToDelete = MenuItem.query.filter_by(id = menu_id).one() 
    if request.method == 'POST':
      db.session.delete(itemToDelete)
      db.session.commit()
      flash('Menu Item Successfully Deleted')
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
      return render_template('deleteMenuItem.html', item = itemToDelete)




if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = False
  app.run(host = '0.0.0.0', port = 5000)
