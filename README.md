Movie Ticket Booking System
A Django-based movie ticket booking application with user and admin roles, secure payments, seat reservation, and admin analytics.

*** Features
User
User Registration & Login
Browse movies
Filter movies by Genre & Language
Watch trailers (YouTube redirect)
Select seats with 5-minute reservation timeout
Stripe payment integration
Email ticket confirmation after successful booking

Admin
Admin access via createsuperuser
Add / manage movies, theaters, shows, and seats
View all bookings
Delete bookings & unlock seats

Admin dashboard with analytics
Total revenue
Popular movies
Busiest theaters

🔗 URLs
User Site: http://127.0.0.1:8000/
Admin Login: http://127.0.0.1:8000/admin/
Admin Dashboard: http://127.0.0.1:8000/admin-dashboard/

Admin access is only for users created using python manage.py createsuperuser

⚙️ Run the Project
git clone <repo-url>
cd project-folder
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver


Open in browser:
http://127.0.0.1:8000/

💳 Stripe Test Card
4242 4242 4242 4242
Any future date | Any CVV

🛠 Tech Stack
Django, Python
Bootstrap, JavaScript
Stripe Payment Gateway
SQLite 
