from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponse

import stripe
import logging

from .models import Movie, Theater, Seat, Booking
from .utils import release_expired_seats

PRICE_PER_SEAT = 200  # INR
logger = logging.getLogger(__name__)


# ======================
# MOVIES
# ======================

def movie_list(request):
    movies = Movie.objects.all()

    if request.GET.get("search"):
        movies = movies.filter(name__icontains=request.GET["search"])
    if request.GET.get("genre"):
        movies = movies.filter(genre__iexact=request.GET["genre"])
    if request.GET.get("language"):
        movies = movies.filter(language__iexact=request.GET["language"])

    return render(request, "movies/movie_list.html", {"movies": movies})


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    return render(request, "movies/movie_detail.html", {"movie": movie})


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, "movies/theater_list.html", {
        "movie": movie,
        "theaters": theaters
    })


# ======================
# SEAT BOOKING
# ======================

@login_required
def book_seats(request, theater_id):
    release_expired_seats()
    theater = get_object_or_404(Theater, id=theater_id)

    if request.method == "POST":
        seat_ids = request.POST.getlist("seats")

        for seat in Seat.objects.filter(id__in=seat_ids, theater=theater):
            if not seat.is_booked and not seat.is_reserved:
                seat.is_reserved = True
                seat.reserved_by = request.user
                seat.reserved_at = timezone.now()
                seat.save()

        return redirect("confirm_booking", theater_id=theater.id)

    seats = Seat.objects.filter(theater=theater)
    return render(request, "movies/seat_selection.html", {
        "theater": theater,
        "seats": seats
    })


@login_required
def confirm_booking(request, theater_id):
    release_expired_seats()
    theater = get_object_or_404(Theater, id=theater_id)

    seats = Seat.objects.filter(
        theater=theater,
        is_reserved=True,
        reserved_by=request.user
    )

    if not seats.exists():
        return redirect("movie_list")

    if request.method == "POST":
        return redirect("make_payment", theater_id=theater.id)

    return render(request, "movies/confirm_booking.html", {
        "theater": theater,
        "seats": seats
    })


# ======================
# PAYMENT (STRIPE)
# ======================

@login_required
def make_payment(request, theater_id):
    release_expired_seats()

    if not settings.STRIPE_SECRET_KEY:
        return HttpResponse(
            "Payment is temporarily unavailable. Stripe key missing.",
            status=503
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    seats = Seat.objects.filter(
        theater_id=theater_id,
        is_reserved=True,
        reserved_by=request.user
    )

    if not seats.exists():
        return redirect("movie_list")

    amount = seats.count() * PRICE_PER_SEAT

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {
                        "name": "Movie Tickets",
                    },
                    "unit_amount": amount * 100,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=request.build_absolute_uri(
                f"/movies/theater/{theater_id}/success/"
            ),
            cancel_url=request.build_absolute_uri(
                f"/movies/theater/{theater_id}/confirm/"
            ),
            customer_email=request.user.email,
        )
    except Exception as e:
        return HttpResponse(f"Stripe error: {str(e)}", status=500)

    return redirect(session.url)


@login_required
def payment_success(request, theater_id):
    seats = Seat.objects.filter(
        theater_id=theater_id,
        is_reserved=True,
        reserved_by=request.user
    )

    if not seats.exists():
        return redirect("movie_list")

    seat_numbers = []

    for seat in seats:
        Booking.objects.create(
            user=request.user,
            seat=seat,
            movie=seat.theater.movie,
            theater=seat.theater
        )
        seat.is_booked = True
        seat.is_reserved = False
        seat.reserved_by = None
        seat.reserved_at = None
        seat.save()
        seat_numbers.append(seat.seat_number)

    # Send email with proper error handling
    try:
        if request.user.email and settings.EMAIL_HOST_USER:
            send_mail(
                subject="🎟 Ticket Booking Confirmation",
                message=f"""Hi {request.user.username},

Your booking is confirmed!

Movie: {seats.first().theater.movie.name}
Theater: {seats.first().theater.name}
Seats: {', '.join(seat_numbers)}
Total: ₹{len(seat_numbers) * PRICE_PER_SEAT}

Enjoy your show!

- BookMySeat Team
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
            )
            print(f"Email sent successfully to {request.user.email}")
        else:
            print(f"Cannot send email. User email: {request.user.email}, Host user configured: {bool(settings.EMAIL_HOST_USER)}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

    return redirect("profile")


# ======================
# ADMIN DASHBOARD
# ======================

@staff_member_required
def admin_dashboard(request):
    context = {
        "total_bookings": Booking.objects.count(),
        "total_revenue": Booking.objects.count() * PRICE_PER_SEAT,
        "popular_movies": Movie.objects.annotate(
            bookings=Count("booking")
        ).order_by("-bookings")[:5],
        "busy_theaters": Theater.objects.annotate(
            bookings=Count("booking")
        ).order_by("-bookings")[:5],
    }
    return render(request, "movies/admin_dashboard.html", context)
