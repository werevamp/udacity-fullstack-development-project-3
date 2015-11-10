#Catalog Item

##Introduction

Catalog Item give a developer an introduction on full stack development. It also
goes through the basics of authorization and authentication.

##Instructions

There are three steps to run this app:

1. Create database
2. Populate application
2. Run the application

###Create Database

The app will not work unless you create the database. To create the database run
the following statement in the command line:

python database_setup.py

###Add Starting Entries

We need to populate the app with some entries. To populate the app run the
following statement in the command line:

python lotsofitems.py

###Run the application

Once the database is created you are ready to run the application. To run the
application run the following statement in the command line.

python item_catalog.py

This will run the app, now you will be able to use the app by hitting
http://localhost:8000.

###API endpoints

Below are a few API endpoints:

http://localhost:8000/catalog/categories/JSON/
http://localhost:8000/catalog/category/1/JSON/
http://localhost:8000/catalog/category/1/items/JSON/
