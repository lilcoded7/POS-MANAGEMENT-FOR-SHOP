from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from accounts.forms import EmailAuthenticationForm


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, "You're already logged in.")
        return redirect('home')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email') 
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', True)
            

            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                
                if not remember_me:
                    request.session.set_expiry(0) 
                
                messages.success(request, f"Welcome back, {user.username}")
                
                return redirect('home')
            
            messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmailAuthenticationForm(request)
     
    context = {
        'form': form,
       
    }
    return render(request, 'auths/login.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, f"You've been logged out. Goodbye!")
    return redirect('login_view')