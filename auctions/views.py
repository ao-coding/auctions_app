from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import  HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django import forms
from django.core.paginator import Paginator
from .models import User, Listing, Bid, Comment, Category, WatchList


def index(request):
    listings = Listing.objects.filter(sold=False)
    paginator = Paginator(listings, 10) # Show 10 listings per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        query_name = request.POST.get('title', None)
        if query_name:
            results = Listing.objects.filter(title__contains=query_name, sold=False)
            paginator = Paginator(results, 10)
            page_obj = paginator.get_page(page_number)

            return render(request, "auctions/index.html", 
            {"page_obj": page_obj,
            "categories": Category.objects.all(),
            })

    else:
        return render(request, "auctions/index.html", 
        {"page_obj": page_obj,
        "categories": Category.objects.all(),
        })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required
def create_listing(request):
    if request.method == "POST" and request.FILES["image_url"]:

        image_url = request.FILES["image_url"]
        fss = FileSystemStorage()
        file = fss.save(image_url.name, image_url)
        url = fss.url(file)

        if (request.FILES["image_url2"] is not None):
            image_url2 = request.FILES["image_url2"]
            file2 = fss.save(image_url2.name, image_url2)
            url2 = fss.url(file2)
        else:
            url2 = None

        title = request.POST.get("title")
        description = request.POST.get("description")
        price = request.POST.get("price")
        category_id = Category.objects.get(id=request.POST["categories"])
        user = request.user

        obj = Listing.objects.create(user=user, title=title, description=description, category=category_id, price=price, image_url=url, image_url2=url2)
        obj.save()
            
    
        return HttpResponseRedirect(reverse('index'))

    else:
        return render(request, "auctions/create_listing.html", {
            "categories": Category.objects.all()
        })


def listing_info(request, listing_id):
    listing = Listing.objects.get(id=listing_id)
    user = request.user

    is_owner = True if listing.user == user else False
    category = Category.objects.get(category=listing.category)
    comments = Comment.objects.filter(listing=listing.id)
    watching = WatchList.objects.filter(user = user, listing = listing)

    return listing, user, is_owner, category, comments, watching


def listing(request, listing_id):
    listing = Listing.objects.get(id=listing_id)
    category = Category.objects.get(category=listing.category)
    comments = Comment.objects.filter(listing=listing.id)
    bids_num = len(Bid.objects.filter(listing=listing.id))
    bids = Bid.objects.filter(listing=listing.id)
    
    if request.user.is_authenticated:
        user = request.user
        is_owner = True if listing.user == user else False
        is_winner = False
        winner=None

        if request.method == "POST":
            comment = request.POST["comment"]
            if comments != "":
                Comment.objects.create(user = user, listing = listing, comment = comment)
         
            return render(request, "auctions/listing.html", {
            "listing": listing,
            "category": category,
            "comments": comments,
            "bids_num":bids_num
            })

        else:
            if (bids_num > 0):
                winner = Bid.objects.get(price = listing.price, listing = listing).user
                is_winner = (user.id == winner.id)

            return render(request, "auctions/listing.html", {
            "listing": listing,
            "category": category,
            "comments": comments,
            "watching": WatchList.objects.filter(user = user, listing = listing).values('watching'), 
            "is_owner": is_owner,
            "is_winner": is_winner,
            "winner":winner,
            "bids_num":bids_num,
            "bids": bids    
            })
            
    else:
        return render(request, "auctions/listing.html", {
            "listing": listing,
            "category": category,
            "comments": comments,
            "bids_num":bids_num
            })


@login_required
def remove_watchlist(request, listing_id):
    info = listing_info(request, listing_id)
    listing, user, is_owner, category, comments, watch = info[0], info[1], info[2], info[3], info[4], info[5]
    watch.watching = False
    watch.save()

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "category": category,
        "comments": comments, 
        "watching": WatchList.objects.get(user = user, listing = listing).watching, 
        "is_owner": is_owner
    })

@login_required
def add_watchlist(request, listing_id):
    info = listing_info(request, listing_id)
    listing, user, is_owner, category, comments = info[0], info[1], info[2], info[3], info[4]
    watch = WatchList.objects.filter(user = user, listing = listing)
    if watch:
        watch = WatchList.objects.get(user = user, listing = listing)
        watch.watching = True
        watch.save()
    else:
        WatchList.objects.create(user = user, listing = listing, watching = True)

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "category": category,
        "comments": comments, 
        "watching": WatchList.objects.get(user = user, listing = listing).watching, 
        "is_owner": is_owner
    })

@login_required
def bidding(request, listing_id):
    info = listing_info(request, listing_id)
    listing, user, is_owner, category, comments, watch = info[0], info[1], info[2], info[3], info[4], info[5]
    if request.method == "POST":
        bid = request.POST["bid"]
        listing.price = float(bid)
        listing.save()
        Bid.objects.create(user = user, price = bid, listing = listing)
        bids_num = len(Bid.objects.filter(listing=listing.id))

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "category": category,
        "comments": comments, 
        "watching": watch, 
        "is_owner": is_owner,
        "bids_num":bids_num
    })

@login_required
def close_bidding(request, listing_id):
    info = listing_info(request, listing_id)
    listing, user, is_owner, category, comments, watch = info[0], info[1], info[2], info[3], info[4], info[5]
    listing.sold = True
    listing.save()
    winner = Bid.objects.get(price = listing.price, listing = listing).user

    return render(request, "auctions/close_bidding.html", {
        "listing": listing,
        "category": category,
        "comments": comments, 
        "watching": watch, 
        "is_owner": is_owner,
        "winner": winner
    })

@login_required
def watchlist(request, user_id):
    listing_ids = WatchList.objects.filter(user = request.user, watching=True).values('listing')
    listing = Listing.objects.filter(id__in = listing_ids)
    return render(request, "auctions/watchlist.html", {
        "listings": listing
    })

def category(request):
    listings = None
    category = None
    if request.method == "POST":
        category = request.POST["categories"]
        listings = Listing.objects.filter(category = category)
    return render(request, "auctions/categories.html", {
        "categories": Category.objects.all(),
        "category": Category.objects.get(id = category).category if category is not None else "",
        "listings": listings
    })

@login_required
def myListings(request):
    
    listing = Listing.objects.filter(user = request.user)
    return render(request, "auctions/myListings.html", {
        "listings": listing
    })

@login_required
def myBids(request):
    bids = Bid.objects.filter(user = request.user)
    
    return render(request, "auctions/myBids.html", {
        "bids": bids
    })