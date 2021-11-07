import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt

from .models import User, Post

class NewPostForm(forms.Form):
    post = forms.CharField(widget=forms.Textarea,label="New Post", max_length=280)


def index(request):
     # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NewPostForm(request.POST)
        user = request.user
        # check whether it's valid:
        if form.is_valid() and (user is not None):
            # process the data in form.cleaned_data as required
            content = form.cleaned_data["post"]
            # Check 280 char rule
            if len(content) <= 280:
                new_post = Post(creater=user, content=content)
                new_post.save()  # save to db
                form = NewPostForm()  # empty form
    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewPostForm()
    
    # Pagination #
    # Will send always this part
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 3)  # Show 10 posts per page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        posts = paginator.page(paginator.num_pages)

    context = {
        "posts" : posts,
        "form" : form
    }
    return render(request, "network/index.html", context)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("network:index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("network:index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("network:index"))
    else:
        return render(request, "network/register.html")

@login_required(login_url="/login")
def following_view(request):
    if request.method == "GET":
        user = request.user
        followings = user.following_users.all()  # Here pagination & User posts should be sent !!!
        context = {
            "followings" : followings
        }
        return render(request, "network/followings.html", context)

@csrf_exempt
@login_required(login_url="/login")
def post_like_view(request, post_id):
    # Query for requested post
    try:
        user = request.user
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found."}, status=404)

    if request.method == "PUT":
        data = json.loads(request.body)
        if data.get("isLiked") is not None:
            user_liked_post = data["isLiked"]  # will be True or False
            if user_liked_post:
                post.liked_users.add(user)
            else:
                post.liked_users.remove(user)
        post.save()
        likeNum = post.liked_users.count()
        return JsonResponse({"likeNum": likeNum}, status=201)